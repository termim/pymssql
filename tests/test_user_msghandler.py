# -*- coding: utf-8 -*-
"""
Test user message handler.
"""

import pytest

from .helpers import config

msgs = []


def user_msg_handler1(msgstate, severity, srvname, procname, line, msgtext):
    global msgs
    procname = procname.decode('ascii')
    msgtext = msgtext.decode('ascii')
    entry = ("msg_handler1: msgstate = %d, severity = %d, procname = '%s', "
             "line = %d, msgtext = '%s'") % (msgstate, severity, procname, line, msgtext)
    msgs.append(entry)


def user_msg_handler2(msgstate, severity, srvname, procname, line, msgtext):
    global msgs
    procname = procname.decode('ascii')
    msgtext = msgtext.decode('ascii')
    entry = ("msg_handler2: msgstate = %d, severity = %d, procname = '%s', "
             "line = %d, msgtext = '%s'") % (msgstate, severity, procname, line, msgtext)
    msgs.append(entry)


def wrong_signature_msg_handler():
    pass


@pytest.fixture
def conn(mssql_conn_function):
    """Fixture providing a new _mssql connection for each test."""
    yield mssql_conn_function
    mssql_conn_function.close()


@pytest.mark.mssql_server_required
class TestUserMsgHandler:

    def test_basic_functionality(self, conn):
        conn.set_msghandler(user_msg_handler1)
        msgs_before = len(msgs)
        conn.execute_non_query("USE master")
        msgs_after = len(msgs)
        delta = msgs_after - msgs_before
        assert delta == 1
        expect = ("msg_handler1: msgstate = 1, severity = 0, procname = ''"
                  ", line = 1, msgtext = 'Changed database context to 'master'.'")
        assert expect == msgs[msgs_after - 1]

    def test_set_handler_to_none(self, conn):
        conn.set_msghandler(None)
        msgs_before = len(msgs)
        conn.execute_non_query("USE master")
        msgs_after = len(msgs)
        delta = msgs_after - msgs_before
        assert delta == 0

    def test_change_handler(self, conn):
        conn.set_msghandler(user_msg_handler1)
        msgs_before = len(msgs)
        conn.execute_non_query("USE master")
        msgs_after = len(msgs)
        delta = msgs_after - msgs_before
        assert delta == 1
        expect = ("msg_handler1: msgstate = 1, severity = 0, procname = ''"
                  ", line = 1, msgtext = 'Changed database context to 'master'.'")
        assert expect == msgs[msgs_after - 1]

        conn.set_msghandler(user_msg_handler2)
        msgs_before = len(msgs)
        conn.execute_non_query("USE %s" % config.database)
        msgs_after = len(msgs)
        delta = msgs_after - msgs_before
        assert delta == 1
        expect = ("msg_handler2: msgstate = 1, severity = 0, procname = ''"
                  ", line = 1, msgtext = 'Changed database context to '%s'.'") % config.database
        assert expect == msgs[msgs_after - 1]

    def test_per_conn_handlers(self, mssql_conn):
        cnx1 = mssql_conn
        cnx2 = mssql_conn
        cnx1.set_msghandler(user_msg_handler1)
        msgs_before = len(msgs)
        cnx1.execute_non_query("USE master")
        msgs_after = len(msgs)
        delta = msgs_after - msgs_before
        assert delta == 1
        expect = ("msg_handler1: msgstate = 1, severity = 0, procname = ''"
                  ", line = 1, msgtext = 'Changed database context to 'master'.'")
        assert expect == msgs[msgs_after - 1]

        cnx2.set_msghandler(user_msg_handler2)
        msgs_before = len(msgs)
        cnx2.execute_non_query("USE %s" % config.database)
        msgs_after = len(msgs)
        delta = msgs_after - msgs_before
        assert delta == 1
        expect = ("msg_handler2: msgstate = 1, severity = 0, procname = ''"
                  ", line = 1, msgtext = 'Changed database context to '%s'.'") % config.database
        assert expect == msgs[msgs_after - 1]

    @staticmethod
    def user_msg_handler3(msgstate, severity, srvname, procname, line, msgtext):
        global msgs
        procname = procname.decode('ascii')
        msgtext = msgtext.decode('ascii')
        entry = ("msg_handler3 called")
        msgs.append(entry)

    def test_static_method_handler(self, conn):
        conn.set_msghandler(self.user_msg_handler3)
        msgs_before = len(msgs)
        conn.execute_non_query("USE master")
        msgs_after = len(msgs)
        delta = msgs_after - msgs_before
        assert delta == 1
        expect = ("msg_handler3 called")
        assert expect == msgs[msgs_after - 1]

    def test_wrong_signature_handler(self, conn):
        conn.set_msghandler(wrong_signature_msg_handler)
        conn.execute_non_query("USE master")
