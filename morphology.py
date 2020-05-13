import pymorphy2
morph = pymorphy2.MorphAnalyzer()


def gent(word):
    parses = morph.parse(word)
    if not parses:
        return word
    result = parses[0].inflect({'gent'}).word
    if word.istitle():
        result = result[0].upper() + result[1:]
    elif word.isupper():
        result = result.upper()
    return result

