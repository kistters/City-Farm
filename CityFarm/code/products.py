# Dificuldades em zeros hexadecimais; calibrar com benchmarks reais.
PRODUCT_DIFFICULTIES = {
    "corn": 3,
    "wheat": 4,
    "celery": 3,
    "carrot": 3,
    "lettuce": 2,
    "tomato": 3,
}

def product_difficulty(name):
    return PRODUCT_DIFFICULTIES.get(name)
