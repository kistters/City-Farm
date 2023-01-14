import itertools
import json
import random
from collections import Counter
from dataclasses import dataclass, field, asdict
from typing import List

MEALS = {
    "hamburger": ["bread", "meat", "cheese", "tomato", "onion", "lettuce"]
}


@dataclass
class Farmer:
    ingredients_produced: list[str] = field(default_factory=list)

    def produce_ingredient(self):
        ingredients = random.sample(MEALS['hamburger'], random.choice([1, 1, 1, 2]))
        self.ingredients_produced = ingredients * random.choice([0, 1, 1, 1, 2])


@dataclass
class Citizen:
    ingredients_list: list[str] = field(init=False)

    def __post_init__(self):
        self.ingredients_list = MEALS['hamburger'].copy()


@dataclass
class StreetFair:
    citizens: list[Citizen] = field(default_factory=list)
    farmers: list[Farmer] = field(default_factory=list)

    def bargain_the_ingredients(self, citizen: Citizen):
        for farmer in self.farmers:
            items_found = [item for item in citizen.ingredients_list if item in farmer.ingredients_produced]
            for item in items_found:
                farmer.ingredients_produced.remove(item)
                citizen.ingredients_list.remove(item)

    def summary_demand(self) -> Counter:
        return Counter(list(itertools.chain.from_iterable([citizen.ingredients_list for citizen in self.citizens])))

    def summary_supply(self) -> Counter:
        return Counter(list(itertools.chain.from_iterable([farmer.ingredients_produced for farmer in self.farmers])))

    def clock(self):
        # Citizens arriving at the Street Fair
        arrived_citizens = [Citizen()] * random.choice([0, 0, 1, 1, 2])

        # Farmers arriving to produce the demand
        arrived_farmers = [Farmer()] * random.choice([0, 0, 1, 1, 2])

        self.citizens.extend(arrived_citizens)
        if self.summary_demand().keys():
            self.farmers.extend(arrived_farmers)

        for citizen in self.citizens:
            self.bargain_the_ingredients(citizen)

        for farmer in self.farmers:
            farmer.produce_ingredient()

        print(f"\n------")
        for key, value in asdict(self).items():
            print(key, value)


# print(f"citizen: {citizen}\n"
#       f"demand: {dict(sorted(summary['demand'].items(), key=lambda pair: pair[0]))}\n"
#       f"supply: {dict(sorted(summary['supply'].items(), key=lambda pair: pair[0]))}")

# print("{:<11}  {:<10}".format('demand', 'supply'))
# print("{:<11}  {:<10}".format('------', '------'))
# for demand, supply in zip(summary['demand'].items(), summary['supply'].items()):
#     print("| {:<10} {} | {:<10} {} ".format(*demand, *supply))


if __name__ == '__main__':
    street_fair_city = StreetFair()

    for day in range(1, 10):
        street_fair_city.clock()
