from __future__ import annotations

import pytest
from ayudas import crear_repo


@pytest.fixture
def repo(tmp_path):
    return crear_repo(tmp_path / "repo")
