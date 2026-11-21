"""Catálogo único de ingredientes, origens e custo de PoW.

Nesta etapa, animais são origens dos produtos; criação e ciclos de
produção recorrente ficam para uma evolução posterior.
"""
PRODUCTS = {
    "corn": {"difficulty": 3, "source": "field", "emoji": "🌽", "image": True},
    "wheat": {"difficulty": 4, "source": "field", "emoji": "🌾", "image": True},
    "celery": {"difficulty": 3, "source": "field", "emoji": "🥬", "image": True},
    "carrot": {"difficulty": 3, "source": "field", "emoji": "🥕", "image": True},
    "lettuce": {"difficulty": 2, "source": "field", "emoji": "🥬", "image": True},
    "tomato": {"difficulty": 3, "source": "field", "emoji": "🍅", "image": True},
    "rice": {"difficulty": 3, "source": "field", "emoji": "🍚"},
    "beans": {"difficulty": 3, "source": "field", "emoji": "🫘"},
    "potato": {"difficulty": 3, "source": "field", "emoji": "🥔"},
    "orange": {"difficulty": 3, "source": "tree", "emoji": "🍊"},
    "banana": {"difficulty": 3, "source": "tree", "emoji": "🍌"},
    "apple": {"difficulty": 3, "source": "tree", "emoji": "🍎"},
    "milk": {"difficulty": 3, "source": "cow", "emoji": "🥛"},
    "beef": {"difficulty": 4, "source": "cow", "emoji": "🥩"},
    "pork": {"difficulty": 4, "source": "pig", "emoji": "🥓"},
    "eggs": {"difficulty": 3, "source": "chicken", "emoji": "🥚"},
    "chicken_meat": {"difficulty": 4, "source": "chicken", "emoji": "🍗"},
    "fish": {"difficulty": 3, "source": "pond", "emoji": "🐟"},
}
PRODUCT_DIFFICULTIES = {name: value["difficulty"] for name, value in PRODUCTS.items()}


def product_difficulty(name):
    return PRODUCT_DIFFICULTIES.get(name)


def public_catalog():
    return [
        {"name": name, "source": data["source"], "emoji": data["emoji"],
         "image": data.get("image", False)}
        for name, data in PRODUCTS.items()
    ]
