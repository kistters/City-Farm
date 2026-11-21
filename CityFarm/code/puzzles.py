"""Desafios do City-Farm: geração isolada das regras de jogo.

A resposta correta nunca é aceita do navegador por confiança: é comparada
com a versão armazenada no Redis. Os padrões são enviados para observação,
portanto não constituem proteção contra bots.
"""
import secrets

from products import PRODUCTS

RANDOM = secrets.SystemRandom()
LEVEL_REWARD = {1: 1, 2: 2, 3: 3}
PRODUCT_NAMES = tuple(PRODUCTS)


def create_farm(level, product):
    if type(level) is not int or level not in LEVEL_REWARD:
        raise ValueError("Invalid level")
    if product not in PRODUCTS:
        raise ValueError("Unknown ingredient")
    size, count = {1: (3, 3), 2: (6, 6), 3: (3, 4)}[level]
    board = [None] * (size * size)
    for index in RANDOM.sample(range(len(board)), count):
        board[index] = RANDOM.choice(PRODUCT_NAMES) if level == 3 else product
    public = {
        "kind": "farmer", "level": level, "product": product,
        "size": size, "pattern": board,
        "observe_seconds": 6 if level == 3 else 5,
    }
    return public, board


def create_work(level):
    if type(level) is not int or level not in LEVEL_REWARD:
        raise ValueError("Invalid level")
    if level == 1:
        a, b = RANDOM.randint(1, 25), RANDOM.randint(1, 25)
        if RANDOM.choice((True, False)):
            expression, answer = "{} + {}".format(a, b), a + b
        else:
            expression, answer = "{} − {}".format(max(a, b), min(a, b)), abs(a - b)
    elif level == 2:
        a, b = RANDOM.randint(2, 12), RANDOM.randint(2, 12)
        if RANDOM.choice((True, False)):
            expression, answer = "{} × {}".format(a, b), a * b
        else:
            expression, answer = "{} ÷ {}".format(a * b, b), a
    else:
        a, b, c = RANDOM.randint(1, 12), RANDOM.randint(2, 8), RANDOM.randint(2, 8)
        if RANDOM.choice((True, False)):
            expression, answer = "{} + {} × {}".format(a, b, c), a + b * c
        else:
            expression, answer = "({} − {}) ÷ {}".format(a + b * c, a, c), b
    return {"kind": "citizen", "level": level, "expression": expression}, answer


def check_solution(challenge, answer):
    expected = challenge["expected"]
    if challenge["public"]["kind"] == "farmer":
        if not isinstance(answer, list) or len(answer) != len(expected):
            return False
        if any(value is not None and (not isinstance(value, str) or value not in PRODUCTS)
               for value in answer):
            return False
        return answer == expected
    return type(answer) is int and answer == expected
