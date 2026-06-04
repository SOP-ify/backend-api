"""
tests/conftest.py

Shared pytest fixtures and configuration.
Patches MongoDB connection during tests to avoid real DB calls.
"""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.fixture(autouse=True)
def mock_db_connection():
    """
    Automatically patches MongoDB connect/disconnect and index creation
    for all tests. This prevents tests from needing a real MongoDB instance.
    """
    with (
        patch(
            "app.core.database.connect_to_mongo",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.core.database.close_mongo_connection",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.modules.auth.repository.ensure_indexes",
            new=AsyncMock(return_value=None),
        ),
    ):
        yield
