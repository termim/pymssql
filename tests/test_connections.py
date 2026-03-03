# -*- coding: utf-8 -*-
"""
Test connection to database.
"""

from __future__ import with_statement
from os import path, makedirs, environ
import re
import unittest
import tempfile

import pytest

from pymssql import _mssql

from .conftest import mssqlconn


@pytest.fixture
def conn_params(test_cfg):
    """Fixture providing connection parameters."""
    return {
        'server': test_cfg.server,
        'username': test_cfg.user,
        'password': test_cfg.password,
        'database': test_cfg.database,
        'port': test_cfg.port,
        'ipaddress': test_cfg.ipaddress,
        'instance': test_cfg.instance,
    }


def connect_with_debug(**kwargs):
    """Helper function to capture FreeTDS debug output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dump_path = path.join(tmpdir, 'freetds-config-dump.txt')
        dump_path = path.join(tmpdir, 'freetds-dump.txt')
        environ['TDSDUMPCONFIG'] = config_dump_path
        environ['TDSDUMP'] = dump_path
        _mssql.connect(**kwargs)
        with open(config_dump_path, 'r') as fh:
            return fh.read()


@pytest.mark.mssql_server_required
def test_connection_tds_version(conn_params):
    """Test TDS version negotiation."""
    for tds_version in ('4.2', '7.0', '7.1', '7.2', '7.3', '7.4'):
        cdump = connect_with_debug(
            server=conn_params['server'],
            port=conn_params['port'],
            user=conn_params['username'],
            password=conn_params['password'],
            tds_version=tds_version
        )
        major_version = re.search('major_version = (\\S+)', cdump).groups()[0]
        minor_version = re.search('minor_version = (\\S+)', cdump).groups()[0]
        actual_version = f"{major_version}.{minor_version}"
        assert tds_version == actual_version, f"Expected {tds_version}, got {actual_version}"


@pytest.mark.mssql_server_required
def test_connection_by_dns_name(conn_params):
    """Test connection by DNS name."""
    cdump = connect_with_debug(
        server=conn_params['server'],
        port=conn_params['port'],
        user=conn_params['username'],
        password=conn_params['password']
    )
    dump_server_name = re.search('server_name = (\\S+)', cdump).groups()[0]
    assert conn_params['server'] in dump_server_name
    dump_server_host_name = re.search('server_host_name = (\\S+)', cdump).groups()[0]
    assert dump_server_host_name == conn_params['server']
    dump_user_name = re.search('user_name = (\\S+)', cdump).groups()[0]
    assert dump_user_name == conn_params['username']
    dump_port = re.search('port = (\\S+)', cdump).groups()[0]
    assert conn_params['port'] in dump_port


@pytest.mark.mssql_server_required
def test_connection_by_ip(conn_params):
    """Test connection by IP address."""
    cdump = connect_with_debug(
        server=conn_params['ipaddress'],
        port=conn_params['port'],
        user=conn_params['username'],
        password=conn_params['password']
    )
    dump_server_name = re.search('server_name = (\\S+)', cdump).groups()[0]
    assert conn_params['ipaddress'] in dump_server_name
    dump_server_host_name = re.search('server_host_name = (\\S+)', cdump).groups()[0]
    assert dump_server_host_name == conn_params['ipaddress']


@pytest.mark.mssql_server_required
def test_port_override_ipaddress(conn_params):
    """Test port override with IP address."""
    server_join = '%s:%s' % (conn_params['ipaddress'], conn_params['port'])
    cdump = connect_with_debug(server=server_join, user=conn_params['username'], password=conn_params['password'])
    dump_server_name = re.search('server_name = (\\S+)', cdump).groups()[0]
    assert conn_params['ipaddress'] in dump_server_name
    dump_server_host_name = re.search('server_host_name = (\\S+)', cdump).groups()[0]
    assert dump_server_host_name == conn_params['ipaddress']
    dump_port = re.search('port = (\\S+)', cdump).groups()[0]
    assert conn_params['port'] in dump_port


@pytest.mark.mssql_server_required
def test_port_override_name(conn_params):
    """Test port override with DNS name."""
    server_join = '%s:%s' % (conn_params['server'], conn_params['port'])
    cdump = connect_with_debug(server=server_join, user=conn_params['username'], password=conn_params['password'])
    dump_server_name = re.search('server_name = (\\S+)', cdump).groups()[0]
    assert conn_params['server'] in dump_server_name
    dump_server_host_name = re.search('server_host_name = (\\S+)', cdump).groups()[0]
    assert dump_server_host_name == conn_params['server']
    dump_port = re.search('port = (\\S+)', cdump).groups()[0]
    assert conn_params['port'] in dump_port


@pytest.mark.mssql_server_required
def test_instance(conn_params):
    """Test named instance connection."""
    if not conn_params['instance']:
        pytest.skip("No instance configured")
    server_join = r'%s\%s' % (conn_params['server'], conn_params['instance'])
    cdump = connect_with_debug(server=server_join, user=conn_params['username'], password=conn_params['password'])
    dump_server_name = re.search('server_name = (\\S+)', cdump).groups()[0]
    assert conn_params['server'] in dump_server_name
    dump_server_host_name = re.search('server_host_name = (\\S+)', cdump).groups()[0]
    assert dump_server_host_name == conn_params['server']
    dump_port = re.search('port = (\\S+)', cdump).groups()[0]
    assert dump_port == '0'


@pytest.mark.mssql_server_required
def test_valid_tds_version_property(mssql_conn_function):
    """Test TDS version property. Issue #211."""
    conn = mssql_conn_function
    assert conn.tds_version is not None
    assert conn.tds_version > 0


@pytest.mark.mssql_server_required
def test_conn_props_override(test_cfg):
    """Test connection properties override."""
    conn = mssqlconn(conn_properties='SET TEXTSIZE 2147483647')
    conn.close()

    conn = mssqlconn(conn_properties='SET TEXTSIZE 2147483647;')
    conn.close()

    conn = mssqlconn(conn_properties='SET TEXTSIZE 2147483647;SET ANSI_NULLS ON;')
    conn.close()

    conn = mssqlconn(conn_properties='SET TEXTSIZE 2147483647;SET ANSI_NULLS ON')
    conn.close()

    conn = mssqlconn(conn_properties='SET TEXTSIZE 2147483647;'
                     'SET ANSI_NULLS ON;')
    conn.close()

    conn = mssqlconn(conn_properties=['SET TEXTSIZE 2147483647;', 'SET ANSI_NULLS ON'])
    conn.close()
    assert _mssql.MSSQLDriverException, mssqlconn(conn_properties='BOGUS SQL')

    conn = _mssql.connect(
        conn_properties='SET TEXTSIZE 2147483647',
        server=test_cfg.server,
        user=test_cfg.user,
        password=test_cfg.password
    )
    conn.close()


@pytest.mark.slow
@pytest.mark.xfail(strict=False, reason="Could timeout, or fail with different error messages")
@pytest.mark.timeout(600)
def test_repeated_failed_connections():
    """Test repeated failed connections. Issue #145."""
    _mssql.login_timeout = 5
    last_exc_message = None
    for i in range(5):
        try:
            _mssql.connect(
                server='www.google.com',
                port=81,
                user='joe',
                password='secret',
                database='tempdb')
        except Exception as exc:
            exc_message = exc.args[0][1]

            if last_exc_message:
                assert exc_message == last_exc_message

            last_exc_message = exc_message
