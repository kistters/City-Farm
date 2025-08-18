

from dataclasses import dataclass
from datetime import datetime
import os
import random
from typing import Any, Dict, List, Optional
from utils import get_files_path_by_patterns, load_json, proof_of_work, to_hash, verify_proof_of_work, write_json

# Constants for paths
DATA_DIR = os.path.join("data")
SEEDS_JSON_PATH = os.path.join("src/seeds.json")
FARM_DIR = os.path.join(DATA_DIR, "farm")

FARM_SEEDS = load_json(SEEDS_JSON_PATH)

def get_seed_info(seed_name: str) -> Optional[Dict[str, Any]]:
    """
    Get farm seed information by name from any type.
    Returns a dict with seed info, or None if not found.
    """
    for seed_type, seeds in FARM_SEEDS.items():
        if seed_name in seeds:
            return {
                "name": seed_name,
                "type": seed_type,
                **seeds[seed_name]
            }
    print(f"Warning: Seed '{seed_name}' not found in FARM_SEEDS.")
    return None

def get_all_seeds_names() -> List[str]:
    """Get all available farm seed names."""
    all_seeds = []
    for seeds in FARM_SEEDS.values():
        all_seeds.extend(seeds.keys())
    return all_seeds

def get_all_crop_names() -> List[str]:
    """Get all available crop names (excluding animals)."""
    crop_names = []
    for seed_type, seeds in FARM_SEEDS.items():
        if seed_type != "animals":
            crop_names.extend(seeds.keys())
    return crop_names

def get_all_animal_names() -> List[str]:
    """Get all available animal names."""
    animals = FARM_SEEDS.get("animals", {})
    if not animals:
        print("Warning: No animals found in FARM_SEEDS.")
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
        return random.choice(get_all_seeds_names())

    def produce(self, context: Optional[Dict[str, Any]] = None) -> Optional[Seed]:
        """
        Produce a seed, possibly using an animal if required.
        Returns the Seed object or None if failed.
        """
        context = context or {}
        seed_name = context.get('produce') or self.what_to_produce(context)
        seed_info = get_seed_info(seed_name)
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

def lifecycle_manager() -> None:
    """
    Process all seeds in the farm directory, grow them, label, verify, and remove the seed file.
    Manages the complete lifecycle of plants and animals from seed to mature product.
    """
    seed_patterns = [os.path.join(FARM_DIR, "*", "seed.*")]
    seed_paths = get_files_path_by_patterns(patterns=seed_patterns)
    for seed_path in seed_paths:
        try:
            seed = Seed(**load_json(seed_path))
            seed_info = get_seed_info(seed.name)
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
