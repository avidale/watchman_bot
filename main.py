#!/usr/bin/python
# -*- coding: utf-8 -*-
import argparse
import telebot
import os
import random
from datetime import datetime
from flask import Flask, request
from pymongo import MongoClient

ON_HEROKU = os.environ.get('ON_HEROKU')
TOKEN = os.environ['TOKEN']
bot = telebot.TeleBot(TOKEN)

server = Flask(__name__)
TELEBOT_URL = 'telebot_webhook/'
BASE_URL = 'https://the-watchman-bot.herokuapp.com/'


MONGO_URL = 'mongodb://watchman_user1:watchman_password1@ds137441.mlab.com:37441/heroku_5c9l9qp5'
mongo_client = MongoClient(MONGO_URL)
mongo_db = mongo_client.get_default_database()
mongo_users = mongo_db.get_collection('users')
mongo_messages = mongo_db.get_collection('messages')


def try_insert_user(tg_bot_user):
    found = mongo_users.find_one({'tg_id': tg_bot_user.id})
    if found is not None:
        return
    mongo_users.insert_one(dict(
        tg_id=tg_bot_user.id,
        first_name=tg_bot_user.first_name,
        last_name=tg_bot_user.last_name,
        username=tg_bot_user.username,
        subscribed=True  # todo: ask for subscription
    ))


THE_QUESTIONS = [
    "Остановись!",
    "Кто ты?",
    "Откуда ты?",
    "Куда ты идёшь?"
]
with open('many_questions.txt', 'r', encoding='utf-8') as f:
    LONGLIST = list(f.readlines())


@server.route("/" + TELEBOT_URL)
def web_hook():
    bot.remove_webhook()
    bot.set_webhook(url=BASE_URL + TELEBOT_URL + TOKEN)
    return "!", 200


@server.route("/wakeup/")
def wake_up():
    # web_hook()
    for user in mongo_users.find():
        user_id = user.get('tg_id')
        if not user_id or not user.get('subscribed'):
            print("Do not write to user '{}'".format(user))
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
    try_insert_user(message.from_user)
    msg = dict(text=message.text, user_id=message.chat.id, from_user=True, timestamp=str(datetime.utcnow()))
    mongo_messages.insert_one(msg)
    if message.text == 'вопросик пожалуйста':
        response = random.choice(LONGLIST)
    else:
        response = "Я пока что не обладаю памятью, но я буду писать вам каждый вечер. Это моя работа."
    msg = dict(text=response, user_id=message.chat.id, from_user=False, timestamp=str(datetime.utcnow()))
    mongo_messages.insert_one(msg)
    bot.reply_to(message, response)


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
        server.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
        web_hook()


if __name__ == '__main__':
    main_new()
