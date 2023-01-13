import random
from collections import Counter
from dataclasses import dataclass, field
from typing import List

MEALS = {
    "hamburger": ["bread", "meat", "cheese", "tomato", "onion", "lettuce"]
}


@dataclass
class Farmer:
    name: str

    @staticmethod
    def produce_ingredient(item: str, quantity: int) -> List[str]:
        return [item] * (quantity - random.choice([0, 1]))


@dataclass
class Citizen:
    name: str
    ingredients_list: list[str] = field(default_factory=list)

    def wish_meal(self):
        print(self.ingredients_list)
        if not self.ingredients_list:
            self.ingredients_list = MEALS['hamburger'].copy()


@dataclass
class StreetFair:
    demand: list[str] = field(default_factory=list)
    supply: list[str] = field(default_factory=list)

    def request_ingredients(self, items: List[str]):
        # self.demand.extend([item for item in items if item not in self.demand])  # easy
        self.demand.extend(items)

    def increase_ingredient(self, items: List[str]):
        self.supply.extend(items)

    def buy_ingredients(self, items: List[str]):
        items_found = [item for item in items if item in self.supply]
        for item in items_found:
            self.supply.remove(item)
            self.demand.remove(item)
            items.remove(item)

    def summary(self):
        return {
            'demand': Counter(self.demand),
            'supply': Counter(self.supply)
        }


def pretty_print_street_fair(idx, street_fair, citizen):
    summary = street_fair.summary()
    print(f"---\nday: [{idx}]")

    print(f"citizen: {citizen}\n"
          f"demand: {dict(sorted(summary['demand'].items(), key=lambda pair: pair[0]))}\n"
          f"supply: {dict(sorted(summary['supply'].items(), key=lambda pair: pair[0]))}")

    # print("{:<11}  {:<10}".format('demand', 'supply'))
    # print("{:<11}  {:<10}".format('------', '------'))
    # for demand, supply in zip(summary['demand'].items(), summary['supply'].items()):
    #     print("| {:<10} {} | {:<10} {} ".format(*demand, *supply))


if __name__ == '__main__':
    street_fair_city = StreetFair()

    citizen_luck = Citizen('Luck')
    farmer_will = Farmer('Will')
    citizen_luck.wish_meal()

    for day in range(1, 10):
        street_fair_city.buy_ingredients(citizen_luck.ingredients_list)

        street_fair_city.request_ingredients(citizen_luck.ingredients_list)

        produced_ingredients = []
        for ingredients, qty in street_fair_city.summary()['demand'].items():
            produced_ingredients += farmer_will.produce_ingredient(ingredients, qty)

        street_fair_city.increase_ingredient(produced_ingredients)

        pretty_print_street_fair(day, street_fair_city, citizen_luck)