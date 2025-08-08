

from dataclasses import dataclass
from datetime import datetime
import os
import random
from typing import Any, Dict, List, Optional
from utils import get_files_path_by_patterns, load_json, proof_of_work, to_hash, verify_proof_of_work, write_json

# Constants for paths
DATA_DIR = os.path.join("data")
FARM_JSON_PATH = os.path.join(DATA_DIR, "farm.json")
FARM_DIR = os.path.join(DATA_DIR, "farm")

FARM_PRODUCTS = load_json(FARM_JSON_PATH)

def get_product_info(product_name: str) -> Optional[Dict[str, Any]]:
    """
    Get farm product information by name from any type.
    Returns a dict with product info, or None if not found.
    """
    for product_type, products in FARM_PRODUCTS.items():
        if product_name in products:
            return {
                "name": product_name,
                "type": product_type,
                **products[product_name]
            }
    print(f"Warning: Product '{product_name}' not found in FARM_PRODUCTS.")
    return None

def get_all_product_names() -> List[str]:
    """Get all available farm product names."""
    all_products = []
    for products in FARM_PRODUCTS.values():
        all_products.extend(products.keys())
    return all_products

def get_all_crop_names() -> List[str]:
    """Get all available crop names (excluding animals)."""
    crop_names = []
    for product_type, products in FARM_PRODUCTS.items():
        if product_type != "animals":
            crop_names.extend(products.keys())
    return crop_names

def get_all_animal_names() -> List[str]:
    """Get all available animal names."""
    animals = FARM_PRODUCTS.get("animals", {})
    if not animals:
        print("Warning: No animals found in FARM_PRODUCTS.")
    return list(animals.keys())

@dataclass
class Seed:
    name: str
    farmer: str
    planted_at: float
    produced_by: Optional[str] = None

class Farmer:
    def __init__(self, name: str):
        self.name = name

    def what_to_produce(self, context: Optional[Dict[str, Any]] = None) -> str:
        """Decide what to produce next."""
        context = context or {}
        return random.choice(get_all_product_names())

    def produce(self, context: Optional[Dict[str, Any]] = None) -> Optional[Seed]:
        """
        Produce a seed, possibly using an animal if required.
        Returns the Seed object or None if failed.
        """
        context = context or {}
        seed_name = context.get('produce') or self.what_to_produce(context)
        seed_info = get_product_info(seed_name)
        if not seed_info:
            print(f"Error: Could not find info for seed '{seed_name}'.")
            return None
        animal = None
        if seed_info["type"] == "derivatives":
            required_animals = seed_info.get('required_animal', [])
            animal_patterns = [os.path.join(FARM_DIR, self.name, f"{animal}.*") for animal in required_animals]
            animal_paths = get_files_path_by_patterns(patterns=animal_patterns)
            if not animal_paths:
                seed_name = random.choice(required_animals)
                print(f"No {required_animals} found. Creating {seed_name}...")
            else:
                animal = os.path.basename(random.choice(animal_paths))
                print(f"Using existing {animal} for {seed_name}")
        seed = Seed(name=seed_name, farmer=self.name, planted_at=datetime.now().timestamp(), produced_by=animal)
        planting(seed=seed)
        return seed

def planting(seed: Seed) -> str:
    """
    Save the seed to a file and return the file path.
    """
    filename = to_hash(seed)[:9]
    return write_json(seed, os.path.join(FARM_DIR, seed.farmer), f"seed.{seed.name}.{filename}")

def print_progress(seed: Seed, days: List[Any]) -> None:
    print(f"Day {len(days)}: {seed.farmer}'s {seed.name} is growing...")

def growth_daily(seed: Seed, required_days: int) -> Dict[str, Any]:
    """
    Simulate daily growth and return the proof object.
    """
    proof = proof_of_work(data=seed, interactions=required_days, progress_callback=print_progress)
    proof['seed'] = proof.pop('data')
    print(f"{seed.farmer}'s {seed.name} is done.")
    return proof

def labeling(product: Dict[str, Any]) -> str:
    """
    Save the product to a file and return the file path.
    """
    filename = to_hash(product)[:9]
    seed = product['seed']
    return write_json(product, os.path.join(FARM_DIR, seed.farmer), f"{seed.name}.{filename}")

def verify_growth(product_path: str) -> bool:
    """
    Verify the proof of work for a grown product.
    """
    try:
        product = load_json(product_path)
        seed = Seed(**product['seed'])
        return verify_proof_of_work(data=seed, nonces=product['nonces'])
    except Exception as e:
        print(f"Error verifying growth for {product_path}: {e}")
        return False

def clock() -> None:
    """
    Process all seeds in the farm directory, grow them, label, verify, and remove the seed file.
    """
    seed_patterns = [os.path.join(FARM_DIR, "*", "seed.*")]
    seed_paths = get_files_path_by_patterns(patterns=seed_patterns)
    for seed_path in seed_paths:
        try:
            seed = Seed(**load_json(seed_path))
            seed_info = get_product_info(seed.name)
            if not seed_info:
                print(f"Error: No info for seed {seed.name}.")
                continue
            product = growth_daily(seed=seed, required_days=seed_info['required_days'])
            product_path = labeling(product=product)
            verify_growth(product_path)
            os.remove(seed_path)
        except Exception as e:
            print(f"Error processing seed at {seed_path}: {e}")

def main() -> None:
    """
    Main entrypoint for running the farm simulation.
    """
    farmer = Farmer("John")
    farmer.produce()

if __name__ == "__main__":
    main()
