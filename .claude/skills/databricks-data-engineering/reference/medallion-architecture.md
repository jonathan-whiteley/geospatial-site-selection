# Medallion Architecture - Bronze-Silver-Gold

Three-layer design for progressive data quality improvement.

## Layer Definitions

**Bronze (Raw Zone)**
- Purpose: Exact copy of source, minimal transformation
- Format: Delta Lake with schema-on-read
- Retention: Long-term (years)
- Example: `dev_catalog.bronze.raw_events`

**Silver (Cleaned Zone)**
- Purpose: Validated, deduplicated, conformed
- Format: Delta Lake with enforced schema
- Retention: Medium-term (months to years)
- Example: `dev_catalog.silver.cleaned_events`

**Gold (Business Zone)**
- Purpose: Business aggregates and feature tables
- Format: Delta Lake optimized for queries
- Retention: Long-term with optimization
- Example: `dev_catalog.gold.customer_360`

## Unity Catalog Structure

```
main (catalog)
  ├── bronze (schema) - raw data
  ├── silver (schema) - cleaned data
  └── gold (schema) - aggregated data
```

## Quality Gates

**Bronze → Silver:**
- Remove nulls in primary keys
- Deduplicate records
- Validate data types
- Apply business rules

**Silver → Gold:**
- Aggregate to business metrics
- Join with dimension tables
- Apply business logic
- Optimize for analytics
```

