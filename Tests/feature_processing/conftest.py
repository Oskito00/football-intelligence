import sqlite3
import pytest

@pytest.fixture
def conn():
    return sqlite3.connect('test_db.sqlite')

