# -*- coding: utf-8 -*-
"""
Test switching and printing the current database.
"""

import pytest
from pymssql import _mssql


@pytest.mark.mssql_server_required
@pytest.mark.parametrize("db", [
    'master',
    'tempdb',
    'msdb',
    'model',
])
def test_connect_cur_db_name(test_cfg, db):
    conn = _mssql.connect(
        server=test_cfg.server,
        port=test_cfg.port,
        user=test_cfg.user,
        password=test_cfg.password,
        database=db,
    )
    connDBName = conn.execute_scalar("SELECT DB_NAME() AS myDB")
    assert db == connDBName
    assert conn.cur_db_name() == connDBName
    conn.close()


@pytest.mark.mssql_server_required
def test_select_db(test_cfg):
    conn = _mssql.connect(
        server=test_cfg.server,
        port=test_cfg.port,
        user=test_cfg.user,
        password=test_cfg.password,
        database=test_cfg.database,
    )
    for db in ['master', 'model', 'msdb', 'tempdb']:
        conn.select_db(db)
        connDBName = conn.execute_scalar("SELECT DB_NAME() AS myDB")
        assert connDBName == db
        assert conn.cur_db_name() == db
    conn.close()
