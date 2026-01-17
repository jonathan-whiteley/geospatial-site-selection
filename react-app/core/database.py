"""Databricks SQL connection with Service Principal authentication for Databricks Apps."""
import os
from contextlib import contextmanager
from typing import Generator, Any

import pandas as pd
from databricks import sql as dbsql
from databricks.sdk.core import Config

from core.config import get_settings


class DatabricksDB:
    """Database connection manager using Databricks Apps Service Principal auth."""

    def __init__(self):
        self.settings = get_settings()
        self._config = None
        self._log_auth_info()

    def _log_auth_info(self):
        """Log authentication configuration."""
        print("=== Database Configuration ===")
        print(f"HTTP Path: {self.settings.databricks_http_path}")
        print(f"Catalog: {self.settings.databricks_catalog}")
        print(f"DATABRICKS_CLIENT_ID present: {bool(os.environ.get('DATABRICKS_CLIENT_ID'))}")
        print(f"DATABRICKS_CLIENT_SECRET present: {bool(os.environ.get('DATABRICKS_CLIENT_SECRET'))}")

    def _get_config(self) -> Config:
        """Get or create Config for OAuth authentication."""
        if self._config is None:
            # Config auto-detects credentials from environment in Databricks Apps
            self._config = Config()
            print(f"SDK Config initialized:")
            print(f"  Host: {self._config.host}")
            print(f"  Auth type: {self._config.auth_type}")
        return self._config

    @contextmanager
    def get_connection(self) -> Generator[Any, None, None]:
        """
        Get a Databricks SQL connection using Service Principal OAuth.

        In Databricks Apps, Config() automatically uses the injected
        DATABRICKS_CLIENT_ID and DATABRICKS_CLIENT_SECRET.
        """
        connection = None
        try:
            # Get the SDK config (handles OAuth automatically)
            cfg = self._get_config()

            # Create connection using the SDK's credential provider
            # Note: credentials_provider must be a callable that returns the auth function
            connection = dbsql.connect(
                server_hostname=cfg.host,
                http_path=self.settings.databricks_http_path,
                credentials_provider=lambda: cfg.authenticate,
                _use_arrow_native_complex_types=False
            )
            print("SQL connection established")
            yield connection
        except Exception as e:
            print(f"Connection error: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            if connection:
                try:
                    connection.close()
                    print("SQL connection closed")
                except Exception:
                    pass

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
