# -*- coding: utf-8 -*-
"""
Various test helper functions.
"""

import logging
import time

import pytest
from pymssql import _mssql
import pymssql


def eq_(a, b):
    assert a == b, f"'{a}' != '{b}'"

def skip_test(reason='No reason given to skip_test'):
    pytest.skip(reason)

def mark_slow(f):
    return f

mssql_server_required = pytest.mark.mssql_server_required



class Config(object):
    def __str__(self):
        return f"server={self.server}, port={self.port}, database={self.database}, " \
               f"user={self.user}, password={self.password}"

config = Config()


def mssqlconn(conn_properties=None):
    return _mssql.connect(
        server=config.server,
        user=config.user,
        password=config.password,
        database=config.database,
        port=config.port,
        conn_properties=conn_properties
    )


def pymssqlconn(**kwargs):
    return pymssql.connect(
        server=config.server,
        user=config.user,
        password=config.password,
        database=config.database,
        port=config.port,
        **kwargs
    )


def drop_table(conn, tname):
    sql = "if object_id('%s') is not null drop table %s" % (tname, tname)
    conn.execute_non_query(sql)


def clear_table(conn, tname):
    sql = 'delete from %s' % tname
    conn.execute_non_query(sql)


class PyTableBase(object):
    tname = 'pymssql'
    cols = tuple()
    idtype = None

    @classmethod
    def table_sql(cls):
        return 'CREATE TABLE %s (%s)' % (cls.tname, ', '.join(cls.cols))

    @classmethod
    def newconn(cls):
        cls.conn = pymssqlconn()

    @classmethod
    def setup_class(cls):
        cls.newconn()
        # table related commands managed by this class are handled in a
        # different connection
        cls._conn = mssqlconn()
        drop_table(cls._conn, cls.tname)
        cls._conn.execute_non_query(cls.table_sql())

    def setUp(self):
        clear_table(self._conn, self.tname)

    def row_count(self):
        sql = 'select count(*) from %s' % self.tname
        return self.conn._conn.execute_scalar(sql)

    def execute(self, sql, params=None):
        cur = self.conn.cursor()
        cur.execute(sql, params)
        return cur


class TableManager(object):
    def __init__(self, conn, tname, *cols):
        self.conn = conn
        self.tname = tname
        self.cols = cols

        self.create()

    def table_sql(self):
        return 'CREATE TABLE %s (%s)' % (self.tname, ', '.join(self.cols))

    def drop(self):
        #mssql
        sql = "if object_id('%s') is not null drop table %s" % (
            self.tname, self.tname)
        try:
            self.execute(sql)
        except Exception as e:
            self.conn.rollback()
            if 'syntax error' not in str(e):
                raise
            #sqlite
            sql = 'drop table if exists %s' % self.tname
            self.execute(sql)

    def execute(self, sql):
        cur = self.conn.cursor()
        cur.execute(sql)
        self.conn.commit()

    def create(self):
        self.drop()
        self.execute(self.table_sql())

    def clear(self):
        sql = 'delete from %s' % self.tname
        self.execute(sql)

    def count(self):
        sql = 'select count(*) from %s' % self.tname
        cur = self.conn.cursor()
        cur.execute(sql)
        return cur.fetchone()[0]



def clear_db():
    conn = mssqlconn()
    mapping = {
        'P': 'drop procedure [%(name)s]',
        'C': 'alter table [%(parent_name)s] drop constraint [%(name)s]',
        ('FN', 'IF', 'TF'): 'drop function [%(name)s]',
        'V': 'drop view [%(name)s]',
        'F': 'alter table [%(parent_name)s] drop constraint [%(name)s]',
        'U': 'drop table [%(name)s]',
    }
    delete_sql = []
    for type, drop_sql in mapping.items():
        sql = 'select name, object_name( parent_object_id ) as parent_name '\
            'from sys.objects where type in (\'%s\')' % '", "'.join(type)
        conn.execute_query(sql)
        for row in conn:
            if row['name'][0] not in ('#','@'):
                delete_sql.append(drop_sql % dict(row))
    for sql in delete_sql:
        conn.execute_non_query(sql)


class StoredProc(object):
    def __init__(self, name, args, body, mssql=None):
        self.name = name
        self.args = args
        self.body = body
        self.mssql = mssql
        logger_name = '.'.join([__name__, self.__class__.__name__, self.name])
        self.logger = logging.getLogger(logger_name)

    def create(self, mssql=None):
        mssql = mssql or self.mssql
        if not mssql:
            mssql = self.mssql = mssqlconn()

        try:
            self.drop(mssql)
        except:
            pass

        mssql.execute_non_query("""
        CREATE PROCEDURE [dbo].[%(name)s]
            %(args)s
        AS
        BEGIN
            %(body)s
        END
        """ % {
            'name': self.name,
            'args': '\n'.join(self.args),
            'body': self.body,
        })
        self.logger.debug("Created stored proc: %r" % self.name)
        return self

    def execute(self, mssql=None, args=()):
        mssql = mssql or self.mssql
        if not mssql:
            mssql = self.mssql = mssqlconn()
        proc = mssql.init_procedure(self.name)
        for arg in args:
            proc.bind(*arg)
        self.logger.debug("Calling stored proc: %r" % self.name)
        proc.execute()
        self.logger.debug("Called stored proc: %r" % self.name)

    def drop(self, mssql=None):
        mssql = mssql or self.mssql
        if not mssql:
            mssql = self.mssql = mssqlconn()
        mssql.execute_non_query("DROP PROCEDURE [dbo].[%s]" % self.name)
        self.logger.debug("Dropped stored proc: %r" % self.name)
        if self.mssql:
            self.mssql.close()
            self.logger.debug("Closed mssql connection: %r" % self.mssql)
            self.mssql = None

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        self.drop()


def get_sql_server_version(mssql_connection):
    """
    Returns the version of the SQL Server in use:
    """
    result = mssql_connection.execute_scalar(
        "SELECT CAST(SERVERPROPERTY('ProductVersion') as varchar)"
    )
    ver_code = int(result.split('.')[0])
    if ver_code >= 12:
        major_version = 2014
    elif ver_code == 11:
        major_version = 2012
    elif ver_code == 10:
        major_version = 2008
    elif ver_code == 9:
        major_version = 2005
    else:
        major_version = 2000
    return major_version
