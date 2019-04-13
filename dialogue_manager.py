from telebot import types


def make_suggests():
    texts = [
        'Хочу вопрос!',
        'Отписаться',
        'Подписаться'
    ]
    markup = types.ReplyKeyboardMarkup(row_width=len(texts))
    markup.add(*[types.KeyboardButton(s) for s in texts])
    return markup


def classify_text(text):
    if 'подпис' in text.lower():
        return 'subscribe'
    if 'отпис' in text.lower():
        return 'unsubscribe'
    if 'вопрос' in text.lower():
        return 'want_question'
    return 'other'


def reply_with_boltalka(text):
    return "Я пока что не обладаю памятью, но я буду писать вам каждый вечер. Это моя работа."
