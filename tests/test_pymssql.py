# -*- coding: utf-8 -*-
"""
Test pymssql module.
"""

import unittest

import pytest

import pymssql as pym

from .conftest import pymssqlconn


class TestDBAPI2:
    def test_version(self):
        assert pym.__version__


@pytest.fixture
def users_table(mssql_conn):
    """Fixture providing a test table 'users'."""
    table_name = 'users'
    mssql_conn.execute_non_query(f"IF OBJECT_ID('{table_name}') IS NOT NULL DROP TABLE {table_name}")
    mssql_conn.execute_non_query(f"CREATE TABLE {table_name} (name varchar(50))")
    yield table_name
    mssql_conn.execute_non_query(f"IF OBJECT_ID('{table_name}') IS NOT NULL DROP TABLE {table_name}")


@pytest.mark.mssql_server_required
def test_immediate_rollback(pymssql_conn_function, users_table):
    """Test immediate rollback."""
    pymssql_conn_function.rollback()


@pytest.mark.mssql_server_required
def test_multiple_rollbacks(pymssql_conn_function):
    """Test multiple rollbacks."""
    pymssql_conn_function.rollback()
    pymssql_conn_function.rollback()
    pymssql_conn_function.rollback()


@pytest.mark.mssql_server_required
def test_rollback(pymssql_conn_function, users_table):
    """Test rollback functionality."""
    cur = pymssql_conn_function.cursor()
    cur.execute(f'insert into {users_table} values (%s)', 'foobar')
    cur.execute(f'select count(*) from {users_table}')
    assert cur.fetchone()[0] == 1
    pymssql_conn_function.rollback()
    cur.execute(f'select count(*) from {users_table}')
    assert cur.fetchone()[0] == 0


@pytest.mark.mssql_server_required
def test_commit(pymssql_conn_function, users_table):
    """Test commit functionality."""
    cur = pymssql_conn_function.cursor()
    cur.execute(f'insert into {users_table} values (%s)', 'foobar')
    cur.execute(f'select count(*) from {users_table}')
    assert cur.fetchone()[0] == 1
    pymssql_conn_function.commit()
    pymssql_conn_function.rollback()
    cur.execute(f'select count(*) from {users_table}')
    assert cur.fetchone()[0] == 1


@pytest.mark.mssql_server_required
def test_rollback_after_error(pymssql_conn_function, users_table):
    """Test rollback after error."""
    cur = pymssql_conn_function.cursor()
    cur.execute(f'insert into {users_table} values (%s)', 'foobar')
    cur.execute(f'select count(*) from {users_table}')
    assert cur.fetchone()[0] == 1
    try:
        cur.execute('insert into notable values (%s)', '123')
    except pym.ProgrammingError as e:
        if 'notable' not in str(e):
            raise
        pymssql_conn_function.rollback()
    cur.execute(f'select count(*) from {users_table}')
    assert cur.fetchone()[0] == 0


@pytest.mark.mssql_server_required
def test_rollback_after_create_error(pymssql_conn_function, users_table):
    """Test rollback after CREATE error."""
    cur = pymssql_conn_function.cursor()
    cur.execute(f'insert into {users_table} values (%s)', 'foobar')
    cur.execute(f'select count(*) from {users_table}')
    assert cur.fetchone()[0] == 1
    try:
        cur.execute("CREATE TABLE badschema.t1 ( test1 CHAR(5) NOT NULL)")
    except pym.OperationalError as e:
        if 'badschema' not in str(e):
            raise
        pymssql_conn_function.rollback()
    cur.execute(f'select count(*) from {users_table}')
    assert cur.fetchone()[0] == 0


@pytest.mark.mssql_server_required
def test_conn_props_override(test_cfg):
    """Test connection properties override."""
    conn = pym.connect(
        server=test_cfg.server,
        user=test_cfg.user,
        password=test_cfg.password,
        database=test_cfg.database,
        port=test_cfg.port,
        conn_properties='SET TEXTSIZE 2147483647'
    )
    conn.close()

    conn = pym.connect(
        server=test_cfg.server,
        user=test_cfg.user,
        password=test_cfg.password,
        database=test_cfg.database,
        port=test_cfg.port,
        conn_properties='SET TEXTSIZE 2147483647;'
    )
    conn.close()

    conn = pym.connect(
        server=test_cfg.server,
        user=test_cfg.user,
        password=test_cfg.password,
        database=test_cfg.database,
        port=test_cfg.port,
        conn_properties='SET TEXTSIZE 2147483647;SET ANSI_NULLS ON;'
    )
    conn.close()

    conn = pym.connect(
        server=test_cfg.server,
        user=test_cfg.user,
        password=test_cfg.password,
        database=test_cfg.database,
        port=test_cfg.port,
        conn_properties='SET TEXTSIZE 2147483647;SET ANSI_NULLS ON'
    )
    conn.close()

    conn = pym.connect(
        server=test_cfg.server,
        user=test_cfg.user,
        password=test_cfg.password,
        database=test_cfg.database,
        port=test_cfg.port,
        conn_properties='SET TEXTSIZE 2147483647;SET ANSI_NULLS ON;'
    )
    conn.close()

    conn = pym.connect(
        server=test_cfg.server,
        user=test_cfg.user,
        password=test_cfg.password,
        database=test_cfg.database,
        port=test_cfg.port,
        conn_properties=['SET TEXTSIZE 2147483647;', 'SET ANSI_NULLS ON']
    )
    conn.close()
    assert Exception, pym.connect(
        server=test_cfg.server,
        user=test_cfg.user,
        password=test_cfg.password,
        database=test_cfg.database,
        port=test_cfg.port,
        conn_properties='BOGUS SQL'
    )

    conn = pym.connect(
        conn_properties='SET TEXTSIZE 2147483647',
        server=test_cfg.server,
        user=test_cfg.user,
        password=test_cfg.password
    )
    conn.close()


@pytest.fixture
def test_table(mssql_conn):
    """Fixture providing a test table 'test'."""
    table_name = 'test'
    mssql_conn.execute_non_query(f"IF OBJECT_ID('{table_name}') IS NOT NULL DROP TABLE {table_name}")
    mssql_conn.execute_non_query(f"CREATE TABLE {table_name} (name varchar(50))")
    yield table_name
    mssql_conn.execute_non_query(f"IF OBJECT_ID('{table_name}') IS NOT NULL DROP TABLE {table_name}")


@pytest.mark.mssql_server_required
def test_db_creation_with_autocommit(pymssql_conn_function, test_table):
    """Try creating and dropping database with autocommit."""
    test_db_name = 'autocommit_test_database'
    cur = pymssqlconn(autocommit=True).cursor()
    try:
        cur.execute("CREATE DATABASE {0}".format(test_db_name))
    except pym.OperationalError as e:
        expected_msg = "CREATE DATABASE permission denied in database 'master'"
        if expected_msg in str(e.args[1]):
            pytest.skip('We have no CREATE DATABASE permission on test database')
        else:
            pytest.fail()
    else:
        cur.execute("DROP DATABASE {0}".format(test_db_name))


@pytest.mark.mssql_server_required
def test_db_creation_without_autocommit():
    """Try creating and dropping database without autocommit, expecting it to fail."""
    cur = pymssqlconn(autocommit=False).cursor()
    with pytest.raises(pym.OperationalError) as excinfo:
        cur.execute("CREATE DATABASE autocommit_test_database")
    expected_msg = "CREATE DATABASE statement not allowed within multi-statement transaction"
    assert expected_msg in excinfo.exconly()


@pytest.mark.mssql_server_required
def test_autocommit_flipping_tf(test_table):
    """Test autocommit flipping from True to False."""
    insert_value = 'true-false'
    conn = pymssqlconn(autocommit=True)
    conn.autocommit(False)
    cur = conn.cursor()
    cur.execute(f'INSERT INTO {test_table} VALUES (%s)', insert_value)
    conn.commit()
    cur.execute(f'SELECT * FROM {test_table} WHERE name = (%s)', insert_value)
    row = cur.fetchone()
    cur.close()
    conn.close()
    assert len(row) > 0


@pytest.mark.mssql_server_required
def test_autocommit_flipping_ft(test_table):
    """Test autocommit flipping from False to True."""
    insert_value = 'false-true'
    conn = pymssqlconn(autocommit=False)
    conn.autocommit(True)
    cur = conn.cursor()
    cur.execute(f'INSERT INTO {test_table} VALUES (%s)', insert_value)
    cur.execute(f'SELECT * FROM {test_table} WHERE name = (%s)', insert_value)
    row = cur.fetchone()
    assert len(row) > 0


@pytest.mark.mssql_server_required
def test_autocommit_false_does_not_commit(test_table):
    """Test autocommit False does not auto-commit."""
    insert_value = 'false'
    conn = pymssqlconn(autocommit=False)
    cur = conn.cursor()
    cur.execute(f'INSERT INTO {test_table} VALUES (%s)', insert_value)
    conn.rollback()
    cur.execute(f'SELECT * FROM {test_table} WHERE name = (%s)', insert_value)
    row = cur.fetchone()
    cur.close()
    conn.close()
    assert row is None
