import sys
from pathlib import Path

import pytest

from data_analyst.db import Database
from data_analyst.sample_data import create_sample_db

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "eval"))


@pytest.fixture(scope="session")
def db_path(tmp_path_factory):
    return create_sample_db(tmp_path_factory.mktemp("db") / "shop.db")


@pytest.fixture
def db(db_path):
    return Database(db_path, max_rows=50, timeout_s=0.3)
