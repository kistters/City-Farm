from dataclasses import dataclass
from datetime import datetime
import os
import random
import time
from typing import Any, Dict, List, Optional
from utils import (
    get_files_path_by_patterns,
    load_json,
    to_hash,
    verify_proof_of_work,
    write_json,
)
from settings import DATA_DIR, FARM_DIR, SEEDS


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

        for seed_type, seeds in SEEDS.items():
            if seed_name in seeds:
                return {"name": seed_name, "type": seed_type, **seeds[seed_name]}

        raise Exception(f"seed.{seed_name}.not_found")

    @classmethod
    def get_all_names(cls) -> List[str]:
        """Get all available farm seed names."""
        all_seeds = []
        for seeds in SEEDS.values():
            all_seeds.extend(seeds.keys())
        return all_seeds

    def id(self) -> str:
        return to_hash(self)[:9]


@dataclass
class Ingredient:
    seed: Seed
    nonces: List[Any]
    additional_info: Optional[Dict[str, Any]] = None

    def id(self) -> str:
        return to_hash(self)[:9]


class Entity:
    def __init__(self, name: str):
        self.name = name
        try:
            self.events = load_json(
                f"{DATA_DIR}/{self.name}.{self.__class__.__name__.lower()}.json"
            )
        except Exception as e:
            self.events = []
            self.save_events()

    def _add_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Add event to memory (don't save yet)."""
        event = {
            "event_type": event_type,
            "timestamp": datetime.now().isoformat(),
            "data": data,
        }
        self.events.append(event)  # ← Just keep in memory
        print(f"event: {event_type}")

    def save_events(self) -> None:
        """Save all events to disk."""
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            write_json(
                self.events,
                DATA_DIR,
                f"{self.name}.{self.__class__.__name__.lower()}.json",
            )
        except Exception as e:
            print(f"Error saving events: {e}")


class Farmer(Entity):
    def __init__(self, name: str):
        super().__init__(name)

    def what_to_produce(self, context: Optional[Dict[str, Any]] = None) -> Seed:
        """Decide what to produce next."""
        context = context or {}

        seed_name = random.choice(Seed.get_all_names())
        seed_info = Seed.get_info(seed_name=seed_name)

        return Seed(name=seed_info["name"])

    def plant(self, seed: Seed) -> str:
        """
        Plant the seed in the ground.
        """
        seed.farmer = self.name
        seed.planted_at = datetime.now().timestamp()

        filename = f"seed.{seed.name}.{seed.id()}"
        self._add_event(event_type=f"{seed.name}.seed.planted", data=seed)
        return write_json(seed, os.path.join(FARM_DIR, seed.farmer), filename)

    def harvest(self) -> str:
        """
        Harvest the ingredient from the ground.
        """
        ripe_patterns = [os.path.join(FARM_DIR, "*", "ripe.*")]
        ripe_paths = get_files_path_by_patterns(patterns=ripe_patterns)
        for ripe_path in ripe_paths:
            try:
                data = load_json(ripe_path)
                ingredient = Ingredient(
                    seed=Seed(**data.get("data")), nonces=data.get("nonces")
                )

                filename = os.path.basename(ripe_path)
                can_be_harvested = self.verify_growth(ingredient) and filename.endswith(
                    ingredient.seed.id()
                )

                if can_be_harvested:
                    os.rename(ripe_path, ripe_path.replace("ripe.", ""))
                    self._add_event(
                        event_type=f"{ingredient.seed.name}.harvested", data=ingredient
                    )
                else:
                    os.remove(ripe_path)
                    what_happened = ingredient.nonces[-1]
                    self._add_event(
                        event_type=f"{ingredient.seed.name}.disaster.{what_happened}",
                        data=ingredient,
                    )

            except Exception as e:
                print(f"Error harvesting at {ripe_path}: {e}")

    def verify_growth(self, ingredient: Ingredient) -> bool:
        """
        Verify the proof of work for a grown ingredient.
        """
        try:
            return verify_proof_of_work(data=ingredient.seed, nonces=ingredient.nonces)
        except Exception as e:
            print(f"Error verifying growth for {ingredient}: {e}")
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
            farmer.save_events()
        except Exception as e:
            print(f"Error: {e}")
            pass
        time.sleep(7)


if __name__ == "__main__":
    main()
