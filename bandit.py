import math
from collections import Counter


def sigmoid(x, beta=0.3):
    return 1.0 / (1.0 + math.exp(-x*beta))


def create_weights(texts, collection, pos=1, neg=-3, beta=0.3):
    feedbacked = collection.find(
        {'feedback': {'$exists': True}, 'intent': {'$in': ['want_question', 'push_question']}}
    )
    counters = {'pos': Counter(), 'neg': Counter()}
    for record in feedbacked:
        counters[record['feedback']][record['text'].strip()] += 1
    raw_scores = [counters['pos'][text] * pos + counters['neg'][text] * neg for text in texts]
    weights = [sigmoid(x, beta=beta) for x in raw_scores]
    return weights


def unsullied_candidates(texts, collection):
    # return questions that were never rated negatively
    # source: texts (pre-written questions) and collection (including generated questions)
    texts = {t.strip() for t in texts}
    feedbacked = collection.find(
        {'feedback': {'$exists': True}, 'intent': {'$in': ['want_question', 'push_question', 'unique_question']}}
    )
    counters = {'pos': Counter(), 'neg': Counter()}
    for record in feedbacked:
        text = record['text'].strip()
        # skip citiations, parables and news
        if text not in texts and ('href' in text.lower() or 'сегодня' in text.lower()):
            continue
        counters[record['feedback']][text] += 1
    base = texts.union(set(counters['pos'].keys()))
    result = [text for text in base if counters['neg'][text] == 0]
    return result
