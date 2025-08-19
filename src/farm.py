from dataclasses import dataclass
from datetime import datetime
import os
import random
import time
from typing import Any, Dict, List, Optional
from utils import get_files_path_by_patterns, load_json, to_hash, verify_proof_of_work, write_json
from settings import FARM_DIR, FARM_SEEDS



@dataclass
class Seed:
    name: str
    farmer: str = None
    planted_at: float = None
    
    @classmethod
    def get_info(cls, seed_name: str) -> Optional[Dict[str, Any]]:
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
                
        raise Exception(f"seed.{seed_name}.not_found")
    
    @classmethod
    def get_all_names(cls) -> List[str]:
        """Get all available farm seed names."""
        all_seeds = []
        for seeds in FARM_SEEDS.values():
            all_seeds.extend(seeds.keys())
        return all_seeds

# @dataclass
# class Product:
#     id: str
#     seed: Seed
#     nonces: List[int]
    
#     def verify(self) -> bool:
#         return verify_proof_of_work(data=self.seed, nonces=self.nonces)
    
#     def __str__(self) -> str:
#         return f"{self.data['name']}.{to_hash(self.data)[:9]}"

class Farmer:
    def __init__(self, name: str):
        self.name = name

    def what_to_produce(self, context: Optional[Dict[str, Any]] = None) -> Seed:
        """Decide what to produce next."""
        context = context or {}
        
        seed_name = random.choice(Seed.get_all_names())
        seed_info = Seed.get_info(seed_name=seed_name)
        
        return Seed(name=seed_info['name'])

    def plant(self, seed: Seed) -> str:
        """
        Plant the seed in the ground.
        """
        seed.farmer = self.name
        seed.planted_at = datetime.now().timestamp()
        
        filename = f"seed.{seed.name}.{to_hash(seed)[:9]}"
        print(f"{filename}.planted")
        return write_json(seed, os.path.join(FARM_DIR, seed.farmer), filename)

    def harvest(self) -> str:
        """
        Harvest the product from the ground.
        """
        ripe_patterns = [os.path.join(FARM_DIR, "*", "ripe.*")]
        ripe_paths = get_files_path_by_patterns(patterns=ripe_patterns)
        for ripe_path in ripe_paths:
            try:
                product = load_json(ripe_path)
                product_id = to_hash(Seed(**product.get('data')))[:9]
                filename = os.path.basename(ripe_path)
                if self.verify_growth(product) and filename.endswith(product_id):
                    os.rename(ripe_path, ripe_path.replace("ripe.", ""))
                    print(f"{filename}.harvested")
                else:
                    os.remove(ripe_path)
                    print(f"{filename}.is_rotten")
            except Exception as e:
                print(f"Error harvesting at {ripe_path}: {e}")

    def verify_growth(self, product: Dict[str, Any]) -> bool:
        """
        Verify the proof of work for a grown product.
        """
        try:
            seed = Seed(**product['data'])
            return verify_proof_of_work(data=seed, nonces=product['nonces'])
        except Exception as e:
            print(f"Error verifying growth for {product}: {e}")
            return False


def main() -> None:
    """
    Main entrypoint for running the farm simulation.
    """
    farmer = Farmer("John")
    while True:
        try:
            seed = farmer.what_to_produce()
            farmer.plant(seed=seed)
            farmer.harvest()
        except Exception as e:
            print(f"Error: {e}")
            pass
        time.sleep(7)


if __name__ == "__main__":
    main()
