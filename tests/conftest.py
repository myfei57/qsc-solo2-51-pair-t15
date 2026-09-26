"""Fixtures shared by the control service tests."""

import pytest

from desalplant.config import Config
from desalplant.store.store import Store

from support import build


@pytest.fixture()
def data_dir(tmp_path):
    return str(tmp_path / "data")


@pytest.fixture()
def config(data_dir):
    return Config(data_dir=data_dir)


@pytest.fixture()
def services(config):
    return build(config)


@pytest.fixture()
def console(services):
    return services.console


@pytest.fixture()
def plant(services):
    return services.plant


@pytest.fixture()
def store(tmp_path):
    return Store(str(tmp_path / "plant.json"))
