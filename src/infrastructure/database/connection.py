"""SQLite database connection management."""

import sqlite3
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite
import structlog

logger = structlog.get_logger()

# SQL for creating tables
_CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    external_id TEXT,
    is_active INTEGER DEFAULT 1,
    is_admin INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_external_id ON users(external_id);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_user_created ON messages(user_id, created_at);

CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    filename TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    file_path TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    uploaded_by TEXT,
    is_indexed INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (uploaded_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_documents_filename ON documents(filename);
CREATE INDEX IF NOT EXISTS idx_documents_created ON documents(created_at);
"""


class Database:
    """Async SQLite database wrapper.

    Provides connection management and query execution for SQLite.
    Uses aiosqlite for async operations.
    """

    def __init__(self, db_path: str | Path) -> None:
        """Initialize the database.

        Args:
            db_path: Path to the SQLite database file.
        """
        self._db_path = Path(db_path)
        self._connection: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        """Connect to the database and create tables if needed."""
        # Ensure parent directory exists
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        self._connection = await aiosqlite.connect(self._db_path)
        self._connection.row_factory = aiosqlite.Row

        # Enable foreign keys
        await self._connection.execute("PRAGMA foreign_keys = ON")

        # Create tables
        await self._connection.executescript(_CREATE_TABLES)
        await self._connection.commit()

        logger.info("database_connected", path=str(self._db_path))

    async def disconnect(self) -> None:
        """Close the database connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None
            logger.info("database_disconnected", path=str(self._db_path))

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[aiosqlite.Connection]:
        """Context manager for database transactions.

        Yields:
            The database connection for executing queries.

        Raises:
            RuntimeError: If database is not connected.
        """
        if not self._connection:
            raise RuntimeError("Database not connected")

        try:
            yield self._connection
            await self._connection.commit()
        except Exception:
            await self._connection.rollback()
            raise

    async def execute(
        self,
        sql: str,
        parameters: tuple[object, ...] | dict[str, object] | None = None,
    ) -> aiosqlite.Cursor:
        """Execute a SQL statement.

        Args:
            sql: SQL statement to execute.
            parameters: Optional parameters for the statement.

        Returns:
            Cursor with execution results.

        Raises:
            RuntimeError: If database is not connected.
        """
        if not self._connection:
            raise RuntimeError("Database not connected")

        if parameters:
            cursor = await self._connection.execute(sql, parameters)
        else:
            cursor = await self._connection.execute(sql)

        await self._connection.commit()
        return cursor

    async def fetch_one(
        self,
        sql: str,
        parameters: tuple[object, ...] | dict[str, object] | None = None,
    ) -> sqlite3.Row | None:
        """Fetch a single row.

        Args:
            sql: SQL query to execute.
            parameters: Optional parameters for the query.

        Returns:
            The first row or None.
        """
        cursor = await self.execute(sql, parameters)
        return await cursor.fetchone()

    async def fetch_all(
        self,
        sql: str,
        parameters: tuple[object, ...] | dict[str, object] | None = None,
    ) -> list[sqlite3.Row]:
        """Fetch all rows.

        Args:
            sql: SQL query to execute.
            parameters: Optional parameters for the query.

        Returns:
            List of rows.
        """
        cursor = await self.execute(sql, parameters)
        return list(await cursor.fetchall())


# Global database instance
_database: Database | None = None


def get_database() -> Database:
    """Get the global database instance.

    Returns:
        The database instance.

    Raises:
        RuntimeError: If database not initialized.
    """
    if _database is None:
        raise RuntimeError("Database not initialized. Call init_database first.")
    return _database


async def init_database(db_path: str | Path) -> Database:
    """Initialize and connect to the database.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        Connected database instance.
    """
    global _database
    _database = Database(db_path)
    await _database.connect()
    return _database
