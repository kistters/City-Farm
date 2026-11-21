"""Five ingredients available for browser PoW farming and single-item consumption."""
PRODUCTS = {
    "corn": {"difficulty": 3, "source": "field", "emoji": "🌽", "image": True},
    "wheat": {"difficulty": 4, "source": "field", "emoji": "🌾", "image": True},
    "carrot": {"difficulty": 3, "source": "field", "emoji": "🥕", "image": True},
    "lettuce": {"difficulty": 2, "source": "field", "emoji": "🥬", "image": True},
    "tomato": {"difficulty": 3, "source": "field", "emoji": "🍅", "image": True},
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
