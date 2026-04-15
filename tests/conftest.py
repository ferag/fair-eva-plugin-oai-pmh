from pathlib import Path

import pytest

from tests.helpers import load_preferred_tracking_config


@pytest.fixture
def plugin_dir() -> Path:
    return Path("fair_eva/plugin/oai_pmh")


@pytest.fixture
def tracking_config(plugin_dir):
    config, _ = load_preferred_tracking_config(plugin_dir)
    return config


@pytest.fixture
def loaded_config_path(plugin_dir):
    _, config_path = load_preferred_tracking_config(plugin_dir)
    return config_path
