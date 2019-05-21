#!/usr/bin/python
# -*- coding: utf-8 -*-
import argparse
import telebot
import os
import random
import dialogue_manager
import sentry_sdk

from datetime import datetime
from flask import Flask, request
from pymongo import MongoClient
from dialogue_manager import classify_text, make_suggests, reply_with_boltalka, Intents
from grow import reply_with_coach

if os.getenv('SENTRY_DSN', None) is not None:
    sentry_sdk.init(os.environ['SENTRY_DSN'])

ON_HEROKU = os.environ.get('ON_HEROKU')
TOKEN = os.environ['TOKEN']
bot = telebot.TeleBot(TOKEN)

server = Flask(__name__)
TELEBOT_URL = 'telebot_webhook/'
BASE_URL = 'https://the-watchman-bot.herokuapp.com/'


MONGO_URL = os.environ.get('MONGODB_URI')
mongo_client = MongoClient(MONGO_URL)
mongo_db = mongo_client.get_default_database()
mongo_users = mongo_db.get_collection('users')
mongo_messages = mongo_db.get_collection('messages')


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
        subscribed=True  # todo: ask for subscription
    )
    mongo_users.insert_one(new_user)
    return new_user


THE_QUESTIONS = [
    "Остановись!",
    "Кто ты?",
    "Откуда ты?",
    "Куда ты идёшь?"
]
with open('many_questions.txt', 'r', encoding='utf-8') as f:
    LONGLIST = [
        q for q in f.readlines()
        if not q.strip().startswith('#')
           and not q.strip().startswith('/')
           and len(q.strip()) >= 5
    ]


@server.route("/" + TELEBOT_URL)
def web_hook():
    bot.remove_webhook()
    bot.set_webhook(url=BASE_URL + TELEBOT_URL + TOKEN)
    return "!", 200


@server.route("/wakeup/")
def wake_up():
    web_hook()
    # todo: decide what to do if the update interferes with the current dialogue
    for user in mongo_users.find():
        user_id = user.get('tg_id')
        if not user_id or not user.get('subscribed'):
            print("Do not write to user '{}'".format(user))
            continue
        print("Writing to user '{}'".format(user_id))
        """
        for utterance in THE_QUESTIONS:
            bot.send_message(user.user_id, utterance)
            time.sleep(0.01)
            msg = StoredMessage(text=utterance, user_id=user.user_id, from_user=False)
            db.session.add(msg)
        """
        utterance = random.choice(LONGLIST)
        bot.send_message(user_id, utterance)

        msg = dict(text=utterance, user_id=user_id, from_user=False, timestamp=str(datetime.utcnow()))
        mongo_messages.insert_one(msg)
    return "Маам, ну ещё пять минуточек!", 200


@bot.message_handler(func=lambda message: True)
def process_message(message):
    user_object = get_or_insert_user(message.from_user)
    user_id = message.chat.id
    msg = dict(text=message.text, user_id=user_id, from_user=True, timestamp=str(datetime.utcnow()))
    mongo_messages.insert_one(msg)
    intent = classify_text(message.text, user_object=user_object)
    the_update = None
    if intent == Intents.HELP:
        response = dialogue_manager.REPLY_HELP
    elif intent == Intents.INTRO:
        response = dialogue_manager.REPLY_HELP + '\n' + dialogue_manager.REPLY_INTRO
    elif intent == Intents.WANT_QUESTION:
        response = random.choice(LONGLIST)
    elif intent == Intents.SUBSCRIBE:
        response = "Теперь вы подписаны на ежедневные вопросы!"
        the_update = {"$set": {'subscribed': True}}
    elif intent == Intents.UNSUBSCRIBE:
        response = "Теперь вы отписаны от ежедневных вопросов!"
        the_update = {"$set": {'subscribed': False}}
    elif intent == Intents.GROW_COACH_INTRO or intent == Intents.GROW_COACH or intent == Intents.GROW_COACH_EXIT:
        response, the_update = reply_with_coach(message.text, user_object=user_object, intent=intent)
    else:
        response = reply_with_boltalka(message.text, user_object)

    # todo: unconditionally, update the prev_intent - needed for classification
    if the_update is None:
        the_update = {}
    if '$set' not in the_update:
        the_update['$set'] = {}
    the_update['$set']['last_intent'] = intent
    mongo_users.update_one({'tg_id': message.from_user.id}, the_update)
    user_object = get_or_insert_user(tg_uid=message.from_user.id)

    msg = dict(text=response, user_id=user_id, from_user=False, timestamp=str(datetime.utcnow()))
    # todo: log the previous message id
    mongo_messages.insert_one(msg)
    suggests = make_suggests(text=response, intent=intent, user_object=user_object)
    bot.reply_to(message, response, reply_markup=suggests)


@server.route('/' + TELEBOT_URL + TOKEN, methods=['POST'])
def get_message():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "!", 200


parser = argparse.ArgumentParser(description='Run the bot')
parser.add_argument('--poll', action='store_true')


def main_new():
    args = parser.parse_args()
    if args.poll:
        bot.remove_webhook()
        bot.polling()
    else:
        # this branch is intended to run only in the production environment (e.g. Heroku web app)
        web_hook()
        server.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))


if __name__ == '__main__':
    main_new()
