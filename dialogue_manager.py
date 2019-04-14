from telebot import types
import requests
import json


class Intents:
    HELP = 'help'
    SUBSCRIBE = 'subscribe'
    UNSUBSCRIBE = 'unsubscribe'
    WANT_QUESTION = 'want_question'
    OTHER = 'other'


REPLY_HELP = """
Здравствуйте!
Я создан, чтобы регулярно задавать вам вопросы. 
Какие-то из них могут оказаться для вас важными.
Доступные команды:
/help - прочитать это сообщение
/subscribe - подписаться на ежедневные вопросы
/unsubscribe - отписаться от ежедневных вопросов
"""


def make_suggests(text='', intent=Intents.OTHER, user_object=None):
    if user_object is None:
        user_object = {}
    texts = [
        'Хочу вопрос!'
    ]
    if user_object.get('subscribed'):
        texts.append('Отписаться'),
    else:
        texts.append('Подписаться')
    markup = types.ReplyKeyboardMarkup()
    markup.add(*[types.KeyboardButton(s) for s in texts])
    return markup


def classify_text(text):
    # fast commands
    if text == '/help' or text == '/start':
        return Intents.HELP
    if text == '/subscribe':
        return Intents.SUBSCRIBE
    if text == 'unsubscribe':
        return Intents.UNSUBSCRIBE
    # substrings
    if 'подпис' in text.lower():
        return Intents.SUBSCRIBE
    if 'отпис' in text.lower():
        return Intents.UNSUBSCRIBE
    if 'вопрос' in text.lower():
        return Intents.WANT_QUESTION
    # fallback to boltalka
    return Intents.OTHER


def reply_with_boltalka(text):
    # return "Я пока что не обладаю памятью, но я буду писать вам каждый вечер. Это моя работа."
    r = requests.post(
        "https://matchast-chatbot.herokuapp.com/boltalka_api",
        data=json.dumps({'utterance': text}),
        headers={'content-type': 'application/json'}
    )
    return json.loads(r.text)['response']