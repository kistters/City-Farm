import os
import pytest

from farm import Farmer
from city import Citizen
from settings import DATA_DIR


@pytest.mark.parametrize("_class", [Farmer, Citizen])
def test_aggregation(_class):
    entity = _class(name="Tester")
    assert os.path.exists(f"{DATA_DIR}/{entity.name}.{_class.__name__.lower()}.json")
