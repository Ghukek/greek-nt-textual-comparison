
import unicodedata


def normalize_word(word, normalize_final_sigma=True):
    word = word.lower()
    word = unicodedata.normalize("NFD", word)

    word = "".join(
        char
        for char in word
        if unicodedata.category(char) != "Mn"
    )

    word = "".join(
        char
        for char in word
        if not unicodedata.category(char).startswith("P")
    )

    word = word.replace("᾽", "").replace("ʼ", "")

    if normalize_final_sigma:
        word = word.replace("ς", "σ")

    return word

