import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from src.ledger import bootstrap_database, LedgerEngine

@pytest.fixture
def db_engine(tmp_path):
    """
    Create a SQLAlchemy engine fixture that spins up an isolated,
    temporary SQLite database for testing threading and locks.
    """
    db_file = tmp_path / "test.db"
    database_url = f"sqlite:///{db_file}"
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
    )

    # Enable WAL mode and foreign keys for SQLite
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()

    yield engine
    engine.dispose()

@pytest.fixture
def session_factory(db_engine):
    """Return a configured session factory."""
    return sessionmaker(bind=db_engine)

@pytest.fixture
def seeded_db(db_engine, session_factory):
    """
    Yields a database pre-seeded with User 1 ($100), User 2 (€0),
    and the FX Clearing accounts.
    Returns a dictionary of account IDs, the LedgerEngine instance,
    and the session_factory for direct DB assertions.
    """
    # bootstrap_database drops and creates all tables, then seeds data
    account_ids = bootstrap_database(db_engine, session_factory)
    ledger = LedgerEngine(session_factory)
    
    yield {
        "engine": db_engine,
        "session_factory": session_factory,
        "account_ids": account_ids,
        "ledger": ledger
    }
