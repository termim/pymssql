# -*- coding: utf-8 -*-
"""
Basic SQLAlchemy tests.
"""

import unittest

import pytest

from .helpers import eq_

try:
    import sqlalchemy as sa
except ImportError:
    pytest.skip('SQLAlchemy is not available', allow_module_level=True)
from sqlalchemy.orm import sessionmaker, declarative_base


@pytest.fixture(scope="module")
def sa_engine(test_cfg):
    """Create SQLAlchemy engine."""
    return sa.create_engine(
        'mssql+pymssql://%s:%s@%s:%s/%s' % (
            test_cfg.user,
            test_cfg.password,
            test_cfg.server,
            test_cfg.port,
            test_cfg.database
        ),
        echo=False
    )


meta = sa.MetaData()
Base = declarative_base(metadata=meta)


@pytest.fixture(scope="class")
def sa_session(sa_engine):
    """Create SQLAlchemy session."""
    Session = sessionmaker(bind=sa_engine)
    return Session()


class SAObj(Base):
    __tablename__ = 'sa_test_objs'
    __allow_unmapped__ = True
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(50))
    data = sa.Column(sa.PickleType)


@pytest.mark.mssql_server_required
class TestSA:

    def test_basic_usage(self, sa_engine, sa_session):
        saotbl = SAObj.__table__
        saotbl.drop(sa_engine, checkfirst=True)
        saotbl.create(sa_engine)

        s = SAObj(name='foobar')
        sa_session.add(s)
        sa_session.commit()
        assert s.id
        assert sa_session.query(SAObj).count() == 1

    def test_pickle_type(self, sa_engine, sa_session):
        saotbl = SAObj.__table__
        saotbl.drop(sa_engine, checkfirst=True)
        saotbl.create(sa_engine)

        s = SAObj(name='foobar', data=['one'])
        sa_session.add(s)
        sa_session.commit()
        res = sa_session.execute(sa.select(saotbl.c.data))
        row = res.fetchone()
        eq_(row[0], ['one'])
