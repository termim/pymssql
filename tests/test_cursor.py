# -*- coding: utf-8 -*-
"""
Cursor tests extracted from helpers.py CursorBase.

This module contains tests for cursor functionality including:
- Description handling
- Row counting
- Fetch operations (fetchone, fetchmany, fetchall)
- Dictionary vs tuple row formats
- Executemany operations
"""

import pytest
import pymssql

from .helpers import (
    pymssqlconn,
    TableManager,
)



@pytest.mark.mssql_server_required
class TestCursor:
    """
    Test cursor functionality with pymssql.
    """

    @classmethod
    def setup_class(cls):
        cls.conn = pymssqlconn()
        cls.t1 = TableManager(cls.conn, 'test', 'id int', 'name varchar(50)')

    def setup_method(self, method):
        self.conn.rollback()
        self.t1.clear()
        self.execute("insert into test values (1, 'one')")
        self.execute("insert into test values (2, 'two')")
        self.execute("insert into test values (3, 'three')")
        self.execute("insert into test values (4, 'four')")
        self.execute("insert into test values (5, 'five')")
        self.conn.commit()

    def execute(self, sql):
        cur = self.conn.cursor()
        cur.execute(sql)
        return cur

    def executemany(self, sql, params_seq, batch_size=1):
        cur = self.conn.cursor()
        cur.executemany(sql, params_seq, batch_size=batch_size)
        return cur

    def test_description_not_used(self):
        cur = self.conn.cursor()
        assert cur.description is None

    def test_description_after_insert(self):
        cur = self.execute("insert into test values (6, 'six')")
        self.conn.commit()
        assert cur.description is None

    def test_description_after_select(self):
        cur = self.execute('select * from test')
        assert len(cur.description) == 2
        assert cur.description[0][0] == 'id'
        assert pymssql.NUMBER == cur.description[0][1]
        assert cur.description[1][0] == 'name'
        assert pymssql.STRING == cur.description[1][1]

    def test_sticky_description(self):
        cur = self.execute('select * from test')
        assert len(cur.description) == 2

        cur2 = self.execute('select id from test')
        assert len(cur2.description) == 1

        # description of first cursor should not be affected
        assert len(cur.description) == 2

    def test_fetchone(self):
        cur = self.execute('select * from test order by id')
        res = cur.fetchone()
        assert res[0] == 1
        res = cur.fetchone()
        assert res[0] == 2

        for x in range(0, 5):
            if cur.fetchone() is None:
                # make sure another call is also None and no exception is
                # raised
                assert cur.fetchone() is None
                break
            if x == 5:
                assert False, 'expected cur.fetchone() to be None'

    def test_insert_rowcount(self):
        cur = self.execute("insert into test values (6, 'six')")
        assert cur.rowcount == 1
        self.conn.rollback()

    def test_delete_rowcount(self):
        cur = self.execute("delete from test where id = 5")
        assert cur.rowcount == 1
        cur = self.execute("delete from test where id > 1")
        assert cur.rowcount == 3
        self.conn.rollback()

    def test_update_rowcount(self):
        cur = self.execute("update test set name = 'foo' where id > 1")
        assert cur.rowcount == 4
        self.conn.rollback()

    def test_select_rowcount(self):
        cur = self.execute('select * from test')
        assert cur.rowcount == -1
        cur.fetchall()
        assert cur.rowcount == 5

    def test_fetchone_rowcount(self):
        cur = self.execute('select * from test')
        assert cur.rowcount == -1

        for _ in iter(cur.fetchone, None):
            assert cur.rowcount == -1

        assert cur.rowcount == 5

    def test_fetchmany_rowcount(self):
        cur = self.execute('select * from test')
        assert cur.rowcount == -1

        for _ in iter(cur.fetchmany, []):
            assert cur.rowcount == -1

        assert cur.rowcount == 5

    def test_as_dict(self):
        # test for http://code.google.com/p/pymssql/issues/detail?id=92
        cur = self.conn.cursor(as_dict=True)
        cur.execute("SELECT 'foo' AS first_name, 'bar' AS last_name")
        assert cur.fetchall() == [{'first_name': 'foo', 'last_name': 'bar'}]

    def test_as_dict_no_column_name(self):
        cur = self.conn.cursor(as_dict=True)
        try:
            # SQL Server >= 2008:
            #
            #   SELECT MAX(x), MIN(x) AS [MIN(x)]
            #   FROM (VALUES (1), (2), (3))
            #   AS foo(x)
            #
            # SQL Server = 2005 (remove when we drop support for it):
            #
            #   SELECT MAX(x), MIN(x) AS [MIN(x)]
            #   FROM (SELECT 1
            #         UNION ALL
            #         SELECT 2
            #         UNION ALL
            #         SELECT 3)
            #   AS foo(x)
            cur.execute(
                "SELECT MAX(x), MIN(x) AS [MIN(x)] "
                "FROM (SELECT 1"
                "      UNION ALL"
                "      SELECT 2"
                "      UNION ALL"
                "      SELECT 3) AS foo(x)")
            assert False, "Didn't raise InterfaceError"
        except pymssql.ColumnsWithoutNamesError as exc:
            assert exc.columns_without_names == [0]

    def test_as_dict_no_column_name_2(self):
        cur = self.conn.cursor(as_dict=True)
        try:
            # SQL Server >= 2008:
            #
            #   SELECT MAX(x), MAX(y) AS [MAX(y)], MIN(y)
            #   FROM (VALUES (1, 2), (2, 3), (3, 4))
            #   AS foo(x, y)
            #
            # SQL Server = 2005 (remove when we drop support for it):
            #
            #   SELECT MAX(x), MAX(y) AS [MAX(y)], MIN(y)
            #   FROM (SELECT (1, 2)
            #         UNION ALL
            #         SELECT (2, 3)
            #         UNION ALL
            #         SELECT (3, 4))
            #   AS foo(x, y)
            cur.execute(
                "SELECT MAX(x), MAX(y) AS [MAX(y)], MIN(y) "
                "FROM (SELECT 1, 2"
                "      UNION ALL"
                "      SELECT 2, 3"
                "      UNION ALL"
                "      SELECT 3, 4) AS foo(x, y)")
            assert False, "Didn't raise InterfaceError"
        except pymssql.ColumnsWithoutNamesError as exc:
            assert exc.columns_without_names == [0, 2]

    def test_fetchmany(self):
        cur = self.conn.cursor()
        cur.execute('select * from test')
        assert len(cur.fetchmany(2)) == 2
        assert len(cur.fetchmany(2)) == 2
        assert len(cur.fetchmany(2)) == 1

        # now a couple extra for good measure
        assert len(cur.fetchmany(2)) == 0
        assert len(cur.fetchmany(2)) == 0

    def test_execute_many(self):
        cur = self.executemany(
            "delete from test where id = %(id)s",
            [{'id': 1}, {'id': 2}])
        self.conn.commit()
        assert self.t1.count() == 3
        assert cur.rowcount == 2

    def test_executemany_many(self):
        self.executemany(
            "delete from test where id = %(id)s",
            [{'id': 1}, {'id': 2}],
            batch_size=100)
        self.conn.commit()
        assert self.t1.count() == 3

    def test_executemany_insert(self):
        cur = self.conn.cursor()
        cur.execute('delete from test')
        N = 1000
        self.executemany(
            "insert into test (id, name) values (%s, %s)",
            ((i, f"i={i * 10}") for i in range(N)))
        self.conn.commit()
        assert self.t1.count() == N
        cur.execute("select id, name from test order by id")
        assert cur.fetchall() == [(i, f"i={i * 10}") for i in range(N)]
