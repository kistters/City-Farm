# Constants for paths
import os
from utils import load_json


DATA_DIR = os.path.join("data")
SEEDS_JSON_PATH = os.path.join("src/seeds.json")
FARM_DIR = os.path.join(DATA_DIR, "farm")

FARM_SEEDS = load_json(SEEDS_JSON_PATH)
