"""Desafios visuais e aritméticos. Regras simples, sem persistência.

O navegador recebe o padrão para visualização. Isso não impede automação;
o servidor ainda valida cada resposta e só concede uma recompensa por desafio.
"""
import secrets

from products import FOOD, LEGACY_PRODUCTS

RANDOM = secrets.SystemRandom()
FARM_LEVELS = {
    1: {"size": 3, "cells": 3, "production": 1, "soil_cost": 10, "observe_seconds": 5},
    2: {"size": 6, "cells": 6, "production": 3, "soil_cost": 35, "observe_seconds": 5},
    3: {"size": 3, "cells": 4, "production": 4, "soil_cost": 20, "observe_seconds": 6},
}
WORK_REWARDS = {1: 5, 2: 10, 3: 15}
MEMORY_SYMBOLS = LEGACY_PRODUCTS


def create_farm(level):
    if type(level) is not int or level not in FARM_LEVELS:
        raise ValueError("Invalid level")
    rules = FARM_LEVELS[level]
    board = [None] * (rules["size"] ** 2)
    positions = RANDOM.sample(range(len(board)), rules["cells"])
    # Os ícones distintos da Multicultura são apenas um desafio de memória.
    symbols = RANDOM.sample(MEMORY_SYMBOLS, rules["cells"]) if level == 3 else [FOOD] * len(positions)
    for position, symbol in zip(positions, symbols):
        board[position] = symbol
    public = {
        "kind": "farmer", "level": level,
        "size": rules["size"], "pattern": board,
        "observe_seconds": rules["observe_seconds"],
    }
    return public, board


def create_work(level):
    if type(level) is not int or level not in WORK_REWARDS:
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
        if any(value is not None and
               (not isinstance(value, str) or value not in (FOOD,) + MEMORY_SYMBOLS)
               for value in answer):
            return False
        return answer == expected
    return type(answer) is int and answer == expected
