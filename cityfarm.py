import hashlib
import itertools
import json
import random
import uuid
from base64 import b64encode
from collections import Counter
from dataclasses import dataclass, field, asdict
from typing import List

MEALS = {
    "hamburger": ["bread", "meat", "cheese", "tomato", "onion", "lettuce"]
}


def generate_unique_key() -> str:
    return str(uuid.uuid4())


@dataclass
class Farmer:
    id: str = field(default_factory=generate_unique_key)
    ingredients_produced: list[str] = field(default_factory=list)

    def __str__(self):
        return self.id[:5]

    def produce_ingredient(self):
        ingredients = random.sample(MEALS['hamburger'], random.choice([1, 1, 1, 2]))
        self.ingredients_produced = ingredients * random.choice([0, 1, 1, 1, 2])


@dataclass
class Citizen:
    id: str = field(default_factory=generate_unique_key)
    ingredients_list: list[str] = field(init=False)

    def __post_init__(self):
        self.ingredients_list = MEALS['hamburger'].copy()

    def __str__(self):
        return self.id[:5]


@dataclass
class StreetFair:
    citizens: list[Citizen] = field(default_factory=list)
    farmers: list[Farmer] = field(default_factory=list)
    transactions: list = field(default_factory=list)

    def bargain_the_ingredients(self, citizen: Citizen):
        for farmer in self.farmers:
            items_found = [item for item in citizen.ingredients_list if item in farmer.ingredients_produced]
            for item in items_found:
                farmer.ingredients_produced.remove(item)
                citizen.ingredients_list.remove(item)
                self.transactions.append(f"{citizen} bought [{item}] from {farmer}")

    def clock(self):
        # Citizens arriving at the Street Fair
        arrived_citizens = [Citizen()] * random.choice([0, 1, 1, 1, 2])

        # Farmers arriving to produce the demand
        arrived_farmers = [Farmer()] * random.choice([0, 0, 1, 1, 2])

        self.citizens.extend(arrived_citizens)
        self.farmers.extend(arrived_farmers)

        for farmer in self.farmers:
            farmer.produce_ingredient()

        for citizen in self.citizens:
            self.bargain_the_ingredients(citizen)

    def summary(self):
        demand_ingredients = [citizen.ingredients_list for citizen in self.citizens]
        supply_ingredients = [farmer.ingredients_produced for farmer in self.farmers]
        return {
            'demand': Counter(list(itertools.chain.from_iterable(demand_ingredients))),
            'supply': Counter(list(itertools.chain.from_iterable(supply_ingredients))),
        }


# print(f"citizen: {citizen}\n"
#       f"demand: {dict(sorted(summary['demand'].items(), key=lambda pair: pair[0]))}\n"
#       f"supply: {dict(sorted(summary['supply'].items(), key=lambda pair: pair[0]))}")

# print("{:<11}  {:<10}".format('demand', 'supply'))
# print("{:<11}  {:<10}".format('------', '------'))
# for demand, supply in zip(summary['demand'].items(), summary['supply'].items()):
#     print("| {:<10} {} | {:<10} {} ".format(*demand, *supply))


if __name__ == '__main__':
    from time import sleep

    street_fair_city = StreetFair()

    while True:
        street_fair_city.clock()
        sleep(0.3)
        if not street_fair_city.summary()['demand']:
            break

    for transaction in street_fair_city.transactions:
        print(transaction)

    print(len(street_fair_city.transactions))
