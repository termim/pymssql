# -*- coding: utf-8 -*-

import datetime
import pytest

from pymssql import datetime2


def insert_and_select(conn, table_name, column_name, value, params_as_dict=False):
    """Insert value into table and select it back."""
    # Clear table before insert
    conn.execute_non_query(f"DELETE FROM {table_name}")

    if params_as_dict:
        sql = f'insert into {table_name} ({column_name}) values (%(value)s)'
        conn.execute_non_query(sql, dict(value=value))
    else:
        sql = f'insert into {table_name} ({column_name}) values (%s)'
        conn.execute_non_query(sql, value)

    conn.execute_query(f'select {column_name} from {table_name}')
    rows = tuple(conn)
    assert len(rows) == 1
    return rows[0][column_name]


# DATETIME2 tests


@pytest.mark.mssql_server_required
class Test_DATETIME2:
    """Tests for DATETIME2 data type."""

    @pytest.fixture(scope='class', autouse=True)
    def setup_table(self, mssql_conn, datetime2_supported):
        table_name = "test_datetime2"
        ddl_create = f"CREATE TABLE {table_name} (test DATETIME2)"
        ddl_drop = f"IF OBJECT_ID('{table_name}') IS NOT NULL DROP TABLE {table_name}"

        mssql_conn.execute_non_query(ddl_drop)
        mssql_conn.execute_non_query(ddl_create)

        yield table_name, ddl_drop

        mssql_conn.execute_non_query(ddl_drop)

    def test_min_select(self, mssql_conn, setup_table):
        mssql_conn.execute_query("SELECT CAST ('0001-1-1 0:0:0' as DATETIME2)")
        res = tuple(mssql_conn)[0][0]
        assert isinstance(res, datetime.datetime)
        assert res == datetime2(1, 1, 1, 0, 0, 0, 0)

    def test_min_insert(self, mssql_conn, setup_table):
        table_name, _ = setup_table
        testval = datetime2(1, 1, 1, 0, 0, 0, 0)
        res = insert_and_select(mssql_conn, table_name, 'test', testval)
        assert isinstance(res, datetime.datetime)
        assert res == testval

    def test_max_select(self, mssql_conn, setup_table):
        mssql_conn.execute_query("SELECT CAST ('9999-12-31 23:59:59.9999999' as DATETIME2)")
        res = tuple(mssql_conn)[0][0]
        assert isinstance(res, datetime.datetime)
        assert res == datetime2(9999, 12, 31, 23, 59, 59, 999999)

    def test_max_insert(self, mssql_conn, setup_table):
        table_name, _ = setup_table
        testval = datetime2(9999, 12, 31, 23, 59, 59, 999999)
        res = insert_and_select(mssql_conn, table_name, 'test', testval)
        assert isinstance(res, datetime.datetime)
        assert res == testval

    def test_datetime2(self, mssql_conn, setup_table):
        table_name, _ = setup_table
        testval = datetime2(2013, 1, 2, 3, 4, 5, 6)
        res = insert_and_select(mssql_conn, table_name, 'test', testval)
        assert isinstance(res, datetime.datetime)
        assert testval == res

    def test_truncate(self, mssql_conn, setup_table):
        mssql_conn.execute_query("SELECT CAST ('2024-1-1 0:0:0.1234567' as DATETIME2)")
        res = tuple(mssql_conn)[0][0]
        assert isinstance(res, datetime.datetime)
        assert res == datetime.datetime(2024, 1, 1, 0, 0, 0, 123456)


@pytest.mark.mssql_server_required
class Test_695:
    """Test issue #695 - temporal tables."""

    @pytest.fixture(scope='class', autouse=True)
    def setup_table(self, mssql_conn, datetime2_supported):
        table_name = "dbo.test695"
        ddl_create = f"""
            CREATE TABLE {table_name} (
                valid_from DATETIME2 GENERATED ALWAYS AS ROW START NOT NULL,
                valid_to DATETIME2 GENERATED ALWAYS AS ROW END NOT NULL,
                PERIOD FOR SYSTEM_TIME (valid_from,valid_to),
                id INTEGER NOT NULL IDENTITY(1,1) PRIMARY KEY,
                test VARCHAR(255) NOT NULL,
                )
        """
        ddl_drop = f"IF OBJECT_ID('{table_name}') IS NOT NULL DROP TABLE {table_name}"

        mssql_conn.execute_non_query(ddl_drop)
        mssql_conn.execute_non_query(ddl_create)

        yield table_name, ddl_drop

        mssql_conn.execute_non_query(ddl_drop)

    def test_695(self, mssql_conn, setup_table):
        table_name, _ = setup_table
        mssql_conn.execute_non_query(f"INSERT INTO {table_name} (test) VALUES (%s)", ("TEST", ))
        mssql_conn.execute_query(f"SELECT valid_from, valid_to FROM {table_name}")
        rows = tuple(mssql_conn)
        res = rows[0][1]
        assert isinstance(res, datetime.datetime)


@pytest.mark.mssql_server_required
class Test_DATETIME:
    """Tests for DATETIME data type."""

    @pytest.fixture(scope='class', autouse=True)
    def setup_table(self, mssql_conn, datetime2_supported):
        table_name = "test_datetime"
        ddl_create = f"CREATE TABLE {table_name} (test DATETIME)"
        ddl_drop = f"IF OBJECT_ID('{table_name}') IS NOT NULL DROP TABLE {table_name}"

        mssql_conn.execute_non_query(ddl_drop)
        mssql_conn.execute_non_query(ddl_create)

        yield table_name, ddl_drop

        mssql_conn.execute_non_query(ddl_drop)

    def test_min_select(self, mssql_conn, setup_table):
        mssql_conn.execute_query("SELECT CAST ('1753-1-1 0:0:0' as DATETIME)")
        res = tuple(mssql_conn)[0][0]
        assert isinstance(res, datetime.datetime)
        assert not isinstance(res, datetime2)
        assert res == datetime.datetime(1753, 1, 1, 0, 0, 0, 0)

    def test_min_insert(self, mssql_conn, setup_table):
        table_name, _ = setup_table
        testval = datetime.datetime(1753, 1, 1, 0, 0, 0, 0)
        res = insert_and_select(mssql_conn, table_name, 'test', testval)
        assert isinstance(res, datetime.datetime)
        assert not isinstance(res, datetime2)
        assert res == testval

    def test_max_select(self, mssql_conn, setup_table):
        mssql_conn.execute_query("SELECT CAST ('9999-12-31 23:59:59.997' as DATETIME)")
        res = tuple(mssql_conn)[0][0]
        assert isinstance(res, datetime.datetime)
        assert not isinstance(res, datetime2)
        assert res == datetime.datetime(9999, 12, 31, 23, 59, 59, 997000)

    def test_max_insert(self, mssql_conn, setup_table):
        table_name, _ = setup_table
        testval = datetime.datetime(9999, 12, 31, 23, 59, 59, 997000)
        res = insert_and_select(mssql_conn, table_name, 'test', testval)
        assert isinstance(res, datetime.datetime)
        assert not isinstance(res, datetime2)
        assert res == testval

    def test_datetime(self, mssql_conn, setup_table):
        """Test for issue #118: datetime values are rounded."""
        table_name, _ = setup_table
        for mks in (0, 3000, 7000):
            testval = datetime.datetime(2013, 1, 2, 3, 4, 5, mks)
            mssql_conn.execute_non_query(f"DELETE FROM {table_name}")
            res = insert_and_select(mssql_conn, table_name, 'test', testval)
            assert isinstance(res, datetime.datetime)
            assert not isinstance(res, datetime2)
            assert res == testval

    def test_datetime_params_as_dict(self, mssql_conn, setup_table):
        table_name, _ = setup_table
        testval = datetime.datetime(2013, 1, 2, 3, 4, 5, 3000)
        res = insert_and_select(mssql_conn, table_name, 'test', testval, params_as_dict=True)
        assert isinstance(res, datetime.datetime)
        assert not isinstance(res, datetime2)
        assert res == testval


@pytest.mark.mssql_server_required
class Test_DATE:
    """Tests for DATE data type."""

    @pytest.fixture(scope='class', autouse=True)
    def setup_table(self, mssql_conn, datetime2_supported):
        table_name = "test_date"
        ddl_create = f"CREATE TABLE {table_name} (test DATE)"
        ddl_drop = f"IF OBJECT_ID('{table_name}') IS NOT NULL DROP TABLE {table_name}"

        mssql_conn.execute_non_query(ddl_drop)
        mssql_conn.execute_non_query(ddl_create)

        yield table_name, ddl_drop

        mssql_conn.execute_non_query(ddl_drop)

    def test_min_select(self, mssql_conn, setup_table):
        mssql_conn.execute_query("SELECT CAST ('0001-1-1' as DATE)")
        res = tuple(mssql_conn)[0][0]
        assert isinstance(res, datetime.date)
        assert res == datetime.date(1, 1, 1)

    def test_min_insert(self, mssql_conn, setup_table):
        table_name, _ = setup_table
        testval = datetime.date(1, 1, 1)
        res = insert_and_select(mssql_conn, table_name, 'test', testval)
        assert isinstance(res, datetime.date)
        assert res == testval

    def test_max_select(self, mssql_conn, setup_table):
        mssql_conn.execute_query("SELECT CAST ('9999-12-31' as DATE)")
        res = tuple(mssql_conn)[0][0]
        assert isinstance(res, datetime.date)
        assert res == datetime.date(9999, 12, 31)

    def test_max_insert(self, mssql_conn, setup_table):
        table_name, _ = setup_table
        testval = datetime.date(9999, 12, 31)
        res = insert_and_select(mssql_conn, table_name, 'test', testval)
        assert isinstance(res, datetime.date)
        assert res == testval

    def test_date(self, mssql_conn, setup_table):
        table_name, _ = setup_table
        testval = datetime.date(2013, 1, 2)
        res = insert_and_select(mssql_conn, table_name, 'test', testval)
        assert isinstance(res, datetime.date)
        assert res == testval

    def test_ancient_date(self, mssql_conn, setup_table):
        table_name, _ = setup_table
        testval = datetime.date(13, 1, 2)
        res = insert_and_select(mssql_conn, table_name, 'test', testval)
        assert isinstance(res, datetime.date)
        assert res == testval


@pytest.mark.mssql_server_required
class Test_TIME:
    """Tests for TIME data type."""

    @pytest.fixture(scope='class', autouse=True)
    def setup_table(self, mssql_conn, datetime2_supported):
        table_name = "test_time"
        ddl_create = f"CREATE TABLE {table_name} (test TIME)"
        ddl_drop = f"IF OBJECT_ID('{table_name}') IS NOT NULL DROP TABLE {table_name}"

        mssql_conn.execute_non_query(ddl_drop)
        mssql_conn.execute_non_query(ddl_create)

        yield table_name, ddl_drop

        mssql_conn.execute_non_query(ddl_drop)

    def test_min_select(self, mssql_conn, setup_table):
        mssql_conn.execute_query("SELECT CAST ('0:0:0.0' as TIME)")
        res = tuple(mssql_conn)[0][0]
        assert isinstance(res, datetime.time)
        assert res == datetime.time(0, 0, 0, 0)

    def test_min_insert(self, mssql_conn, setup_table):
        table_name, _ = setup_table
        testval = datetime.time(0, 0, 0, 0)
        res = insert_and_select(mssql_conn, table_name, 'test', testval)
        assert isinstance(res, datetime.time)
        assert res == testval

    def test_max_select(self, mssql_conn, setup_table):
        mssql_conn.execute_query("SELECT CAST ('23:59:59.9999999' as TIME)")
        res = tuple(mssql_conn)[0][0]
        assert isinstance(res, datetime.time)
        assert res == datetime.time(23, 59, 59, 999999)

    def test_max_insert(self, mssql_conn, setup_table):
        table_name, _ = setup_table
        testval = datetime.time(23, 59, 59, 999999)
        res = insert_and_select(mssql_conn, table_name, 'test', testval)
        assert isinstance(res, datetime.time)
        assert res == testval

    def test_time(self, mssql_conn, setup_table):
        table_name, _ = setup_table
        testval = datetime.time(3, 4, 5, 3000)
        res = insert_and_select(mssql_conn, table_name, 'test', testval)
        assert isinstance(res, datetime.time)
        assert res == testval


@pytest.mark.mssql_server_required
class Test_DATETIMEOFFSET:
    """Tests for DATETIMEOFFSET data type."""

    @pytest.fixture(scope='class', autouse=True)
    def setup_table(self, mssql_conn, datetime2_supported):
        table_name = "test_datetimeoffset"
        ddl_create = f"""CREATE TABLE {table_name} (
                            id INT default 1,
                            DateCreated DATETIMEOFFSET default sysdatetimeoffset()
                        )"""
        ddl_drop = f"IF OBJECT_ID('{table_name}') IS NOT NULL DROP TABLE {table_name}"

        mssql_conn.execute_non_query(ddl_drop)
        mssql_conn.execute_non_query(ddl_create)

        yield table_name, ddl_drop

        mssql_conn.execute_non_query(ddl_drop)

    def test_649(self, mssql_conn, setup_table):
        """Test #649."""
        table_name, _ = setup_table
        mssql_conn.execute_non_query(
            f"INSERT INTO {table_name} (id) VALUES (%s)", (2, ))
        mssql_conn.execute_query(
            f'select DateCreated from {table_name} where id = 2')
        res = tuple(mssql_conn)[0][0]
        assert isinstance(res, datetime.datetime)
        assert res.strftime('%z') != ''

    def test_select_cast_0(self, mssql_conn, setup_table):
        mssql_conn.execute_query(
            "SELECT CAST ('2019-06-20 09:54:40.09550' as DATETIMEOFFSET)")
        res = tuple(mssql_conn)[0][0]
        assert isinstance(res, datetime.datetime)
        assert res == datetime.datetime(2019, 6, 20, 9, 54, 40, 95500,
                                        tzinfo=datetime.timezone.utc)

    def test_select_cast(self, mssql_conn, setup_table):
        mssql_conn.execute_query(
            "SELECT CAST ('2019-06-20 09:54:40.09550 +04:00' as DATETIMEOFFSET)")
        res = tuple(mssql_conn)[0][0]
        assert isinstance(res, datetime.datetime)
        assert res == datetime.datetime(2019, 6, 20, 9, 54, 40, 95500,
                    tzinfo=datetime.timezone(datetime.timedelta(seconds=4*60*60)))

    def test_insert_select(self, mssql_conn, setup_table):
        table_name, _ = setup_table
        testval = datetime.datetime(3, 4, 5, 3,
                    tzinfo=datetime.timezone(datetime.timedelta(seconds=4*60*60)))
        mssql_conn.execute_non_query(
            f"INSERT INTO {table_name} (id, DateCreated) VALUES (%s, %s)",
            (22, testval))
        mssql_conn.execute_query(
            f'select DateCreated from {table_name} where id = 22')
        res = tuple(mssql_conn)[0][0]
        assert isinstance(res, datetime.datetime)
        assert res.strftime('%z') != ''
        assert res == testval
