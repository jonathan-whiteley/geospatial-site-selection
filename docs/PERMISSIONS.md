# Databricks Permissions Guide

This document outlines the permissions required to deploy and run the Geospatial Retail Site Selection solution.

---

## Pipeline Permissions (ETL Jobs)

**For deploying & running the bronze → silver → gold pipeline:**

| Permission | Target |
|------------|--------|
| `USE CATALOG` | `jdub_demo` |
| `CREATE SCHEMA` | On catalog (or pre-create schemas) |
| `ALL PRIVILEGES` | On `geo_bronze`, `geo_silver`, `geo_gold` schemas |
| `CREATE VOLUME` / `WRITE VOLUME` | On bronze schema |
| `SELECT` | On CARTO Marketplace table |
| Serverless Compute | Entitlement enabled |

### SQL Commands

```sql
-- Pipeline permissions for user
GRANT USE CATALOG ON CATALOG jdub_demo TO `user@example.com`;
GRANT CREATE SCHEMA ON CATALOG jdub_demo TO `user@example.com`;
GRANT ALL PRIVILEGES ON SCHEMA jdub_demo.geo_bronze TO `user@example.com`;
GRANT ALL PRIVILEGES ON SCHEMA jdub_demo.geo_silver TO `user@example.com`;
GRANT ALL PRIVILEGES ON SCHEMA jdub_demo.geo_gold TO `user@example.com`;
```

---

## App Deployment Permissions

### Steps

1. **Create Databricks App** → point at `react-app/` directory
2. **Grant Service Principal** access to required resources

### Service Principal Grants

| Permission | Target |
|------------|--------|
| `USE CATALOG` | `jdub_demo` |
| `USE SCHEMA` | `geo_gold` (app reads from gold layer) |
| `SELECT` | On gold tables (see table list below) |
| `EXECUTE` | On ML model (if serving predictions) |
| `CAN USE` | SQL Warehouse (for query execution) |

### Gold Layer Tables

The app requires `SELECT` access to these tables:

**Visualization Tables (React App):**
- `viz_h3_grid` - H3 hexagon grid for Massachusetts
- `viz_competitors` - Pizza competitor locations
- `viz_existing_stores` - Current LCE stores with isochrones
- `viz_partners` - Partner isochrones with candidate counts
- `viz_expansion_candidates` - Candidates with distances, partner/competitor proximity
- `viz_network_metrics` - Aggregate KPIs
- `viz_optimization_results` - Pre-computed optimization results

**Genie Tables (Natural Language Queries):**
- `genie_existing_stores` - Simplified store data for Genie queries
- `genie_expansion_candidates` - Simplified candidate data for Genie queries

### SQL Commands

```sql
-- App Service Principal permissions
GRANT USE CATALOG ON CATALOG jdub_demo TO `app-service-principal`;
GRANT USE SCHEMA ON SCHEMA jdub_demo.geo_gold TO `app-service-principal`;
GRANT SELECT ON SCHEMA jdub_demo.geo_gold TO `app-service-principal`;

-- If using ML model serving
GRANT EXECUTE ON MODEL jdub_demo.geo_gold.sales_prediction_model TO `app-service-principal`;
```

### SQL Warehouse Access

Grant SQL Warehouse access via the Databricks Admin Console or API:
- Navigate to **SQL Warehouses** → Select warehouse → **Permissions**
- Add the app service principal with **CAN USE** permission

---

## Genie Space Permissions

For the Genie Space to function properly:

| Permission | Target |
|------------|--------|
| `USE CATALOG` | `jdub_demo` |
| `USE SCHEMA` | `geo_gold` |
| `SELECT` | On `genie_existing_stores`, `genie_expansion_candidates` |
| `CAN USE` | SQL Warehouse (Pro or Serverless required) |

### SQL Commands

```sql
-- Genie Space permissions (for users querying via Genie)
GRANT USE CATALOG ON CATALOG jdub_demo TO `genie-users-group`;
GRANT USE SCHEMA ON SCHEMA jdub_demo.geo_gold TO `genie-users-group`;
GRANT SELECT ON TABLE jdub_demo.geo_gold.genie_existing_stores TO `genie-users-group`;
GRANT SELECT ON TABLE jdub_demo.geo_gold.genie_expansion_candidates TO `genie-users-group`;
```

---

## Multi-Agent Endpoint Permissions

For the Multi-Agent chat integration:

| Permission | Target |
|------------|--------|
| Service Principal | Must have `CAN QUERY` on the Model Serving endpoint |
| OAuth Scopes | `all-apis` for token generation |

### Environment Variables Required

```bash
DATABRICKS_HOST=<workspace-url>
DATABRICKS_CLIENT_ID=<service-principal-client-id>
DATABRICKS_CLIENT_SECRET=<service-principal-secret>
DATABRICKS_AGENT_ENDPOINT=<agent-endpoint-name>
```

---

## Summary

| Component | Access Level | Key Resources |
|-----------|--------------|---------------|
| **Pipeline** | Read/Write | All 3 schemas + serverless compute |
| **App** | Read-only | Gold schema (viz_* + genie_* tables) + SQL warehouse |
| **Genie Space** | Read-only | genie_* tables + Pro/Serverless SQL warehouse |
| **Multi-Agent** | Query | Model Serving endpoint + OAuth |
