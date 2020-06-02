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
