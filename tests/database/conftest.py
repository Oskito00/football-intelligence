import sqlite3
import pytest

@pytest.fixture
def conn():
    conn = sqlite3.connect('test.db')
    return conn

