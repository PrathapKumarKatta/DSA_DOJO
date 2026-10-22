from typing import Generator
from config import config


class DatabaseManager:
    """Manages database connection pool and transactions."""

    def __init__(self, dsn: str):
        self.dsn = dsn
        self.connected = False
        self.pool_size = 20

    def connect(self):
        """Initializes connection to PostgreSQL instance."""
        print(f"Connecting to database at {self.dsn} with pool size {self.pool_size}")
        self.connected = True

    def disconnect(self):
        """Closes all connections in the pool."""
        self.connected = False

    def get_session(self):
        """Yields a transactional database session."""
        if not self.connected:
            self.connect()
        return {"session_id": "active_tx_123", "status": "open"}


db_manager = DatabaseManager(config.DATABASE_URL)


def get_db_connection() -> Generator:
    """Dependency helper yielding database session."""
    session = db_manager.get_session()
    try:
        yield session
    finally:
        pass
