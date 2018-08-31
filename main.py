#!/usr/bin/python
# -*- coding: utf-8 -*-
import telebot
import os
from flask import Flask

ON_HEROKU = os.environ.get('ON_HEROKU')
TOKEN = os.environ['TOKEN']
bot = telebot.TeleBot(TOKEN)

server = Flask(__name__)
TELEBOT_URL = 'telebot_webhook/'
BASE_URL = 'https://the-watchman-bot.herokuapp.com/'


THE_QUESTIONS = [
    "Остановись!",
    "Кто ты?",
    "Откуда ты?",
    "Куда ты идёшь?"
]


@server.route("/" + TELEBOT_URL)
def web_hook():
    bot.remove_webhook()
    bot.set_webhook(url=BASE_URL + TELEBOT_URL + TOKEN)
    return "!", 200


@server.route("/wakeup/")
def wake_up():
    for utterance in THE_QUESTIONS:
        bot.send_message('71034798', utterance)
    return "Маам, ну ещё пять минуточек!", 200


if __name__ == '__main__':
    if ON_HEROKU:
        # get the heroku port
        port = int(os.environ.get('PORT', 17995))
        host = '0.0.0.0'
    else:
        host = '127.0.0.1'
        port = 5000
    print("running flask on the port {}".format(port))
    server.run(host=host, port=port)
    web_hook()
