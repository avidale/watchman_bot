import random
import requests

from bs4 import BeautifulSoup


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
