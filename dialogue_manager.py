import json
import random
import re
import requests

from telebot import types


class Intents:
    GROW_COACH = 'grow_coach'
    GROW_COACH_INTRO = 'grow_coach_intro'
    GROW_COACH_EXIT = 'grow_coach_exit'
    HELP = 'help'
    INTRO = 'intro'
    PARABLE = 'parable'
    SUBSCRIBE = 'subscribe'
    UNSUBSCRIBE = 'unsubscribe'
    WANT_QUESTION = 'want_question'
    OTHER = 'other'
    PUSH_QUESTION = 'push_question'
    PUSH_MISS_YOU = 'push_miss_you'
    PUSH_UNSUBSCRIBE = 'push_unsubscribe'
    PUSH_ASK_FEEDBACK = 'push_ask_for_feedback'
    CITATION = 'citation'
    CONTACT_DEV = 'contact_developer'


REPLY_HELP = """
Здравствуйте!
Я создан, чтобы регулярно задавать вам вопросы. 
Какие-то из них могут оказаться для вас важными.
Доступные команды:
/coach - запустить сессию коучинга
/help - прочитать это сообщение
/subscribe - подписаться на ежедневные вопросы
/unsubscribe - отписаться от ежедневных вопросов
Если вы подпишетесь, вопросы будут приходить каждый вечер, в 21.30 по Московскому времени.
"""

REPLY_INTRO = """
Когда-то давно, тысячу лет назад, а может быть две, в один азиатский город пришёл путник. 
У врат его остановил стражник, и задал три вопроса:
- Кто ты? Откуда ты? И куда ты идёшь?
- Сколько тебе платят за твою работу? - спросил путник вместо ответа. 
- Две корзины риса в день
- Я буду платить тебе четыре корзины риса, если ты будешь задавать мне эти вопросы каждый день.

Я тоже в каком-то смысле стражник, и был создан по мотивам этой притчи. 
Но я ещё и бот, и поэтому мне даже не нужен рис. 
"""


def make_like_dislike_buttons(req_id=0, wtf=False):
    buttons = list()
    buttons.append(types.InlineKeyboardButton("\U0001F44D", callback_data="{}_pos".format(req_id)))
    if wtf:
        buttons.append(types.InlineKeyboardButton("\U0001F914", callback_data="{}_wtf".format(req_id)))
    buttons.append(types.InlineKeyboardButton("\U0001F44E", callback_data="{}_neg".format(req_id)))
    inline_markup = types.InlineKeyboardMarkup()
    inline_markup.add(*buttons)
    return inline_markup


def make_suggests(text='', intent=Intents.OTHER, user_object=None, req_id=0):
    if intent == Intents.WANT_QUESTION:
        return make_like_dislike_buttons(req_id=req_id)
    if intent == Intents.OTHER and random.random() < 0.9:
        return make_like_dislike_buttons(req_id=req_id, wtf=True)

    suggests_markup = types.ReplyKeyboardMarkup()
    if user_object is None:
        user_object = {}
    texts = [
        'Хочу вопрос!'
    ]
    if user_object.get('subscribed'):
        texts.append('Отписаться'),
    else:
        texts.append('Подписаться')
    if user_object.get('coach_state', {}).get('is_active'):
        texts.append('Завершить сессию')
    else:
        texts.append('Хочу коуч-сессию')

    if intent in {Intents.HELP, Intents.INTRO}:
        texts.extend(['Дай случайную цитату', 'Расскажи притчу', 'Связь с разработчиком'])
    elif intent == Intents.PARABLE and random.random() < 0.5:
        texts.insert(0, 'Ещё притчу!')
    elif intent == Intents.CITATION and random.random() < 0.5:
        texts.insert(0, 'Ещё цитату!')
    elif 'coach' not in intent and random.random() < 0.4:
        texts.append(random.choice([
            'Цитата', 'Притча', 'Случайная цитата', 'Случайная притча', 'Расскажи притчу', 'Хочу цитату'
        ]))
    suggests_markup.add(*[types.KeyboardButton(s) for s in texts])

    return suggests_markup


def classify_text(text, user_object=None):
    normalized = text.lower().strip()
    if user_object is None:
        user_object = {}
    # fast commands
    if text == '/help':
        return Intents.HELP
    if text == '/subscribe':
        return Intents.SUBSCRIBE
    if text == '/unsubscribe':
        return Intents.UNSUBSCRIBE
    if text == '/start':
        return Intents.INTRO
    if text == '/coach':
        return Intents.GROW_COACH_INTRO
    if text == '/citation':
        return Intents.CITATION
    if text == '/parable':
        return Intents.PARABLE

    # continue scenarios
    if user_object.get('last_intent') in {Intents.GROW_COACH, Intents.GROW_COACH_INTRO}:
        if user_object.get('coach_state').get('is_active'):
            # intent transitions within coach scenario are different
            if re.match('^.*(зак[оа]нч|заверш|прекра[тщ]).*(сессию|ко[ау]ч).*$', normalized):
                return Intents.GROW_COACH_EXIT
            return Intents.GROW_COACH

    # substrings
    if 'подпис' in normalized:
        return Intents.SUBSCRIBE
    if 'отпис' in normalized:
        return Intents.UNSUBSCRIBE
    if re.match('^(помоги.*|(хочу|начать|начни|начнем) ко[уа]ч[ -]*сессию.*|.*обсуд.*(проблем|дел).*)$', normalized):
        return Intents.GROW_COACH_INTRO
    if 'вопрос' in normalized:
        return Intents.WANT_QUESTION
    if 'цитат' in normalized or 'высказывани' in normalized:
        return Intents.CITATION
    if 'притч' in normalized or 'историю' in normalized or 'сказк' in normalized:
        return Intents.PARABLE
    if normalized in {'помощь', 'справка', 'хелп', 'help'}:
        return Intents.HELP
    if re.match('.*(связ|напи[сш]).*разраб', normalized):
        return Intents.CONTACT_DEV

    # fallback to boltalka
    return Intents.OTHER


def reply_with_boltalka(text, user_object=None):
    r = requests.post(
        "https://boltalka-as-a-service.herokuapp.com/boltalka_api",
        data=json.dumps({'utterance': text}),
        headers={'content-type': 'application/json'}
    )
    return json.loads(r.text)['response']