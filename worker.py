import glob
import os
import random
import threading
import time
import uuid
from datetime import datetime, timedelta

from utils import write_to_file, move_file

FRUITS = (("grapes", 4), ("banana", 4), ("orange", 3), ("apple", 5))


class InvalidBarcode(Exception):
    pass


class RottenIngredient(Exception):
    pass


class Worker(threading.Thread):
    def __init__(self, name, stop_event):
        threading.Thread.__init__(self, name=name)
        self.stop_event = stop_event

    def run(self):
        while not self.stop_event.is_set():
            day_or_night, weather = get_barcode_info(f"data/city-farm")
            print(f"{self.name}: this {day_or_night} is {weather}")
            self.make()
        if self.stop_event.is_set():
            print(self.name + ' has stopped.')

    def make(self):
        raise NotImplementedError()


def get_barcode_info(filepath: str) -> tuple:
    with open(filepath, "r") as f:
        barcode = f.read()
    timestamp, owner = barcode.split(":")
    return timestamp, owner


class Farmer(Worker):

    def check_ingredient(self, filepath: str):
        try:
            timestamp, owner = get_barcode_info(filepath)
            produced_at = datetime.fromtimestamp(float(timestamp))
            if produced_at < datetime.now() - timedelta(seconds=10):
                if owner != self.name:
                    print("it's not mine")
                raise RottenIngredient

        except (FileNotFoundError, RottenIngredient):
            if os.path.isfile(filepath):
                os.remove(filepath)
        except Exception as e:
            print(e)

    def make(self):
        ingredient, takes = random.choice(FRUITS)
        box = f"data/street-fair/{self.name}/ingredients/{ingredient}"
        ingredients_files = glob.glob(os.path.join(box, "*"))

        for file in ingredients_files:
            self.check_ingredient(file)
            time.sleep(0.3)

        time.sleep(takes)
        barcode = f"{datetime.now().timestamp()}:{self.name}"
        write_to_file(box, uuid.uuid4().hex, barcode)


class Citizen(Worker):
    def check_ingredient(self, filepath: str) -> bool:
        try:
            timestamp, owner = get_barcode_info(filepath)
            produced_at = datetime.fromtimestamp(float(timestamp))
            if produced_at < datetime.now() - timedelta(seconds=10):
                raise RottenIngredient

            return True

        except Exception as e:
            print(e)

        return False

    def make(self):
        ingredient, price = random.choice(FRUITS)
        farmers = [os.path.basename(file) for file in glob.glob(os.path.join('data/street-fair', "*"))]
        citizen_dir = f"data/house/{self.name}/ingredients/{ingredient}"

        for farmer in farmers:
            time.sleep(3)
            box = f"data/street-fair/{farmer}/ingredients/{ingredient}"
            farmer_cash_box = f"data/street-fair/{farmer}/point-of-sale/"
            ingredients_files = glob.glob(os.path.join(box, "*"))
            for file in ingredients_files:
                if self.check_ingredient(file):
                    move_file(file, citizen_dir)
                    payment_detail = f"{datetime.now().timestamp()}:{self.name}"
                    money_note = f"{price}-{os.path.basename(file)}"
                    write_to_file(farmer_cash_box, money_note, payment_detail)
                else:
                    break


class CityFarm(Worker):
    def make(self):
        try:
            day_or_night, weather = get_barcode_info(f"data/city-farm")
        except Exception as e:
            day_or_night = 'night'

        weathers = ['sunny', 'cloudy', 'windy', 'rainy', 'stormy']

        day_or_night = 'day' if day_or_night == 'night' else 'night'

        if day_or_night == 'night':
            weathers.remove('sunny')

        weather = random.choice(weathers)
        write_to_file(f"data", 'city-farm', f'{day_or_night}:{weather}')

        time.sleep(5)


def main():
    stop_event = threading.Event()
    try:
        cityfarm = CityFarm('city-farm', stop_event)
        cityfarm.start()
        while True:
            print(threading.active_count())
            thread_working = [thread.name for thread in threading.enumerate()]
            command = input('Enter your command:')
            if command == 'farmer':
                farmers = [os.path.basename(file) for file in glob.glob(os.path.join('data/street-fair', "*"))]

                candidates = [item for item in farmers if item not in thread_working]
                name = candidates[0] if candidates else uuid.uuid4().hex[:7]
                farmer = Farmer(name, stop_event)
                farmer.start()

            elif command == 'citizen':
                citizens = [os.path.basename(file) for file in glob.glob(os.path.join('data/house', "*"))]

                candidates = [item for item in citizens if item not in thread_working]
                name = candidates[0] if candidates else uuid.uuid4().hex[:7]
                citizen = Citizen(name, stop_event)
                citizen.start()
            else:
                print('Unknown command.')

    except KeyboardInterrupt:
        print('[Program] Interrupted by user. Exiting...')
        stop_event.set()  # tell all threads to stop
        while threading.active_count() > 1:
            time.sleep(1)


if __name__ == '__main__':
    main()
