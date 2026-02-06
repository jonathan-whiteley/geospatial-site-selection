# Little Caesars Expansion Analytics
## Executive Summary

---

## 1. Data Sources + Model

### Data Pipeline
**Bronze → Silver → Gold** medallion architecture in Unity Catalog

| Layer | Purpose |
|-------|---------|
| Bronze | Raw ingestion: Census API, CARTO Marketplace, Overture Maps POIs |
| Silver | Enrichment: H3 hexagonal grid, drive-time isochrones, feature engineering |
| Gold | ML predictions + visualization tables for app and Genie |

> **[VISUAL]** Architecture diagram showing data flow from sources through medallion layers

### ML Model
- **Algorithm**: XGBoost regression trained on existing store performance
- **Target**: Predicted annual sales per expansion candidate
- **Features**: 130+ variables (demographics, income, competition density, POI counts, accessibility)
- **Output**: Ranked expansion candidates with fulfillment strategy recommendations

> **[VISUAL]** Feature importance chart from model (top 10 predictors)

---

## 2. App Features and Stack

### Interactive Dashboard
| Feature | Description |
|---------|-------------|
| Map View | Dark-themed Mapbox with stores, candidates, partners, competitors |
| Filtering | By fulfillment strategy, sales range, region, competition level |
| Expansion Agent | Natural language chat powered by Databricks Genie |
| KPI Summary | Network-wide metrics and performance tiers |

> **[VISUAL]** Screenshot of app with map and chat panel visible

### Fulfillment Strategies
- **New Store**: Greenfield sites in whitespace markets (higher investment, full control)
- **Partner**: Co-location with Walmart, 7-Eleven, Shaw's (lower investment, shared traffic)

### Technology Stack
| Component | Technology |
|-----------|------------|
| Platform | Databricks (Unity Catalog, Serverless SQL, Model Serving) |
| Spatial | H3 hexagonal grid, Valhalla routing engine |
| Frontend | React + Mapbox GL JS |
| AI/Analytics | Genie Space + Multi-Agent serving |

---

## 3. Considerations for Production

### Data & Model
- **Refresh cadence**: Census data annual; POI/competitor data quarterly
- **Model retraining**: Trigger on new store openings or significant performance drift
- **Ground truth**: Integrate actual sales data for model validation

### Infrastructure
- **Compute**: Move from interactive clusters to scheduled Workflows jobs
- **Serving**: Production Model Serving endpoint with autoscaling
- **Monitoring**: Add MLflow model monitoring for prediction drift

### Governance & Security
- **Access control**: Row-level security on sensitive sales data
- **Data lineage**: Unity Catalog lineage for audit trail
- **PII handling**: Census data aggregated at block group level (no individual PII)

### App Deployment
- **Environment promotion**: Dev → Staging → Prod via Asset Bundles
- **Authentication**: Integrate with customer SSO/identity provider
- **Usage tracking**: Add telemetry for feature adoption metrics

> **[VISUAL]** Simple timeline or checklist for production readiness milestones

---

*Generated for Little Caesars Site Selection Project*
