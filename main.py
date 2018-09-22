#!/usr/bin/python
# -*- coding: utf-8 -*-
import telebot
import os
import time
from datetime import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

ON_HEROKU = os.environ.get('ON_HEROKU')
TOKEN = os.environ['TOKEN']
bot = telebot.TeleBot(TOKEN)

server = Flask(__name__)
TELEBOT_URL = 'telebot_webhook/'
BASE_URL = 'https://the-watchman-bot.herokuapp.com/'
DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///watchman_local.db')

server.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
db = SQLAlchemy(server)
migrate = Migrate(server, db)

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
    from_user = db.Column(db.Boolean)
    process_time = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return '<Message "{}" {} "{}" at {}>'.format(self.text, "from" if self.from_user else "to", self.user_id, self.process_time)
        
        
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
    web_hook()
    for user in StoredUser.query.all():
        print("Writing to user '{}'".format(user.user_id))
        for utterance in THE_QUESTIONS:
            bot.send_message(user.user_id, utterance)
            time.sleep(0.01)
            msg = StoredMessage(text=utterance, user_id=user.user_id, from_user=False)
            db.session.add(msg)
    db.session.commit()
    return "Маам, ну ещё пять минуточек!", 200


@bot.message_handler(func=lambda message: True)
def process_message(message):
    msg = StoredMessage(text=message.text, user_id=message.chat.id, from_user=True)
    print(msg)
    db.session.add(msg)
    response = "Я пока что не обладаю памятью, но я буду писать вам каждый вечер. Это моя работа."
    db.session.add(StoredMessage(text=response, user_id=message.chat.id, from_user=False))
    bot.reply_to(message, response)
    print('total number of messages: {}'.format(
        len(StoredMessage.query.all()))
    )
    found_user = StoredUser.query.filter_by(user_id=message.chat.id).first()
    if found_user:
        print("found existing user '{}'".format(found_user))
    else:
        new_user = StoredUser(user_id=message.chat.id)
        db.session.add(new_user)
        print("added user '{}'".format(new_user))
    db.session.commit()


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
