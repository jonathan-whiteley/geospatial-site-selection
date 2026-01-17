"""Environment configuration for the Geospatial Retail Site Selection app."""
import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass
class Settings:
    """Application settings loaded from environment variables."""

    # Databricks connection
    databricks_server_hostname: str = ""
    databricks_http_path: str = ""
    databricks_token: str = ""  # For local development only
    databricks_client_id: str = ""  # Service Principal
    databricks_client_secret: str = ""  # Service Principal

    # Catalog and schemas
    databricks_catalog: str = "jdub_demo"
    databricks_gold_schema: str = "geo_gold"
    databricks_silver_schema: str = "geo_silver"
    databricks_bronze_schema: str = "geo_bronze"

    def __post_init__(self):
        """Load values from environment variables."""
        self.databricks_server_hostname = os.getenv(
            "DATABRICKS_SERVER_HOSTNAME",
            "fe-vm-jdub-vm-serverless.cloud.databricks.com"
        )
        self.databricks_http_path = os.getenv(
            "DATABRICKS_HTTP_PATH",
            "/sql/1.0/warehouses/0168e23e24e6ae10"
        )
        self.databricks_token = os.getenv("DATABRICKS_TOKEN", "")
        self.databricks_client_id = os.getenv("DATABRICKS_CLIENT_ID", "")
        self.databricks_client_secret = os.getenv("DATABRICKS_CLIENT_SECRET", "")

        self.databricks_catalog = os.getenv("DATABRICKS_CATALOG", "jdub_demo")
        self.databricks_gold_schema = os.getenv("DATABRICKS_GOLD_SCHEMA", "geo_gold")
        self.databricks_silver_schema = os.getenv("DATABRICKS_SILVER_SCHEMA", "geo_silver")
        self.databricks_bronze_schema = os.getenv("DATABRICKS_BRONZE_SCHEMA", "geo_bronze")

    @property
    def is_service_principal(self) -> bool:
        """Check if running with Service Principal authentication."""
        return bool(self.databricks_client_id and self.databricks_client_secret)

    @property
    def gold_table_prefix(self) -> str:
        """Return fully qualified prefix for gold tables."""
        return f"{self.databricks_catalog}.{self.databricks_gold_schema}"

    @property
    def silver_table_prefix(self) -> str:
        """Return fully qualified prefix for silver tables."""
        return f"{self.databricks_catalog}.{self.databricks_silver_schema}"

    @property
    def bronze_table_prefix(self) -> str:
        """Return fully qualified prefix for bronze tables."""
        return f"{self.databricks_catalog}.{self.databricks_bronze_schema}"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
