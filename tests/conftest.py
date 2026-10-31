"""Shared pytest fixtures: paths to the bundled sample manuscripts."""

from pathlib import Path

import pytest

DATA_DIR = Path(__file__).parent / "data"


@pytest.fixture()
def data_path() -> Path:
    """Directory holding the sample manuscript files used across tests."""
    return DATA_DIR
