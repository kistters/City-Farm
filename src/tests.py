import os
import pytest

from farm import Farmer
from city import Citizen
from settings import DATA_DIR

@pytest.mark.parametrize("Entity", [Farmer, Citizen])
def test_aggregation(Entity):
    entity = Entity(name="Tester")
    assert os.path.exists(f"{DATA_DIR}/{entity.name}.{Entity.__name__.lower()}.json")
