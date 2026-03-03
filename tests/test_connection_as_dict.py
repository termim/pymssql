# -*- coding: utf-8 -*-
"""
Test connection with as_dict=True.
"""

import unittest

import pytest

import pymssql


def pymssqlconn(test_cfg, **kwargs):
    return pymssql.connect(
            server=test_cfg.server,
            user=test_cfg.user,
            password=test_cfg.password,
            database=test_cfg.database,
            port=test_cfg.port,
            **kwargs
        )


@pytest.fixture
def conn_as_dict(test_cfg):
    """Fixture providing pymssql.Connection with as_dict=True."""
    return pymssqlconn(test_cfg, as_dict=True)


@pytest.mark.mssql_server_required
class TestConnectionAsDict:

    def test_fetchall_with_connection_as_dict(self, conn_as_dict):
        # This test is for http://code.google.com/p/pymssql/issues/detail?id=18
        cursor = conn_as_dict.cursor()
        cursor.execute("SELECT 'foo' AS first_name, 'bar' AS last_name")
        data = cursor.fetchall()
        assert data == [{'first_name': 'foo', 'last_name': 'bar'}]

    def test_no_results_with_connection_as_dict(self, conn_as_dict):
        # Make sure that checking for columns without names doesn't break
        # statements that don't return results

        cursor = conn_as_dict.cursor()
        cursor.execute("""
        CREATE TABLE daily_measurement (
            datetime DATETIME,
            value FLOAT,
            notes VARCHAR,
        )
        """)
