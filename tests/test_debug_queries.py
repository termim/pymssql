# -*- coding: utf-8 -*-
"""
Test queries with debug on.
"""

from contextlib import contextmanager
from io import StringIO
import sys

import pytest



@contextmanager
def redirect_stderr():
    sys.stderr = StringIO()
    yield sys.stderr
    sys.stderr = sys.__stderr__


@pytest.fixture
def conn_with_debug(mssql_conn):
    """Fixture providing connection with debug enabled."""
    mssql_conn.debug_queries = True
    yield mssql_conn
    mssql_conn.debug_queries = False


@pytest.mark.mssql_server_required
def test_MSSQLConnection_with_debug_queries(conn_with_debug):
    """Test for http://code.google.com/p/pymssql/issues/detail?id=98"""
    sql = "SELECT 'foo' AS first_name, 'bar' AS last_name"
    expected_row = {
        0: 'foo',
        1: 'bar',
        'first_name': 'foo',
        'last_name': 'bar',
    }

    with redirect_stderr() as stderr:
        row = conn_with_debug.execute_row(sql)
        assert row == expected_row

    # Check that the SQL is logged (contains the query in debug output)
    stderr_output = stderr.getvalue()
    assert "#%s#" % sql in stderr_output
