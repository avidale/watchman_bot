import requests
import random
import re

from morphology import gent

from bs4 import BeautifulSoup

from parables import opinions

HEADER = {
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:32.0) Gecko/20100101 Firefox/32.0'
}
SITE_ROOT = 'http://kakoysegodnyaprazdnik.ru'


text2month = {
    'yanvar': 1,
    'fevral': 2,
    'mart': 3,
    'aprel': 4,
    'may': 5,
    'iyun': 6,
    'iyul': 7,
    'avgust': 8,
    'sentyabr': 9,
    'oktyabr': 10,
    'noyabr': 11,
    'dekabr': 12,
}


def text2date(text):
    toks = text.split('/')
    m = text2month[toks[2]]
    d = int(toks[3])
    return '{:02}.{:02}'.format(m, d)


def parse_event_text(doc):
    """
    Split the `text` field, into event, its translation, and country.
    Optionally, parse its date and convert to a more convenient format.
    """
    doc['event'] = None
    doc['country'] = None
    doc['alias'] = None
    t = doc['text'][2:]
    parts = t.split(' - ', 1)
    if len(parts) > 1:
        doc['country'] = parts[1].strip()
    lhs = parts[0]
    if '(' in lhs and ')' in lhs:
        parts = lhs.split('(', 1)
        doc['alias'] = parts[1].replace(')', '').strip()
        lhs = parts[0]
    doc['event'] = lhs.strip()
    if 'suffix' in doc:
        doc['date'] = text2date(doc['suffix'])


def get_today_events(url=SITE_ROOT):
    """ Go to the url and parse out all the events at this day """
    docs = []
    r = requests.get(url, headers=HEADER)
    r.encoding = r.apparent_encoding
    day = BeautifulSoup(r.text, features='lxml')
    listing = day.find('div', {'class': 'listing_wr'})
    for d in listing.findAll('div', {'itemprop': ['acceptedAnswer', 'suggestedAnswer']}):
        doc = {
            'text': re.sub('\\d+ (года?|лет)$', '', d.text),
            'upvotes': int(d.find('meta')['content']),
            # 'suffix': suffix,
        }
        parse_event_text(doc)
        docs.append(doc)
    return docs


def is_like_religion(text):
    text = text.lower()
    if re.match('.*(свят|бог|апостол|господ|икон|бож|именин)', text):
        return True
    return False


@opinions
def get_random_event(url=SITE_ROOT):
    events = get_today_events(url=url)
    w = [
        e['upvotes'] ** 0.5 * (0.1 if is_like_religion(e['event']) else 1)
        for e in events
    ]
    event = random.choices(events, weights=w)[0]
    if event['country']:
        country = gent(event['country'])
        result = random.choice([
            f'Сегодня в {country} отмечают {event["event"]}.',
            f'Сегодня празднуют {event["event"]} в {country}.',
            f'Мне тут рассказали, что сегодня {event["event"]} в {country}.',
            f'Сегодня особенный день: в {country} отмечают {event["event"]}.',
        ])
    else:
        result = random.choice([
            f'Сегодня отмечают {event["event"]}.',
            f'Сегодня празднуют {event["event"]}.',
            f'Мне тут рассказали, что сегодня {event["event"]}.',
            f'Сегодня необычный день: празднуют {event["event"]}.',
        ])
    return result
