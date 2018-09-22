#!/usr/bin/python
# -*- coding: utf-8 -*-
import telebot
import os
import time
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

ON_HEROKU = os.environ.get('ON_HEROKU')
TOKEN = os.environ['TOKEN']
bot = telebot.TeleBot(TOKEN)

server = Flask(__name__)
TELEBOT_URL = 'telebot_webhook/'
BASE_URL = 'https://the-watchman-bot.herokuapp.com/'
DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///watchman_local.db')

server.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
db = SQLAlchemy(server)


THE_QUESTIONS = [
    "Остановись!",
    "Кто ты?",
    "Откуда ты?",
    "Куда ты идёшь?"
]


class StoredMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Unicode())
    user_id = db.Column(db.Integer)

    def __repr__(self):
        return '<Message "{}" from "{}">'.format(self.text, self.user_id)
        
        
class StoredUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, unique=True)

    def __repr__(self):
        return '<User "{}">'.format(self.user_id)


@server.route("/" + TELEBOT_URL)
def web_hook():
    bot.remove_webhook()
    bot.set_webhook(url=BASE_URL + TELEBOT_URL + TOKEN)
    return "!", 200


@server.route("/wakeup/")
def wake_up():
    for user in StoredUser.query.all():
        print("Writing to user '{}'".format(user.user_id))
        for utterance in THE_QUESTIONS:
            bot.send_message(user.user_id, utterance)
            time.sleep(0.01)
    return "Маам, ну ещё пять минуточек!", 200


@bot.message_handler(func=lambda message: True)
def process_message(message):
    msg = StoredMessage(text=message.text, user_id=message.chat.id)
    print(msg)
    db.session.add(msg)
    db.session.commit()
    print('total number of messages: {}'.format(
        len(StoredMessage.query.all()))
    )
    found_user = StoredUser.query.filter_by(user_id=message.chat.id).first()
    if found_user:
        print("found existing user '{}'".format(found_user))
    else:
        new_user = StoredUser(user_id=message.chat.id)
        db.session.add(new_user)
        db.session.commit()
        print("added user '{}'".format(new_user))


if __name__ == '__main__':
    db.create_all()
    if ON_HEROKU:
        # get the heroku port
        port = int(os.environ.get('PORT', 17995))
        host = '0.0.0.0'
    else:
        host = '127.0.0.1'
        port = 5000
    if ON_HEROKU:
        print("running flask on the port {}".format(port))
        server.run(host=host, port=port)
        web_hook()
    else:
        bot.remove_webhook()
        bot.polling()
