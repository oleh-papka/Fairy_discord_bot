import re
from Levenshtein import ratio, distance
from thefuzz import process
from words import profanity_words, exceptions, non_exceptions
from config import logger

char_eng_ukr = {
    'a': 'а',
    'c': 'с',
    'e': 'е',
    'i': 'і',
    'o': 'о',
    'p': 'р',
    'x': 'х',
    'y': 'у'
}


def profanity_check(test_word: str):

    test_word_input = test_word

    if test_word in non_exceptions:
        logger.info(f'On word: {test_word_input}')
        return True

    if test_word in exceptions:
        return False

    # Normalization
    test_word = test_word.lower()
    replacer = char_eng_ukr.get
    test_word = [replacer(n, n) for n in test_word]
    test_word = ''.join(test_word)
    test_word = re.sub(r"[^a-zA-Zа-яА-Я0-9]+", '', test_word)
    if len(test_word) == 0:
        return False

    if test_word in exceptions:
        return False

    if test_word in profanity_words:
        logger.info(f'On word: {test_word_input}')
        return True

    profanity_similar = process.extract(test_word, profanity_words, limit=10)

    for word in profanity_similar:
        word = word[0]
        simil = ratio(word, test_word)
        dist = distance(word, test_word)

        if simil >= 0.8:
            if dist <= 1:
                logger.info(f'On word: {test_word_input}, accuracy: {simil}, distance: {dist}, match: {test_word}')
                return True

        # if simil >= 0.8:
        #     if dist <= 3:
        #         logger.info(f'On word: {test_word_input}, accuracy: {simil}, distance: {dist}')
        #         return True

    return False



# words = []

# with open('src/profanity.txt', 'r') as words_file:
#     for word in words_file:
#         if len(word) > 2:
#             words.append(word.replace("\n", ""))


# words_additional_1 = []

# for word in words:
#     words_additional_1.append(word.replace('е', 'є'))


# words_additional_2 = []

# for word in words:
#     words_additional_2.append(word.replace('е', 'йе'))


# words_additional_3 = []

# for word in words:
#     words_additional_3.append(word.replace('о', 'а'))


# words.extend(words_additional_1)
# words.extend(words_additional_2)
# words.extend(words_additional_3)

# with open('src/words_1.py', 'w') as f:
#     f.write(str(list(set(words))))
