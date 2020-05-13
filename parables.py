import random
import requests
import xmltodict

from bs4 import BeautifulSoup


ASK_OPINION = [
    'Что вы про это думаете?',
    'Как вы относитесь к этому?',
    'Как вы думаете, что это говорит о нашем мире?',
    'Удивительно, правда?',
    'Скажите, какие чувства у вас эта история вызывает?',
    'Давайте об этом поговорим.',
]


def opinions(func):
    def new_function(*args, ask_opinion=False, **kwargs):
        result = func(*args, **kwargs)
        if ask_opinion:
            result = result + '\n\n' + random.choice(ASK_OPINION)
        return result
    return new_function


def first_lower(s):
    return s[0].lower() + s[1:]


@opinions
def get_random_citation():
    r = requests.get('http://api.forismatic.com/api/1.0/?method=getQuote&format=json')
    if not r.ok:
        return 'Хм, что-то у меня не нашлось цитаты. \n' \
               'Но вы можете попросить меня рассказать притчу.'
    j = r.json()
    if j['quoteAuthor']:
        intro = random.choice([
            'Вот что однажды сказал(а) {}.',
            'Это цитата автора {}.',
            'Так говаривал {}.',
            'Говорят, что автор этой цитаты - {}.',
        ]).format(j['quoteAuthor'])
    else:
        intro = random.choice([
            'Вот вам цитата.',
            'Вот такую цитату удалось найти',
            'Итак, цитата.',
            'Зачитываю цитату',
            'Вот что мне сегодня принёс рандом',
        ])
    result = '{}\n\n{}\n\n<a href="{}">Источник</a>'.format(intro, j['quoteText'], j['quoteLink'])
    return result


@opinions
def get_random_parable():
    r = requests.get('https://pritchi.ru/action_random')
    if not r.ok:
        return 'С притчами что-то сегодня не выходит. ' \
               'Но вы можете попробовать меня найти вам случайную цитату.'
    soup = BeautifulSoup(r.text, features='html.parser')
    article = soup.find('article', {'class': 'article-area parable'})
    text = article.find('div').text
    if len(text) > 2000:
        text = text[:1000] + '...'
    title = article.find('h1').text
    subtitle = article.find('h2').text
    intro = random.choice([
        '{} "{}".',
        '{} под названием "{}".',
        '{}. Называется "{}".',
        'Вот вам {} "{}".',
    ]).format(subtitle, title)

    result = '{}\n\n{}\n\n<a href="{}">Источник</a>'.format(intro, text, r.url)
    return result


@opinions
def get_random_news(topic='science'):
    """ The topics are chosen from https://yandex.ru/news/export """
    if topic == 'random':
        topic = random.choice(['index', 'science', 'world'])
    r = requests.get('https://news.yandex.ru/{}.rss'.format(topic))
    if not r.ok:
        return 'Не получилось найти новость. Но я могу вам рассказать притчу или цитату.'
    news_list = xmltodict.parse(r.text)['rss']['channel']['item']
    item = random.choice(news_list)
    title = item['title']
    url = item['link']
    text = item['description']
    result = random.choice([
        f'Тут люди в городе <a href="{url}">поговаривают</a>, что {first_lower(title)}.\n{text}',
        f'Я <a href="{url}">где-то услышал</a>, новость, что {first_lower(title)}.',
        f'А вы уже слышали <a href="{url}">новость</a>, что {first_lower(title)}?\n{text}',
        f'Ходят <a href="{url}">слухи</a>, что {first_lower(title)}. Вроде бы {first_lower(text)}',
        f'Вот какую <a href="{url}">новость</a> я недавно слышал. {title}.',
        f'Простите, что я <a href="{url}">сплетничаю</a>, но уж больно любопытно. {title}.',
    ])
    return result
