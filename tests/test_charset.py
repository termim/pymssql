# -*- coding: utf-8 -*-
"""
Test charset usage in queries.
"""

import pytest
import pymssql
from .helpers import config


@pytest.fixture
def conn_with_charset():
    """Fixture providing pymssql.Connection with WINDOWS-1251 charset."""
    conn = pymssql.connect(
        server=config.server,
        user=config.user,
        password=config.password,
        database=config.database,
        port=config.port,
        charset='WINDOWS-1251',
    )
    yield conn
    conn.close()


@pytest.mark.mssql_server_required
class TestCharset:
    """Tests for charset usage in queries."""

    def test_charset(self, conn_with_charset):
        cursor = conn_with_charset.cursor()

        try:
            cursor.execute(
                'select %s, %s',
                ('Здравствуй', 'Мир')  # Russian strings
            )
        except UnicodeDecodeError as e:
            pytest.fail("cursor.execute() raised %s unexpectedly: %s" % (e.__class__.__name__, e))

        a, b = cursor.fetchone()

        assert a == 'Здравствуй'
        assert b == 'Мир'
