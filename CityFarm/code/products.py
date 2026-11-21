"""Catálogo único: cinco ingredientes disponíveis na fazenda e no mercado."""
PRODUCTS = {
    "corn": {"source": "field", "emoji": "🌽", "image": True},
    "wheat": {"source": "field", "emoji": "🌾", "image": True},
    "carrot": {"source": "field", "emoji": "🥕", "image": True},
    "lettuce": {"source": "field", "emoji": "🥬", "image": True},
    "tomato": {"source": "field", "emoji": "🍅", "image": True},
}


def public_catalog():
    return [
        {"name": name, "source": data["source"], "emoji": data["emoji"],
         "image": data["image"]}
        for name, data in PRODUCTS.items()
    ]
