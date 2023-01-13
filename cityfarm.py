from collections import Counter
from dataclasses import dataclass, field
from typing import List

MEALS = {
    ""
}

@dataclass
class Farmer:
    name: str

    @staticmethod
    def produce_ingredient(ingredient: str, quantity: int) -> List[str]:
        # TODO produce time
        if not ingredient.isalpha() or len(ingredient) < 3:
            raise Exception(f"Ingredient {ingredient} is not allowed!")

        return [ingredient for _ in range(quantity)]


@dataclass
class Citizen:
    name: str


@dataclass
class StreetFair:
    demand: list[str] = field(default_factory=list)
    supply: list[str] = field(default_factory=list)

    def request_ingredients(self, ingredients: List[str]):
        self.demand.extend(ingredients)

    def increase_ingredient(self, ingredient: str):
        self.supply.append(ingredient)

    def summary(self):
        return {
            'demand': Counter(self.demand),
            'supply': Counter(self.supply)
        }

