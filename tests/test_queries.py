# -*- coding: utf-8 -*-
"""
Test queries.
"""

from datetime import datetime

import pytest



@pytest.fixture
def test_table(mssql_conn):
    """Fixture providing a clean test table for each test."""
    # Create table
    mssql_conn.execute_non_query("""
    CREATE TABLE pymssql (
        pk_id int IDENTITY (1, 1) NOT NULL,
        real_no real,
        float_no float,
        money_no money,
        stamp_datetime datetime,
        data_bit bit,
        comment_vch varchar(50),
        comment_nvch nvarchar(50),
        comment_text text,
        comment_ntext ntext,
        data_image image,
        data_binary varbinary(40),
        decimal_no decimal(38,2),
        numeric_no numeric(38,8),
        stamp_time timestamp,
        bin_data varbinary(16)
    )""")

    yield mssql_conn

    # Cleanup
    mssql_conn.execute_non_query('DROP TABLE pymssql')


@pytest.mark.mssql_server_required
def test01SimpleSelect(test_table):
    """Test simple SELECT query."""
    query = 'SELECT getdate() as cur_date_info'
    test_table.execute_query(query)
    rows = tuple(test_table)
    assert isinstance(rows[0]['cur_date_info'], datetime)


@pytest.mark.mssql_server_required
def test02EmptySelect(test_table):
    """Test SELECT from empty table."""
    query = 'SELECT * FROM pymssql'
    test_table.execute_query(query)
    rows = tuple(test_table)
    assert rows == ()


@pytest.mark.mssql_server_required
def test03InsertSelect(test_table):
    """Test INSERT and SELECT."""
    # Insert sample data
    for x in range(10):
        y = x + 1
        query = """
        INSERT INTO pymssql (
            real_no,
            float_no,
            money_no,
            stamp_datetime,
            data_bit,
            comment_vch,
            comment_ntext,
            comment_text,
            comment_nvch,
            decimal_no,
            numeric_no,
            bin_data
        ) VALUES (
            %d, %d, %d, getdate(), %d,
            'comment %d',
            'detail %d',
            'hmm',
            'bhmme',
            234.99,
            894123.09,
            %#x
        );""" % (y, y, y, (y % 2), y, y, y)
        test_table.execute_non_query(query)

    # Select and verify
    test_table.execute_query('SELECT * FROM pymssql')
    rows = tuple(test_table)
    assert len(rows) == 10

    # Check column count
    cols = [k for k in rows[0] if type(k) is int]
    assert len(cols) == 16


@pytest.mark.mssql_server_required
def test19MultipleResults(test_table):
    """Test multiple SELECT results."""
    test_table.execute_query("SELECT 'ret1'; SELECT 'ret2'; SELECT 'ret3'")
    rows = tuple(test_table)
    assert rows[0][0] == 'ret1'
    test_table.nextresult()

    rows = tuple(test_table)
    assert rows[0][0] == 'ret2'
    test_table.nextresult()

    rows = tuple(test_table)
    assert rows[0][0] == 'ret3'


@pytest.mark.mssql_server_required
def test04BinaryTypeSqlInjection(test_table):
    """Test binary type with SQL injection attempt."""
    test_table.execute_query('SELECT * FROM pymssql WHERE bin_data=%s', ('0x OR 1=1;',))
    rows = tuple(test_table)
    assert len(rows) == 0
