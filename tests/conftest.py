# -*- coding: utf-8 -*-
"""
Pytest configuration.
"""

import decimal
import os
from configparser import ConfigParser

import pytest
from pymssql import _mssql
import pymssql


cdir = os.path.dirname(__file__)
cfgpath = os.path.join(cdir, 'tests.cfg')


class Config:
    """Configuration class for test connection settings."""
    def __init__(self):
        self.server = 'localhost'
        self.user = 'sa'
        self.password = 'sqlServerPassw0rd'
        self.database = 'tempdb'
        self.port = '1433'
        self.ipaddress = '127.0.0.1'
        self.instance = ''
        self.orig_decimal_prec = None

    def __str__(self):
        return f"server={self.server}, port={self.port}, database={self.database}, " \
               f"user={self.user}, password={self.password}"


# Global config instance
config = Config()


def mssqlconn(conn_properties=None):
    """Create a _mssql.MSSQLConnection."""
    return _mssql.connect(
        server=config.server,
        user=config.user,
        password=config.password,
        database=config.database,
        port=config.port,
        conn_properties=conn_properties
    )


def pymssqlconn(**kwargs):
    """Create a pymssql.Connection."""
    return pymssql.connect(
        server=config.server,
        user=config.user,
        password=config.password,
        database=config.database,
        port=config.port,
        **kwargs
    )


@pytest.fixture(scope="module")
def mssql_conn():
    """Fixture providing _mssql.MSSQLConnection (low-level API)."""
    return mssqlconn()


@pytest.fixture(scope="function")
def mssql_conn_function():
    """Fixture providing a new _mssql.MSSQLConnection for each test."""
    conn = mssqlconn()
    yield conn
    conn.close()


@pytest.fixture(scope="module")
def pymssql_conn():
    """Fixture providing pymssql.Connection (high-level DB-API)."""
    return pymssqlconn()


@pytest.fixture(scope="function")
def pymssql_conn_function():
    """Fixture providing a new pymssql.Connection for each test."""
    conn = pymssqlconn()
    yield conn
    conn.close()


@pytest.fixture(scope="module")
def sql_server_version(mssql_conn):
    """Fixture providing SQL Server version."""
    result = mssql_conn.execute_scalar(
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


@pytest.fixture(scope="module")
def datetime2_supported(mssql_conn, sql_server_version):
    """Check if DATETIME2 is supported (SQL Server 2008+ and TDS 7.3+)."""
    if sql_server_version < 2008:
        pytest.skip("DATETIME2 field type isn't supported by SQL Server versions prior to 2008.")
    if mssql_conn.tds_version < 7.3:
        pytest.skip("DATETIME2 field type isn't supported by TDS protocol older than 7.3.")
    return True


_parser = ConfigParser({
    'server': 'localhost',
    'username': 'sa',
    'password': 'sqlServerPassw0rd',
    'database': 'tempdb',
    'port': '1433',
    'ipaddress': '127.0.0.1',
    'instance': '',
})

optional_markers = {
    "slow": {"help": "Skip long tests",
             "marker-descr": "Mark tests that run longer than ~3 seconds",
             "skip-reason": "Test runs too long."},
    "mssql_server_required": {"help": "Skip tests that require MSSQL server",
             "marker-descr": "Mark tests that require MSSQL server",
             "skip-reason": "Test only runs if MSSQL server is available."},
    # add further markers here
}


def clear_db():
    """Clear all test objects from database."""
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
    conn.close()


def pytest_addoption(parser):
    parser.addoption(
        "--pymssql-section",
        type=str,
        default=os.environ.get('PYMSSQL_TEST_CONFIG', None),
        help="The name of the section to use from tests.cfg"
    )
    for marker, info in optional_markers.items():
        parser.addoption("--skip-{}".format(marker.replace('_','-')), action="store_true",
                         default=False, help=info['help'])

def pytest_configure(config):
    section = config.getoption('--pymssql-section')
    if section is not None:
        if not os.path.exists(cfgpath):
            raise ValueError(f"Config file '{cfgpath}' dos not exist.")
        _parser.read(cfgpath)
        if not _parser.has_section(section):
            raise ValueError('the tests.cfg file does not have section: %s' % section)
    else:
        section = 'DEFAULT'

    config.server = os.getenv('PYMSSQL_TEST_SERVER') or _parser.get(section, 'server')
    config.user = os.getenv('PYMSSQL_TEST_USERNAME') or _parser.get(section, 'username')
    config.password = os.getenv('PYMSSQL_TEST_PASSWORD') or _parser.get(section, 'password')
    config.database = os.getenv('PYMSSQL_TEST_DATABASE') or _parser.get(section, 'database')
    config.port = os.getenv('PYMSSQL_TEST_PORT') or _parser.get(section, 'port')
    config.ipaddress = os.getenv('PYMSSQL_TEST_IPADDRESS') or _parser.get(section, 'ipaddress')
    config.instance = os.getenv('PYMSSQL_TEST_INSTANCE') or _parser.get(section, 'instance')
    config.orig_decimal_prec = decimal.getcontext().prec

    for marker, info in optional_markers.items():
        config.addinivalue_line("markers",
                                "{}: {}".format(marker, info['marker-descr']))

    clear_db()


def pytest_collection_modifyitems(config, items):
    # Check if MSSQL server is available
    try:
        test_conn = mssqlconn()
        mssql_available = True
        test_conn.close()
    except Exception:
        mssql_available = False

    marker = "mssql_server_required"
    info = optional_markers[marker]
    if not mssql_available or config.getoption("--skip-{}".format(marker.replace('_','-'))):
        skip = pytest.mark.skip(reason=info['skip-reason'])
        for item in items:
            if marker in item.keywords:
                item.add_marker(skip)
    marker = "slow"
    info = optional_markers[marker]
    if not mssql_available or config.getoption("--skip-{}".format(marker)):
        skip = pytest.mark.skip(reason=info['skip-reason'])
        for item in items:
            if marker in item.keywords:
                item.add_marker(skip)
