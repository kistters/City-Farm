

from dataclasses import dataclass
from datetime import datetime
import random
from utils import load_json, proof_of_work, to_hash, verify_proof_of_work, write_json


FARM_PRODUCTS = load_json('data/farm.json')

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

@dataclass
class Seed:
    name: str
    farmer: str
    planted_at: float


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
        seed_name = context.get('produce', self.what_to_produce(context))
        seed_info = get_product_info(seed_name)


        if seed_info["type"] == "derivatives":
            required_animals = seed_info['required_animal']

            existing_animal = None
            for animal in required_animals:
                if self.check_existing_animal(animal):
                    existing_animal = animal
                    break
            
            if existing_animal is None:
                animal_to_create = random.choice(required_animals)
                print(f"No {required_animals} found. Creating {animal_to_create}...")
                self.produce({'produce': animal_to_create})
            else:
                print(f"Using existing {existing_animal} for {seed_name}")

        seed = Seed(name=seed_name, farmer=self.name, planted_at=datetime.now().timestamp() )
        product = growth_daily(seed=seed, required_days=seed_info['required_days'])
        product_path = labeling(product=product)
        verify_growth(product_path)
        return product


def print_progress(seed, days):
    print(f"Day {len(days)}: Growing {seed.name}...")
    
def growth_daily(seed: Seed, required_days: int) -> dict:
    proof = proof_of_work(data=seed, interactions=required_days, progress_callback=print_progress)
    proof['seed'] = proof.pop('data')
    return proof

def labeling(product) -> str:
    filename = to_hash(product)[:9]
    seed = product['seed']
    return write_json(product, f"farm/{seed.farmer}/", f"{seed.name}.{filename}")

def verify_growth(product_path):
    product = load_json(product_path)
    seed = Seed(**product['seed'])  
    return verify_proof_of_work(data=seed, nonces=product['nonces'])


def main():
    farmer = Farmer("John")
    # farmer.produce()
    farmer.produce({"produce": 'honey' })


if __name__ == "__main__":
    main()
