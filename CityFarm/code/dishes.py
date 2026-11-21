"""Receitas da feira. Não são produtos: são pedidos de consumo de ingredientes."""
DISHES = {
    "rice_beans_beef": {
        "name": "Rice, Beans & Beef", "emoji": "🍛",
        "ingredients": {"rice": 1, "beans": 1, "beef": 1},
    },
    "omelette": {
        "name": "Tomato Omelette", "emoji": "🍳",
        "ingredients": {"eggs": 2, "tomato": 1},
    },
    "chicken_potatoes": {
        "name": "Chicken & Potatoes", "emoji": "🍗",
        "ingredients": {"chicken_meat": 1, "potato": 2},
    },
    "fruit_salad": {
        "name": "Fruit Salad", "emoji": "🥗",
        "ingredients": {"orange": 1, "banana": 1, "apple": 1},
    },
    "fish_rice": {
        "name": "Fish & Rice", "emoji": "🍣",
        "ingredients": {"fish": 1, "rice": 1},
    },
}


def public_dishes():
    return [
        {"id": code, "name": dish["name"], "emoji": dish["emoji"],
         "ingredients": dish["ingredients"],
         "ingredients_text": " + ".join(
             "{}× {}".format(count, ingredient.replace("_", " "))
             for ingredient, count in dish["ingredients"].items()
         )}
        for code, dish in DISHES.items()
    ]
