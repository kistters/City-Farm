import os
import random
import time
from typing import Any, Dict, List
from farm import Seed
from settings import DISASTERS, FARM_DIR
from utils import get_files_path_by_patterns, load_json, proof_of_work, write_json


def growth_daily(seed: Seed) -> Dict[str, Any]:
    """
    daily growth and return the proof product.
    """
    def _print_progress(seed: Seed, days: List[Any]) -> None:
        pass
        # print(f"Day {len(days)}: {seed.farmer}'s {seed.name} is growing...")
    
    seed_info = Seed.get_info(seed_name=seed.name)
    required_days = seed_info['required_days']
    
    proof = proof_of_work(data=seed, interactions=required_days, progress_callback=_print_progress)
    print(f"{seed.farmer}'s {seed.name} is done.")
    return proof


def lifecycle_manager() -> None:
    """
    Process all seeds in the farm directory, grow them, label, verify, and remove the seed file.
    Manages the complete lifecycle of plants and animals from seed to mature product.
    """    
    
    def misfortunate_event() -> bool:
        all_disasters = []
        for disasters in DISASTERS.values():
            all_disasters.extend(disasters.keys())
        disaster = random.choice(all_disasters)
        return random.choices([False, True], weights=[10, 1])[0], disaster
    
    seed_patterns = [os.path.join(FARM_DIR, "*", "seed.*")]
    seed_paths = get_files_path_by_patterns(patterns=seed_patterns)
    for seed_path in seed_paths:
        try:
            seed = Seed(**load_json(seed_path))
            product = growth_daily(seed=seed)
            happened, which_disaster = misfortunate_event()
            if happened:
                product['nonces'] = product['nonces'][:random.randint(1, len(product['nonces']))] + [which_disaster]
                
            folder, filename = os.path.dirname(seed_path), os.path.basename(seed_path)
            write_json(product, folder=folder, filename=filename)
            os.rename(seed_path, seed_path.replace("seed.", "ripe."))
        except Exception as e:
            print(f"Error processing seed at {seed_path}: {e}")
            

def run_lifecycle():
    """Run the lifecycle manager continuously every 60 seconds."""
    while True:
        try:
            lifecycle_manager()
        except Exception as e:
            print(f"Error: {e}")
            pass
        time.sleep(7)

if __name__ == "__main__":
    run_lifecycle()
