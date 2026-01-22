"""Databricks SQL connection with Service Principal authentication for Databricks Apps.

Phase 1 Performance Optimization:
- Thread-local connections for parallel query execution
- Config object is cached and shared (thread-safe)
- Each thread gets its own connection for parallel queries
"""
import os
import time
import threading
from contextlib import contextmanager
from typing import Generator, Any, Optional

import pandas as pd
from databricks import sql as dbsql
from databricks.sdk.core import Config

from core.config import get_settings


class DatabricksDB:
    """Database connection manager with thread-local connections for parallel queries."""

    def __init__(self):
        self.settings = get_settings()
        self._config = None
        self._config_lock = threading.Lock()
        self._thread_local = threading.local()
        self._log_auth_info()

    def _log_auth_info(self):
        """Log authentication configuration."""
        print("=== Database Configuration ===")
        print(f"HTTP Path: {self.settings.databricks_http_path}")
        print(f"Catalog: {self.settings.databricks_catalog}")
        print(f"Parallel queries: ENABLED (thread-local connections)")
        print(f"DATABRICKS_CLIENT_ID present: {bool(os.environ.get('DATABRICKS_CLIENT_ID'))}")
        print(f"DATABRICKS_CLIENT_SECRET present: {bool(os.environ.get('DATABRICKS_CLIENT_SECRET'))}")

    def _get_config(self) -> Config:
        """Get or create Config for OAuth authentication (thread-safe)."""
        if self._config is None:
            with self._config_lock:
                if self._config is None:
                    # Config auto-detects credentials from environment in Databricks Apps
                    self._config = Config()
                    print(f"SDK Config initialized:")
                    print(f"  Host: {self._config.host}")
                    print(f"  Auth type: {self._config.auth_type}")
        return self._config

    def _create_connection(self) -> Any:
        """Create a new database connection."""
        cfg = self._get_config()
        connection = dbsql.connect(
            server_hostname=cfg.host,
            http_path=self.settings.databricks_http_path,
            credentials_provider=lambda: cfg.authenticate,
            _use_arrow_native_complex_types=False
        )
        return connection

    def _get_thread_connection(self) -> Any:
        """Get or create a connection for the current thread."""
        if not hasattr(self._thread_local, 'connection') or self._thread_local.connection is None:
            self._thread_local.connection = self._create_connection()
            thread_id = threading.current_thread().name
            print(f"SQL connection established (thread: {thread_id})")
        return self._thread_local.connection

    def _close_thread_connection(self):
        """Close the connection for the current thread."""
        if hasattr(self._thread_local, 'connection') and self._thread_local.connection is not None:
            try:
                self._thread_local.connection.close()
                thread_id = threading.current_thread().name
                print(f"SQL connection closed (thread: {thread_id})")
            except Exception:
                pass
            self._thread_local.connection = None

    @contextmanager
    def get_connection(self) -> Generator[Any, None, None]:
        """
        Get a Databricks SQL connection using Service Principal OAuth.
        Uses thread-local connections for parallel query support.

        In Databricks Apps, Config() automatically uses the injected
        DATABRICKS_CLIENT_ID and DATABRICKS_CLIENT_SECRET.
        """
        connection = None
        try:
            connection = self._get_thread_connection()
            yield connection
        except Exception as e:
            print(f"Connection error: {type(e).__name__}: {str(e)}")
            # Invalidate thread connection on error
            self._close_thread_connection()
            import traceback
            traceback.print_exc()
            raise

    def execute_query(self, sql_query: str) -> pd.DataFrame:
        """
        Execute a SQL query and return results as a DataFrame.

        Args:
            sql_query: SQL query to execute

        Returns:
            pandas DataFrame with query results
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql_query)
                    columns = [desc[0] for desc in cursor.description]
                    data = cursor.fetchall()
                    df = pd.DataFrame(data, columns=columns)

                    # Convert numeric columns where possible
                    for col in df.columns:
                        try:
                            converted = pd.to_numeric(df[col])
                            df[col] = converted
                        except (ValueError, TypeError):
                            # Column cannot be converted to numeric, keep original
                            pass

                    return df
        except Exception as e:
            print(f"ERROR executing query: {str(e)}")
            print(f"Query: {sql_query[:200]}...")
            return pd.DataFrame()


# Singleton instance
_db_instance = None


def get_db() -> DatabricksDB:
    """Get singleton database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabricksDB()
    return _db_instance
