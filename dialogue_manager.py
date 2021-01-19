import json
import random
import re
import requests

from telebot import types

PUNCT = set('.?,;!:')


EMPTY_STATE = {
    'coach_state': {},
}


class Intents:
    GROW_COACH = 'grow_coach'
    GROW_COACH_INTRO = 'grow_coach_intro'
    GROW_COACH_EXIT = 'grow_coach_exit'
    GROW_COACH_FEEDBACK = 'grow_coach_feedback'
    HELP = 'help'
    INTRO = 'intro'
    PARABLE = 'parable'
    SUBSCRIBE = 'subscribe'
    UNSUBSCRIBE = 'unsubscribe'
    WANT_QUESTION = 'want_question'
    UNIQUE_QUESTION = 'unique_question'
    OTHER = 'other'
    PUSH_QUESTION = 'push_question'
    PUSH_SPECIAL = 'push_special'
    PUSH_MISS_YOU = 'push_miss_you'
    PUSH_UNSUBSCRIBE = 'push_unsubscribe'
    PUSH_ASK_FEEDBACK = 'push_ask_for_feedback'
    CITATION = 'citation'
    NEWS = 'news'
    DAY_TODAY = 'today_events'
    CONTACT_DEV = 'contact_developer'


REPLY_HELP = """
Здравствуйте!
Я создан, чтобы регулярно задавать вам вопросы. 
Какие-то из них могут оказаться для вас важными.
Если вы подпишетесь, новые вопросы будут приходить каждый вечер, в 21.30 по Московскому времени.

Кроме вопросов, я могу рассказать вам цитату или притчу или обсудить свежие сплетни.
А ещё я могу просто болтать с вами по-русски или по-английски.
Я часто несу чепуху, потому что я не очень образован и у меня плохая память.
Но иногда я случайно попадаю в точку.

Доступные команды:
/ask - получить вопрос для самоанализа
/subscribe - подписаться на ежедневные вопросы
/unsubscribe - отписаться от ежедневных вопросов
/coach - получить помощь в достижении цели
/help - прочитать это сообщение
/parable - случайная притча
/citation - случайная цитата
/news  - случайная новость
/today - что отмечают сегодня

Создано с любовью ко всему живому by @cointegrated
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
    # for 30% of questions, we generate like-dislike buttons
    if (intent == Intents.WANT_QUESTION or intent == Intents.NEWS) and random.random() < 0.7:
        return make_like_dislike_buttons(req_id=req_id)
    # for 30% of conversational messages, we generate like-dislike buttons with the third option
    if intent == Intents.OTHER and random.random() < 0.7:
        return make_like_dislike_buttons(req_id=req_id, wtf=True)

    suggests_markup = types.ReplyKeyboardMarkup()
    if user_object is None:
        user_object = {}
    texts = []
    coach_state = user_object.get('coach_state', {}) or {}
    if coach_state.get('is_active'):
        if coach_state.get('intro'):
            texts.append(random.choice(['Окей', 'Поехали!', 'Хорошо', 'Понятно']))
        if coach_state.get('ask_feedback'):
            texts.append(random.choice(['Круто!', 'Отлично', 'Очень понравилась', 'Офигенно']))
            texts.append(random.choice(['Нормально', 'Сойдёт', 'Неплохо']))
            texts.append(random.choice(['Так себе', 'Не понравилась', 'Не очень']))
        else:
            texts.append('Завершить сессию')
    else:
        texts.append('Хочу вопрос!')
        if user_object.get('subscribed'):
            texts.append('Отписаться'),
        else:
            texts.append('Подписаться')
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
    normalized = re.sub('[^a-zа-яё0-9]+', ' ', text.lower()).strip()
    if user_object is None:
        user_object = {}
    # fast commands
    if text == '/help':
        return Intents.HELP
    if text == '/ask':
        return Intents.WANT_QUESTION
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
    if text == '/news':
        return Intents.NEWS
    if text == '/today':
        return Intents.DAY_TODAY

    # interrupt scenarios
    if normalized == 'хочу вопрос':
        return Intents.WANT_QUESTION
    if normalized == 'отписаться':
        return Intents.UNSUBSCRIBE

    # continue scenarios
    coach_state = user_object.get('coach_state') or {}
    if user_object.get('last_intent') in {Intents.GROW_COACH, Intents.GROW_COACH_INTRO}:
        if coach_state.get('is_active'):
            # intent transitions within coach scenario are different
            if re.match('^.*(зак[оа]нч|заверш|прекра[тщ]).*(сессию|ко[ау]ч).*$', normalized):
                return Intents.GROW_COACH_EXIT
            if coach_state.get('ask_feedback'):
                return Intents.GROW_COACH_FEEDBACK
            return Intents.GROW_COACH
    if coach_state.get('ask_feedback'):  # we need this additional 'if' after forcing exit from coach session
        return Intents.GROW_COACH_FEEDBACK

    # substrings
    if 'подпис' in normalized:
        return Intents.SUBSCRIBE
    if 'отпис' in normalized:
        return Intents.UNSUBSCRIBE
    if re.match('^(помоги.*|(хочу|начать|начни|начнем) ко[уа]ч[ -]*сессию.*|.*обсуд.*(проблем|дел).*)$', normalized):
        return Intents.GROW_COACH_INTRO
    if 'вопрос' in normalized:
        if 'генер' in normalized:
            return Intents.UNIQUE_QUESTION
        return Intents.WANT_QUESTION
    if 'цитат' in normalized or 'высказывани' in normalized:
        return Intents.CITATION
    if 'притч' in normalized or 'историю' in normalized or 'сказк' in normalized:
        return Intents.PARABLE
    if normalized in {'помощь', 'справка', 'хелп', 'help'}:
        return Intents.HELP
    if re.match('.*(свя[зж]|напи[сш]).*разраб', normalized):
        return Intents.CONTACT_DEV
    if re.match('расск.*новост', normalized):
        return Intents.NEWS
    if 'сегодня' in normalized and re.match('.*(день|праздник|дата|событие|отмечают|празднуют)', normalized):
        return Intents.DAY_TODAY

    # fallback to boltalka
    return Intents.OTHER


def remove_spaces(text):
    result = []
    for i, s in enumerate(text.split()):
        if s[0] not in PUNCT and len(result) > 0:
            result.append(' ')
        result.append(s)
    return ''.join(result)


def reply_with_boltalka(text, user_object=None):
    h = (user_object or {}).get('history', []) + [text]
    req_data = {
        'utterance': text,
        'history': h,
    }
    r = requests.post(
        # "https://boltalka-as-a-service.herokuapp.com/boltalka_api",
        'http://dialogue-as-a-service.toys.dialogic.digital/boltalka_api',
        data=json.dumps(req_data),
        headers={'content-type': 'application/json'}
    )
    return remove_spaces(json.loads(r.text)['response']).capitalize()
