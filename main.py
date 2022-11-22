#!/usr/bin/python
# -*- coding: utf-8 -*-
import argparse
from typing import Tuple

import telebot
import time
import logging
import mongomock
import os
import random
import sentry_sdk
import uuid
import yaml

from apscheduler.schedulers.background import BackgroundScheduler

import dialogue_manager
import parables
import daytoday

from datetime import datetime
from flask import Flask, request
from pymongo import MongoClient
from telebot.apihelper import ApiException
from dialogue_manager import classify_text, make_suggests, reply_with_boltalka, Intents, QTypes
from grow import reply_with_coach

from bandit import create_weights, unsullied_candidates

logger = logging.getLogger(__name__)


if os.getenv('SENTRY_DSN', None) is not None:
    sentry_sdk.init(os.environ['SENTRY_DSN'])

ON_HEROKU = os.environ.get('ON_HEROKU')
TOKEN = os.environ['TOKEN']
bot = telebot.TeleBot(TOKEN)

server = Flask(__name__)
TELEBOT_URL = 'telebot_webhook/'
BASE_URL = 'https://the-watchman-bot.herokuapp.com/'
BASE_URL = 'https://the-watchman-bot.toys.dialogic.digital/'

SECRET = os.getenv('SECRET', 'mfrw7qy4as-]e0qs-ads;lkfua')

# The API will not allow more than ~30 messages to different users per second
TIMEOUT_BETWEEN_MESSAGES = 0.5


MONGO_URL = os.environ.get('MONGODB_URI')
if MONGO_URL:
    mongo_client = MongoClient(MONGO_URL)
    mongo_db = mongo_client.get_default_database()
else:
    mongo_client = mongomock.MongoClient()
    mongo_db = mongo_client.db
mongo_users = mongo_db.get_collection('users')
mongo_messages = mongo_db.get_collection('messages')

PROCESSED_MESSAGES = set()


with open('data/many_questions.txt', 'r', encoding='utf-8') as f:
    LONGLIST = [
        q.strip() for q in f.readlines()
        if not q.strip().startswith('#')
           and not q.strip().startswith('/')
           and len(q.strip()) >= 5
    ]

with open('data/special_questions.yaml', 'r', encoding='utf-8') as f:
    special_questions = yaml.safe_load(f)


UNSULLIED = unsullied_candidates(texts=LONGLIST, collection=mongo_messages)
WEIGHTS = create_weights(texts=LONGLIST, collection=mongo_messages)


def get_or_insert_user(tg_user=None, tg_uid=None):
    if tg_user is not None:
        uid = tg_user.id
    elif tg_uid is not None:
        uid = tg_uid
    else:
        return None
    found = mongo_users.find_one({'tg_id': uid})
    if found is not None:
        return found
    if tg_user is None:
        return ValueError('User should be created, but telegram user object was not provided.')
    new_user = dict(
        tg_id=tg_user.id,
        first_name=tg_user.first_name,
        last_name=tg_user.last_name,
        username=tg_user.username,
        subscribed=True,  # todo: ask for subscription
    )
    mongo_users.insert_one(new_user)
    return new_user


@server.route("/" + TELEBOT_URL)
def web_hook():
    bot.remove_webhook()
    time.sleep(TIMEOUT_BETWEEN_MESSAGES)
    bot.set_webhook(url=BASE_URL + TELEBOT_URL + TOKEN)
    return "!", 200


def generate_question(text_weights=None, unsullied_texts=None) -> Tuple[str, str]:
    rnd = random.random()
    # if rnd > 0.98:
    #    try:
    #        return parables.get_random_news(ask_opinion=True, topic='random'), QTypes.NEWS
    #    except:
    #        rnd = 0
    if rnd > 0.9:
        try:
            return parables.get_random_citation(ask_opinion=True), QTypes.CITATION
        except:
            rnd = 0
    if rnd > 0.85:
        try:
            text, text_type = daytoday.get_random_event(ask_opinion=True, return_empty=True), QTypes.DAY_TODAY
            if text:
                return text, text_type
            else:
                rnd = 0
        except:
            rnd = 0
    if rnd > 0.5:
        return make_new_question(), QTypes.UNIQUE_QUESTION

    # else:
    if unsullied_texts and random.random() < 0.5:
        # choose from "good or unexplored" questions
        return random.choice(unsullied_texts), QTypes.UNSULLIED
    else:
        if text_weights:
            return random.choices(LONGLIST, weights=text_weights)[0], QTypes.WEIGHTED
        else:
            return random.choice(LONGLIST), QTypes.UNIFORM


def make_new_question():
    # generate a question with a language model using 10 random languages as examples
    examples = [random.choice(LONGLIST).strip() for i in range(10)]
    text = reply_with_boltalka(text=random.choice(LONGLIST), user_object={'history': examples})
    if '?' not in text:
        return random.choice(LONGLIST)
    return text.split('?')[0] + '?'


@server.route(f"/{SECRET}/wakeup/")
def wake_up():
    web_hook()
    reply_with_boltalka('Попытка заранее разбудить болталку', user_object={})
    today_date = str(datetime.today())[:10]
    weights = create_weights(LONGLIST, collection=mongo_messages)
    unsullied = unsullied_candidates(LONGLIST, collection=mongo_messages)

    for user in mongo_users.find():
        user_id = user.get('tg_id')
        num_unanswered = user.get('num_unanswered', 0)
        if not user_id or not user.get('subscribed'):
            print("Do not write to the unsubscribed user '{}'".format(user))
            continue
        if 'last_message_time' in user:
            # don't send the update if the last user message is very recent
            delta = datetime.utcnow() - datetime.fromisoformat(user['last_message_time'])
            if delta.total_seconds() < 60 * 10:  # after 10 minutes of inactivity a gentle push seems OK
                print("Do not write to the user '{}' in the middle of conversation".format(user))
                continue
        print("Writing to user '{}'".format(user_id))
        req_id = str(uuid.uuid4())
        utterance, method = generate_question(text_weights=weights, unsullied_texts=unsullied)
        intent = Intents.PUSH_QUESTION

        if num_unanswered >= 30:
            mongo_users.update_one(
                {'tg_id': user_id},
                {'$set': {'subscribed': False}}
            )
            utterance = 'Привет! Я устал от этого бесконечного одностороннего монолога. ' \
                        '\nЯ вас отписываю от вопросов. ' \
                        'Когда захотите, подпишитесь снова сами.' \
                        '\nНадеюсь, у вас всё хорошо.'
            intent = Intents.PUSH_UNSUBSCRIBE
        elif num_unanswered >= 20 and random.random() < 0.9:
            # we bother the user only with 10% probability
            continue
        elif num_unanswered >= 10 and random.random() < 0.5:
            # send message to user every other day
            continue
        elif num_unanswered >= 3 and random.random() < 0.2:
            # 20 % of messages ask what happens with the user
            utterance = random.choice([
                'Хм, я уже несколько дней не получаю ответа. С вами всё в порядке?',
                'Что-то вы давно мне не отвечаете. Как у вас дела?',
                # 'Привет! Я давно уже не получаю от вас писем. Вы куда-то уехали?',
                'Здравствуйте! Как давно я не получал от вас писем. Где вы?',
                # 'Эх, как я соскучился по вашим интересным ответам... Почему вы мне не пишете?',
                'Мне так нравилось читать ваши ответы... Может, напишете мне снова?',
                # 'Мне кажется, нам надо прояснить отношения. Почему вы не отвечаете?!',
                # 'Последние несколько дней мне кажется, что я пишу в пустоту. Что произошло?',
                'Привет! Вы давно мне не отвечаете. Расскажите, что у вас за это время произошло?',
                'Добрый вечер! Давненько вы мне ничего не писали, я по вам соскучился. Что у вас сейчас происходит?',
                'Привет! Вы уже несколько дней мне не отвечаете. '
                'Давайте договоримся, что вы будете время от времени отвечать на мои вопросы?',
            ])
            intent = Intents.PUSH_MISS_YOU
            method = Intents.PUSH_MISS_YOU
        elif today_date in special_questions:
            intent = Intents.PUSH_SPECIAL
            method = Intents.PUSH_SPECIAL
            if isinstance(special_questions[today_date], list):
                utterance = random.choice(special_questions[today_date])
            else:
                utterance = special_questions[today_date]

        for attempt in range(3):
            try:
                bot.send_message(
                    user_id, utterance,
                    reply_markup=dialogue_manager.make_like_dislike_buttons(req_id=req_id),
                    parse_mode='html',
                    disable_web_page_preview=True,
                )
                break
            except telebot.apihelper.ApiException as e:
                if e.result.text and 'bot was blocked by the user' in e.result.text:
                    # unsubscribe this user
                    mongo_users.update_one(
                        {'tg_id': user_id},
                        {'$set': {'subscribed': False, 'blocked': True}}
                    )
                    break
                elif e.result.text and 'user is deactivated' in e.result.text:
                    mongo_users.update_one(
                        {'tg_id': user_id},
                        {'$set': {'subscribed': False, 'deactivated': True}}
                    )
                    break
                elif e.result.status_code == 429:
                    # too many requests - just waiting
                    time.sleep(3)
                    continue
                else:
                    # don't know how to handle it
                    raise e
        msg = dict(
            text=utterance, user_id=user_id, from_user=False, timestamp=str(datetime.utcnow()),
            push=True, req_id=req_id, intent=intent, method=method,
        )
        mongo_messages.insert_one(msg)

        the_update = {'$set': {
            'num_unanswered': num_unanswered + 1,
            'history': [utterance],
        }}
        the_update['$set'].update(dialogue_manager.EMPTY_STATE)
        mongo_users.update_one({'tg_id': user_id}, the_update)
        time.sleep(TIMEOUT_BETWEEN_MESSAGES)
    return "Маам, ну ещё пять минуточек!", 200


@bot.message_handler(func=lambda message: True)
def process_message(message):
    if message.message_id in PROCESSED_MESSAGES:
        return
    PROCESSED_MESSAGES.add(message.message_id)

    bot.send_chat_action(message.chat.id, 'typing')

    user_object = get_or_insert_user(message.from_user)
    user_object['history'] = user_object.get('history') or []
    user_id = message.chat.id
    req_id = str(uuid.uuid4())
    now = str(datetime.utcnow())
    msg = dict(
        text=message.text, user_id=user_id, from_user=True, timestamp=now,
        req_id=req_id,
    )
    mongo_messages.insert_one(msg)
    intent = classify_text(message.text, user_object=user_object)
    the_update = {}

    if user_object.get('coach_state') and 'grow_coach' not in intent:
        # interrupt the coach scenario if we are out of it
        the_update = {"$set": {'coach_state': {}}}

    method = None

    if intent == Intents.HELP:
        response = dialogue_manager.REPLY_HELP
    elif intent == Intents.INTRO:
        response = dialogue_manager.REPLY_HELP + '\n' + dialogue_manager.REPLY_INTRO
    elif intent == Intents.WANT_QUESTION:
        response, method = generate_question(text_weights=WEIGHTS, unsullied_texts=UNSULLIED)
    elif intent == Intents.UNIQUE_QUESTION:
        response = make_new_question()
        method = QTypes.UNIQUE_QUESTION
    elif intent == Intents.SUBSCRIBE:
        response = "Теперь вы подписаны на ежедневные вопросы!"
        the_update = {"$set": {'subscribed': True}}
    elif intent == Intents.UNSUBSCRIBE:
        response = "Теперь вы отписаны от ежедневных вопросов!"
        the_update = {"$set": {'subscribed': False}}
    elif intent in {Intents.GROW_COACH_INTRO, Intents.GROW_COACH, Intents.GROW_COACH_EXIT, Intents.GROW_COACH_FEEDBACK}:
        response, the_update = reply_with_coach(message.text, user_object=user_object, intent=intent)
    elif intent == Intents.PARABLE:
        response = parables.get_random_parable()
        method = QTypes.PARABLE
    elif intent == Intents.CITATION:
        response = parables.get_random_citation()
        method = QTypes.CITATION
    elif intent == Intents.CONTACT_DEV:
        response = 'Напишите моему разработчику напрямую. Это @cointegrated. Не стесняйтесь!'
    elif intent == Intents.NEWS:
        response = parables.get_random_news(ask_opinion=(random.random() < 0.2), topic='random')
        method = QTypes.NEWS
    elif intent == Intents.DAY_TODAY:
        response = daytoday.get_random_event(ask_opinion=(random.random() < 0.4))
        method = QTypes.UNIFORM
    else:
        response = reply_with_boltalka(message.text, user_object)

    if '$set' not in the_update:
        the_update['$set'] = {}
    the_update['$set']['last_intent'] = intent
    the_update['$set']['num_unanswered'] = 0
    the_update['$set']['last_message_time'] = now

    new_history = user_object['history'] + [message.text or ''] + [response]
    the_update['$set']['history'] = new_history[-10:]

    mongo_users.update_one({'tg_id': message.from_user.id}, the_update)
    user_object = get_or_insert_user(tg_uid=message.from_user.id)

    msg = dict(
        text=response, user_id=user_id, from_user=False, timestamp=str(datetime.utcnow()),
        req_id=req_id, push=False, intent=intent, method=method,
    )
    mongo_messages.insert_one(msg)
    suggests = make_suggests(text=response, intent=intent, user_object=user_object, req_id=req_id)
    bot.reply_to(message, response, reply_markup=suggests, parse_mode='html', disable_web_page_preview=True)


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    payload = call.data
    if '_' not in payload:
        bot.answer_callback_query(call.id, 'Странно')
        return
    req_id, sentiment = payload.split('_', 1)
    mongo_messages.update_one({'req_id': req_id, 'from_user': False}, {'$set': {'feedback': sentiment}})
    try:
        bot.answer_callback_query(call.id, "Фидбек принят!")
    except ApiException as e:
        logger.warning('Api exception when answering callback query: {}'.format(e))

    user_object = get_or_insert_user(call.from_user)
    if user_object:
        user_id = user_object['tg_id']
        likes_streak = user_object.get('likes_streak', 0)
        if sentiment == 'pos':
            likes_streak += 1
            if likes_streak % 5 == 0 and random.random() < 0.4:
                intent = Intents.PUSH_ASK_FEEDBACK
                utterance = 'Я рад, что вам нравятся мои вопросы. ' \
                            'Весьма приятно чувствовать себя нужным.' \
                            '\nЯ буду очень благодарен, если вы про меня расскажете где-нибудь в соцсетях (:'
                bot.send_message(user_id, utterance, parse_mode='html')
                msg = dict(
                    text=utterance, user_id=user_id, from_user=False, timestamp=str(datetime.utcnow()),
                    push=True, req_id=req_id, intent=intent,
                )
                mongo_messages.insert_one(msg)
        else:
            likes_streak = 0
        the_update = {'$set': {'likes_streak': likes_streak}}
        mongo_users.update_one({'tg_id': user_id}, the_update)


@server.route('/' + TELEBOT_URL + TOKEN, methods=['POST'])
def get_message():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "!", 200


parser = argparse.ArgumentParser(description='Run the bot')
parser.add_argument('--poll', action='store_true')


def main():
    args = parser.parse_args()
    if args.poll:
        bot.remove_webhook()
        bot.polling()
    else:
        # this branch is intended to run only in the production environment (e.g. Heroku web app)
        web_hook()

        # rerun the bot every 24 hours
        scheduler = BackgroundScheduler()
        scheduler.add_job(wake_up, 'cron', hour=18, minute=30)  # I hope this is UTCDockerfileDockerfile
        scheduler.start()

        server.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))


if __name__ == '__main__':
    main()
