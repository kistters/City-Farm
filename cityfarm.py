import itertools
import os
import random
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime

MEALS = {
    "hamburger": ["bread", "meat", "cheese", "tomato", "onion", "lettuce", "bacon"],
    "fruit_salad": ["grapes", "banana", "orange", "apple", "strawberry", "pear", "mango", "honey_pot"],
    "soup": ["meat", "potato", "carrot", "broccoli", "onion", "bread"]
}


def desire_to_cook():
    meal = random.choice(list(MEALS.keys()))
    return MEALS[meal].copy()


def able_to_produce():
    ingredients = list(itertools.chain.from_iterable(MEALS.values()))
    return random.sample(ingredients, random.choice([1, 1, 1, 2]))


@dataclass
class Farmer:
    id: str = field(default_factory=uuid.uuid4)
    ingredients_produced: list[str] = field(default_factory=list)

    def __str__(self):
        return f"{self.id}"[:5]

    def produce_ingredient(self):
        self.ingredients_produced = able_to_produce() * random.choice([0, 1, 1, 1, 2])


@dataclass
class Citizen:
    id: str = field(default_factory=uuid.uuid4)
    ingredients_list: list[str] = field(init=False)

    def __post_init__(self):
        self.ingredients_list = desire_to_cook()

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
        arrived_citizens = [Citizen()] * random.choice([0, 1, 1, 1, 1])

        # Farmers arriving to produce the demand
        arrived_farmers = [Farmer()] * random.choice([0, 0, 0, 1])

        self.citizens.extend(arrived_citizens)
        self.farmers.extend(arrived_farmers)

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
        'transactions_by_farmer': Counter([str(f) for f in transactions_by_farmer]),
        'satisfied_citizens': Counter([str(c) for c in transactions_by_citizen if not c.ingredients_list]),
        'unsatisfied_citizens': Counter([str(c) for c in transactions_by_citizen if c.ingredients_list]),
        'transactions_by_ingredients': Counter([i for i in transactions_by_ingredient]),
    }


def print_formatted(data, format_type='bars', symbol=".", column_num=2):
    counter, msg = Counter(data).items(), ''

    if data and format_type == 'bars':
        chart = dict(counter)
        max_len = max(len(category) for category in chart)
        for category, frequency in chart.items():
            padding = (max_len - len(category)) * " "
            msg += f"{category}{padding} |{symbol * (50 if frequency > 50 else frequency) }{frequency}\n"

    if data and format_type == 'columns':
        rows = list(counter)
        size_column = len(max(dict(counter).keys(), key=len)) + 3
        for chunk in [rows[i:i + column_num] for i in range(0, len(rows), column_num)]:
            for key, value in chunk:
                msg += f"| {key} {value:<{size_column - len(key)}}"
            msg += "\n"

    return msg


if __name__ == '__main__':
    from time import sleep

    street_fair_city = StreetFair()

    while True:
        street_fair_city.clock()
        os.system('clear')

        output = f"""[top 5 farmers]
{print_formatted(dict(summary(street_fair_city)['transactions_by_farmer'].most_common(5)))}
[demand ingredients]:
{print_formatted(summary(street_fair_city)['demand'], format_type='columns',  column_num=9)}
[sold ingredients]: 
{print_formatted(summary(street_fair_city)['transactions_by_ingredients'], format_type='columns',  column_num=9)}
- unsatisfied citizens: {len(summary(street_fair_city)['unsatisfied_citizens'].keys())}
- satisfied citizens: {len(summary(street_fair_city)['satisfied_citizens'].keys())}
- farmer working: {len(street_fair_city.farmers)}
- sales: {len(street_fair_city.transactions)}
"""
        print(output)
        sleep(0.3)
        if street_fair_city.citizens and not summary(street_fair_city)['demand']:
            break
