"""Databricks SQL connection with Service Principal authentication support."""
import os
from contextlib import contextmanager
from typing import Generator, Any

import pandas as pd
from databricks import sql as dbsql
from databricks.sdk.config import Config

from core.config import get_settings


class DatabricksDB:
    """Database connection manager supporting both PAT and Service Principal auth."""

    def __init__(self):
        self.settings = get_settings()
        self._connection = None

    def _get_credentials_provider(self):
        """Get credentials provider for Service Principal authentication."""
        config = Config()
        return lambda: config.authenticate()

    @contextmanager
    def get_connection(self) -> Generator[Any, None, None]:
        """
        Get a Databricks SQL connection.

        In Databricks Apps: Uses DATABRICKS_CLIENT_ID/SECRET (Service Principal)
        In development: Uses DATABRICKS_TOKEN (PAT)
        """
        connection = None
        try:
            if self.settings.is_service_principal:
                # Service Principal authentication (Databricks Apps)
                connection = dbsql.connect(
                    server_hostname=self.settings.databricks_server_hostname,
                    http_path=self.settings.databricks_http_path,
                    credentials_provider=self._get_credentials_provider(),
                    _use_arrow_native_complex_types=False
                )
            else:
                # PAT token authentication (local development)
                connection = dbsql.connect(
                    server_hostname=self.settings.databricks_server_hostname,
                    http_path=self.settings.databricks_http_path,
                    access_token=self.settings.databricks_token,
                    _use_arrow_native_complex_types=False
                )
            yield connection
        finally:
            if connection:
                connection.close()

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

                    # Convert numeric columns
                    for col in df.columns:
                        try:
                            df[col] = pd.to_numeric(df[col], errors='ignore')
                        except Exception:
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
