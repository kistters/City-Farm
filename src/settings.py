# Constants for paths
import os
from utils import load_json


DATA_DIR = os.path.join("data")
SEEDS_JSON_PATH = os.path.join("src/seeds.json")
DISASTERS_JSON_PATH = os.path.join("src/disasters.json")
DISHES_JSON_PATH = os.path.join("src/dishes.json")

FARM_DIR = os.path.join(DATA_DIR, "farm")
CITY_DIR = os.path.join(DATA_DIR, "city")
WISH_DIR = os.path.join(DATA_DIR, "wish")

SEEDS = load_json(SEEDS_JSON_PATH)
DISASTERS = load_json(DISASTERS_JSON_PATH)
DISHES = load_json(DISHES_JSON_PATH)
