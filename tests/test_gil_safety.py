"""Tests for free-threaded Python support."""

import logging
import os
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest


def is_free_threaded():
    return (
        sys.version_info >= (3, 13)
        and hasattr(sys, "_is_gil_enabled")
        and not sys._is_gil_enabled()
    )


pytestmark = pytest.mark.skipif(
    not is_free_threaded(), reason="Requires free-threaded Python with the GIL disabled"
)

logger = logging.getLogger(__name__)


def test_extensions_import_without_enabling_gil():
    code = """
import sys
import pymssql._mssql
import pymssql._pymssql
print(sys._is_gil_enabled())
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHON_GIL": "0"},
    )

    assert result.returncode == 0, (
        f"Extension import failed.\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert result.stdout.strip() == "False"
    assert "global interpreter lock" not in result.stderr.lower()


def test_gil_remains_disabled_after_import():
    import pymssql._mssql
    import pymssql._pymssql

    assert not sys._is_gil_enabled()


@pytest.mark.mssql_server_required
def test_concurrent_operations_use_independent_connections():
    from tests.helpers import mssqlconn

    def query_on_own_connection(thread_id):
        stage = "connecting"
        logger.debug(
            "free-threaded test start thread_id=%d native_id=%s stage=%s",
            thread_id,
            threading.get_native_id(),
            stage,
        )
        try:
            # Each worker owns its connection; connection sharing is unsupported.
            with mssqlconn() as conn:
                for query_id in range(50):
                    stage = f"query {query_id}"
                    result = conn.execute_scalar(
                        "SELECT %d * %d", (thread_id, query_id)
                    )
                    assert result == thread_id * query_id
            return thread_id
        except Exception:
            logger.exception(
                "free-threaded test failed thread_id=%d native_id=%s stage=%s",
                thread_id,
                threading.get_native_id(),
                stage,
            )
            raise

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(query_on_own_connection, range(10)))

    assert results == list(range(10))


@pytest.mark.mssql_server_required
def test_failed_connect_error_state_is_isolated():
    from pymssql import _mssql
    from tests.helpers import config

    num_connections = 8
    start = threading.Barrier(num_connections)

    def fail_to_connect(thread_id):
        server = f"pymssql_missing_host_{thread_id}.invalid"
        stage = "waiting to connect to a missing host"
        logger.debug(
            "free-threaded test start thread_id=%d native_id=%s stage=%s",
            thread_id,
            threading.get_native_id(),
            stage,
        )
        try:
            start.wait(timeout=30)
            stage = "connecting to a missing host"
            # Exercise fallback buffers before dbopen() has a registered DBPROCESS.
            conn = _mssql.connect(
                server=server,
                user=config.user,
                password=config.password,
                database=config.database,
                port=config.port,
            )
            conn.close()
            pytest.fail(f"Connection unexpectedly opened server {server!r}")
        except _mssql.MSSQLDatabaseException as exc:
            error_text = exc.text.decode("utf-8", "replace")
            if server not in error_text:
                logger.error(
                    "free-threaded error state mismatch thread_id=%d "
                    "native_id=%s stage=%s expected_server=%s error_text=%r",
                    thread_id,
                    threading.get_native_id(),
                    stage,
                    server,
                    error_text,
                    exc_info=(type(exc), exc, exc.__traceback__),
                )
                raise AssertionError(
                    f"thread_id={thread_id} stage={stage}: error did not identify "
                    f"{server!r}: {error_text!r}"
                )
            return server
        except Exception:
            logger.exception(
                "free-threaded test failed thread_id=%d native_id=%s stage=%s",
                thread_id,
                threading.get_native_id(),
                stage,
            )
            raise

    with ThreadPoolExecutor(max_workers=num_connections) as executor:
        errors = list(executor.map(fail_to_connect, range(num_connections)))

    assert errors == [
        f"pymssql_missing_host_{thread_id}.invalid"
        for thread_id in range(num_connections)
    ]
