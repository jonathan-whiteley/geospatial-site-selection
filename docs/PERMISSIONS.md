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
| `SELECT` | On gold tables (`viz_current_stores`, `viz_expansion_candidates`, etc.) |
| `EXECUTE` | On ML model (if serving predictions) |
| `CAN USE` | SQL Warehouse (for query execution) |

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

## Summary

| Component | Access Level | Key Resources |
|-----------|--------------|---------------|
| **Pipeline** | Read/Write | All 3 schemas + serverless compute |
| **App** | Read-only | Gold schema + SQL warehouse |
