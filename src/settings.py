# Constants for paths
import os
from utils import load_json

# Get the project root directory (parent of src)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
SEEDS_JSON_PATH = os.path.join(PROJECT_ROOT, "src/const/seeds.json")
DISASTERS_JSON_PATH = os.path.join(PROJECT_ROOT, "src/const/disasters.json")
DISHES_JSON_PATH = os.path.join(PROJECT_ROOT, "src/const/dishes.json")

FARM_DIR = os.path.join(DATA_DIR, "farm")
CITY_DIR = os.path.join(DATA_DIR, "city")
WISH_DIR = os.path.join(DATA_DIR, "wish")

SEEDS = load_json(SEEDS_JSON_PATH)
DISASTERS = load_json(DISASTERS_JSON_PATH)
DISHES = load_json(DISHES_JSON_PATH)
