

from datetime import datetime
import random
import uuid
from utils import write_to_file


FARM_PRODUCTS = {
    "vegetables": {
        "tomato": {"required_days": 70},
        "lettuce": {"required_days": 45},
        "carrot": {"required_days": 75},
        "potato": {"required_days": 90},
        "onion": {"required_days": 100},
        "cucumber": {"required_days": 60},
        "pepper": {"required_days": 80},
        "broccoli": {"required_days": 85},
        "cauliflower": {"required_days": 80}
    },
    "fruits": {
        "apple": {"required_days": 365},
        "orange": {"required_days": 730},
        "strawberry": {"required_days": 90},
        "grape": {"required_days": 180},
        "banana": {"required_days": 365},
        "peach": {"required_days": 365},
        "pear": {"required_days": 365},
        "cherry": {"required_days": 120}
    },
    "grains": {
        "wheat": {"required_days": 120},
        "corn": {"required_days": 80},
        "rice": {"required_days": 150},
        "oats": {"required_days": 100},
        "barley": {"required_days": 110}
    },
    "herbs": {
        "basil": {"required_days": 30},
        "mint": {"required_days": 45},
        "rosemary": {"required_days": 60},
        "thyme": {"required_days": 40},
        "sage": {"required_days": 50},
        "oregano": {"required_days": 35},
        "parsley": {"required_days": 55}
    },
    "animals": {
        "chicken": {"required_days": 180},
        "pig": {"required_days": 365},
        "fish": {"required_days": 90},
        "cow": {"required_days": 730},
        "bee": {"required_days": 30},
        "duck": {"required_days": 120},
        "goat": {"required_days": 365},
    },
    "derivatives": {
        "milk": {"required_days": 1, "required_animal": ["cow", "goat"]},
        "honey": {"required_days": 7, "required_animal": ["bee"]},
        "eggs": {"required_days": 1, "required_animal": ["chicken", "duck"]},
    }
}


def get_product_info(product_name: str):
    """Get farm product information by name from any type"""
    for product_type, products in FARM_PRODUCTS.items():
        if product_name in products:
            return {
                "name": product_name,
                "type": product_type,
                **products[product_name]
            }
    return None

def get_all_product_names():
    """Get all available farm product names"""
    all_products = []
    for product_type, products in FARM_PRODUCTS.items():
        all_products.extend(products.keys())
    return all_products

def get_all_crop_names():
    """Get all available crop names (excluding animals)"""
    crop_names = []
    for product_type, products in FARM_PRODUCTS.items():
        if product_type != "animals":
            crop_names.extend(products.keys())
    return crop_names

def get_all_animal_names():
    """Get all available animal names"""
    return list(FARM_PRODUCTS["animals"].keys())



class Farmer:
    def __init__(self, name: str):
        self.name = name

    def what_to_produce(self, context: dict = {}):
        return random.choice(get_all_product_names())

    def check_existing_animal(self, animal_name: str) -> bool:
        """Check if a specific animal already exists for this farmer"""
        import os
        import glob
        
        animal_path = f"data/farm/{self.name}/"
        if not os.path.exists(animal_path):
            return False
            
        pattern = os.path.join(animal_path, f"{animal_name}.*")
        existing_files = glob.glob(pattern)
        return len(existing_files) > 0

    def produce(self, context: dict = {}):
        product_name = context.get('produce', self.what_to_produce(context))
        product_info = get_product_info(product_name)


        if product_info["type"] == "derivatives":
            required_animals = product_info['required_animal']

            existing_animal = None
            for animal in required_animals:
                if self.check_existing_animal(animal):
                    existing_animal = animal
                    break
            
            # If no required animal exists, create one
            if existing_animal is None:
                animal_to_create = random.choice(required_animals)
                print(f"No {required_animals} found. Creating {animal_to_create}...")
                self.produce({'produce': animal_to_create})
            else:
                print(f"Using existing {existing_animal} for {product_name}")

        print(f"Producing {product_name}")
        box = f"data/farm/{self.name}/"
        filename = f"{product_name}.{uuid.uuid4().hex}"
        barcode = f"{product_name}:{datetime.now().timestamp()}:{self.name}"
        write_to_file(box, filename, barcode)




def main():
    farmer = Farmer("John")
    farmer.produce()
    farmer.produce({"produce": 'honey' })


if __name__ == "__main__":
    main()

