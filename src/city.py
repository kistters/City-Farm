from dataclasses import dataclass
from datetime import datetime
import os
import random
import time
from typing import Any, Dict, List, Optional
from farm import Entity, Ingredient, Seed
from utils import get_files_path_by_patterns, load_json, to_hash, write_json
from settings import CITY_DIR, DISHES, FARM_DIR, WISH_DIR


@dataclass
class Dishe:
    name: str
    citizen: str = None
    cooked_at: float = None
    ingredients: List[str] = None
    
    @classmethod
    def get_info(cls, dishe_name: str) -> Optional[Dict[str, Any]]:
        """
        Get city dishe information by name from any type.
        Returns a dict with dishe info, or None if not found.
        """
    
        for dishe_type, dishes in DISHES.items():
            if dishe_name in dishes:
                return {
                    "name": dishe_name,
                    "type": dishe_type,
                    **dishes[dishe_name]
                }
                
        raise Exception(f"dishe.{dishe_name}.not_found")
    
    @classmethod
    def get_all_names(cls) -> List[str]:
        """Get all available dishe names."""
        all_dishes = []
        for dishes in DISHES.values():
            all_dishes.extend(dishes.keys())
        return all_dishes

    def id(self) -> str:
        return to_hash(self)[:9]


class Citizen(Entity):
    def __init__(self, name: str):
        super().__init__(name)
    
    def what_to_prepare(self, context: Optional[Dict[str, Any]] = None) -> Dishe:
        """Decide what to produce next."""
        context = context or {}
        
        dishe_name = random.choice(Dishe.get_all_names())
        dishe_info = Dishe.get_info(dishe_name=dishe_name)
        
        return Dishe(name=dishe_info['name'], ingredients=dishe_info['required_ingredients'])

    def buy_ingredients(self, dishe: Dishe) -> str:
        """
        Buy the ingredients for the dishe.
        """
        for ingredient_name in dishe.ingredients:
            ingredient_patterns = [os.path.join(FARM_DIR, "*", f"{ingredient_name}.*")]
            ingredient_paths = get_files_path_by_patterns(patterns=ingredient_patterns)
            ingredient_paths = [
                ingredient for ingredient in ingredient_paths 
                if not any(word in ingredient.lower() for word in ['seed', 'ripe'])
            ]

            if not ingredient_paths:
                write_json({"who.want": ingredient_name}, WISH_DIR, f"{ingredient_name}.wish")
                continue

            for ingredient_path in ingredient_paths:
                try:
                    data = load_json(ingredient_path)
                    ingredient =  Ingredient(seed=Seed(**data.get('data')), nonces=data.get('nonces'))
                except Exception as e:
                    print(f"Error loading ingredient: {e}")
                    continue
                
                if ingredient_name in ingredient_path:
                    filename = f"{ingredient.seed.name}.{ingredient.seed.id()}"
                    write_json(ingredient, os.path.join(CITY_DIR, self.name, "ingredients"), filename)
                    os.remove(ingredient_path)
                    ingredient_paths.remove(ingredient_path)
                    self._add_event(event_type=f"{ingredient.seed.name}.bought.from.{ingredient.seed.farmer}", data=ingredient)
                    break

    def cook(self, dishe: Dishe) -> None:
        """
        Cook the dishe.
        """
        print(f"Cooking {dishe}")
        for ingredient_name in dishe.ingredients:
            my_ingredient_patterns = [os.path.join(CITY_DIR, self.name, f"{ingredient_name}.*")]
            my_ingredient_paths = get_files_path_by_patterns(patterns=my_ingredient_patterns)
            if not my_ingredient_paths:
                continue
        


def main() -> None:
    """
    Main entrypoint for running the farm simulation.
    """
    citizen = Citizen("Will")
    while True:
        try:
            dishe = citizen.what_to_prepare()
            citizen.buy_ingredients(dishe)
            citizen.cook(dishe)
            citizen.save_events()
        except Exception as e:
            print(f"Error: {e}")
            pass
        time.sleep(7 / 2)


if __name__ == "__main__":
    main()
