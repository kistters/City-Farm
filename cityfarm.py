import itertools
import os
import random
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime

MEALS = {
    "hamburger": ["bread", "meat", "cheese", "tomato", "onion", "lettuce"]
}


def generate_unique_key() -> str:
    return str(uuid.uuid4())


@dataclass
class Farmer:
    id: str = field(default_factory=uuid.uuid4)
    ingredients_produced: list[str] = field(default_factory=list)

    def __str__(self):
        return f"{self.id}"[:5]

    def produce_ingredient(self):
        ingredients = random.sample(MEALS['hamburger'], random.choice([1, 1, 1, 2]))
        self.ingredients_produced = ingredients * random.choice([0, 1, 1, 1, 2])


@dataclass
class Citizen:
    id: str = field(default_factory=uuid.uuid4)
    ingredients_list: list[str] = field(init=False)

    def __post_init__(self):
        self.ingredients_list = MEALS['hamburger'].copy()

    def __str__(self):
        return f"{self.id}"[:5]


@dataclass
class Transaction:
    citizen: Citizen
    farmer: Farmer
    ingredient: str
    created_at: datetime


@dataclass
class StreetFair:
    citizens: list[Citizen] = field(default_factory=list)
    farmers: list[Farmer] = field(default_factory=list)
    transactions: list[Transaction] = field(default_factory=list)

    def bargain_the_ingredients(self, citizen: Citizen):
        random.shuffle(self.farmers)
        for farmer in self.farmers:
            ingredients_found = [item for item in citizen.ingredients_list if item in farmer.ingredients_produced]
            for ingredient in ingredients_found:
                farmer.ingredients_produced.remove(ingredient)
                citizen.ingredients_list.remove(ingredient)
                item = Transaction(citizen=citizen, farmer=farmer, ingredient=ingredient, created_at=datetime.now())
                self.transactions.append(item)

    def clock(self):
        # Citizens arriving at the Street Fair
        arrived_citizens = [Citizen()] * random.choice([0, 1, 1, 1, 2])

        # Farmers arriving to produce the demand
        arrived_farmers = [Farmer()] * random.choice([0, 0, 0, 1, 1])

        self.citizens.extend(arrived_citizens)
        self.farmers.extend(arrived_farmers if len(self.farmers) < 10 else [])

        for farmer in self.farmers:
            farmer.produce_ingredient()

        for citizen in self.citizens:
            self.bargain_the_ingredients(citizen)


def summary(street_fair: StreetFair):
    demand_ingredients = [citizen.ingredients_list for citizen in street_fair.citizens]
    supply_ingredients = [farmer.ingredients_produced for farmer in street_fair.farmers]
    transactions_by_farmer = [transaction.farmer for transaction in street_fair.transactions]
    transactions_by_citizen = [transaction.citizen for transaction in street_fair.transactions]
    transactions_by_ingredient = [transaction.ingredient for transaction in street_fair.transactions]

    return {
        'demand': Counter(list(itertools.chain.from_iterable(demand_ingredients))),
        'supply': Counter(list(itertools.chain.from_iterable(supply_ingredients))),
        'transactions_by_farmer': Counter([str(farmer) for farmer in transactions_by_farmer]),
        'transactions_by_citizen': Counter(
            [str(citizen) for citizen in transactions_by_citizen if not citizen.ingredients_list]),
        'transactions_by_ingredients': Counter([ingredient for ingredient in transactions_by_ingredient]),
    }


def print_ascii_bar_chart(data, symbol=None):
    if not data:
        return

    counter = Counter(data).items()
    if not symbol:
        print(dict(counter))
        return

    chart = {category: symbol * frequency for category, frequency in counter}
    max_len = max(len(category) for category in chart)
    for category, frequency in chart.items():
        padding = (max_len - len(category)) * " "
        print(f"{category}{padding} |{frequency}{len(frequency)}")


if __name__ == '__main__':
    from time import sleep

    street_fair_city = StreetFair()

    while True:
        street_fair_city.clock()
        os.system('clear')
        print(f"ingredients:", )
        print_ascii_bar_chart(summary(street_fair_city)['transactions_by_ingredients'])
        print(f"\nsatisfied citizens: {len(summary(street_fair_city)['transactions_by_citizen'].keys())}")
        print(f"\nfarmer sales({len(street_fair_city.transactions)}):")
        print_ascii_bar_chart(summary(street_fair_city)['transactions_by_farmer'], symbol='.')
        sleep(0.3)
        if street_fair_city.citizens and not summary(street_fair_city)['demand']:
            break
