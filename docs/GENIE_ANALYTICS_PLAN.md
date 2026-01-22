# Genie Space Analytics Plan

A plan for analytics-ready gold layer tables optimized for natural language queries via Databricks Genie, enabling non-technical users to explore expansion opportunities and partnership strategies.

---

## Current State: Visualization Tables

The existing `viz_*` tables are optimized for **app rendering**, not natural language analytics:

| Table | Purpose | Genie Limitation |
|-------|---------|------------------|
| `viz_expansion_candidates` | Map markers + filtering | Too many columns, technical H3 IDs, no friendly names |
| `viz_existing_stores` | Store markers | Missing business context (performance tiers, tenure) |
| `viz_partners` | Partner isochrones | Array columns, GeoJSON not queryable |
| `viz_competitors` | Competitor markers | No competitive analysis metrics |
| `viz_optimization_results` | Pre-computed optimization | Array of H3 cells, not human-readable |
| `viz_network_metrics` | Singleton KPIs | Single row, no time series or comparisons |

---

## Proposed: Genie-Optimized Analytics Tables

### Design Principles

1. **Denormalized for simplicity** - One table per business concept, no joins required
2. **Human-readable values** - City names, tier labels, strategy descriptions (no H3 IDs in answers)
3. **Pre-computed metrics** - Ratios, ranks, and percentiles ready for comparison
4. **Consistent naming** - Snake_case, business terminology, clear units in column names
5. **Rich descriptions** - Column comments for Genie context understanding

---

## Table Specifications

### 1. `genie_expansion_opportunities`

**Purpose:** Primary table for exploring where to open new stores

```sql
CREATE TABLE genie_expansion_opportunities (
  -- Identity
  opportunity_id STRING COMMENT 'Unique identifier for the expansion opportunity',
  opportunity_name STRING COMMENT 'Human-readable name like "Boston - Back Bay" or "Springfield - Downtown"',

  -- Location
  city STRING COMMENT 'City or town name',
  region STRING COMMENT 'Region grouping: Boston Metro, Greater Boston, Western MA, Cape & Islands',
  county STRING COMMENT 'County name',
  latitude DOUBLE,
  longitude DOUBLE,

  -- Predicted Performance
  predicted_annual_sales DOUBLE COMMENT 'ML-predicted annual sales in USD',
  predicted_monthly_sales DOUBLE COMMENT 'ML-predicted monthly sales in USD',
  sales_confidence_lower DOUBLE COMMENT 'Lower bound of 80% prediction interval',
  sales_confidence_upper DOUBLE COMMENT 'Upper bound of 80% prediction interval',
  sales_rank INT COMMENT 'Rank by predicted sales (1 = highest)',
  sales_percentile DOUBLE COMMENT 'Percentile rank (0.95 = top 5%)',
  sales_tier STRING COMMENT 'Performance tier: Premium, Strong, Moderate, Developing',

  -- Demographics
  trade_area_population INT COMMENT 'Population within 5-minute drive time',
  target_demographic_count INT COMMENT 'Target demographic (families with children) count',
  target_demographic_pct DOUBLE COMMENT 'Percent of population in target demographic',
  median_household_income DOUBLE COMMENT 'Median household income in trade area',
  population_density_rank STRING COMMENT 'Density tier: Very High, High, Medium, Low',

  -- Competitive Landscape
  competitor_count INT COMMENT 'Number of pizza competitors within 5-min drive',
  nearest_competitor_miles DOUBLE COMMENT 'Distance to nearest pizza competitor in miles',
  competitor_density STRING COMMENT 'Competition level: Saturated, Competitive, Moderate, Low',

  -- Network Context
  nearest_lce_store_miles DOUBLE COMMENT 'Distance to nearest existing Little Caesars in miles',
  nearest_lce_store_id STRING COMMENT 'Store number of nearest existing location',
  cannibalization_risk STRING COMMENT 'Risk of cannibalizing existing store: High, Medium, Low, None',

  -- Fulfillment Strategy
  fulfillment_strategy STRING COMMENT 'Recommended approach: Partner or New Store',
  partner_store_name STRING COMMENT 'If Partner strategy, name of partner store (e.g., Walmart, 7-Eleven)',
  partner_store_type STRING COMMENT 'Partner category: Big Box, Convenience, Grocery',
  partner_drive_time_mins DOUBLE COMMENT 'Drive time to partner location in minutes',

  -- Investment Context
  estimated_build_cost STRING COMMENT 'Build cost tier: High ($500K+), Medium ($300-500K), Standard ($150-300K)',
  roi_estimate STRING COMMENT 'Estimated ROI tier: Excellent (>30%), Good (20-30%), Moderate (10-20%)',

  -- Quality Flags
  quality_score DOUBLE COMMENT 'Composite quality score (0-100)',
  quality_tier STRING COMMENT 'Overall quality: Top 25%, Top 50%, Top 75%, Bottom 25%',
  recommended BOOLEAN COMMENT 'True if meets all investment criteria',

  -- Metadata
  last_updated TIMESTAMP
)
COMMENT 'Expansion opportunities ranked by predicted sales with demographics, competition, and strategy recommendations. Use this table to find the best locations for new Little Caesars stores.';
```

**Sample Questions This Enables:**
- "What are the top 10 expansion opportunities in Boston Metro?"
- "Show me partner opportunities with predicted sales over $500K"
- "Which locations have low competition and high population?"
- "Compare opportunities in Western MA vs Cape & Islands"

---

### 2. `genie_partnership_analysis`

**Purpose:** Evaluate partnership opportunities with convenience stores, big box retailers, etc.

```sql
CREATE TABLE genie_partnership_analysis (
  -- Partner Identity
  partner_id STRING,
  partner_name STRING COMMENT 'Store name like "Walmart #1234" or "7-Eleven Boston"',
  partner_brand STRING COMMENT 'Brand: Walmart, Target, 7-Eleven, Cumberland Farms, etc.',
  partner_type STRING COMMENT 'Category: Big Box, Convenience, Grocery, Gas Station',

  -- Location
  city STRING,
  region STRING,
  address STRING,
  latitude DOUBLE,
  longitude DOUBLE,

  -- Partnership Potential
  candidates_in_trade_area INT COMMENT 'Number of expansion candidates within partner trade area',
  total_addressable_sales DOUBLE COMMENT 'Sum of predicted sales for all candidates in trade area',
  avg_candidate_sales DOUBLE COMMENT 'Average predicted sales per candidate in trade area',
  partnership_score DOUBLE COMMENT 'Composite partnership attractiveness score (0-100)',
  partnership_tier STRING COMMENT 'Priority tier: High Priority, Medium Priority, Low Priority',

  -- Trade Area Demographics
  trade_area_population INT,
  target_demographic_pct DOUBLE,
  median_household_income DOUBLE,

  -- Competitive Context
  pizza_competitors_nearby INT COMMENT 'Pizza competitors within partner trade area',
  nearest_lce_miles DOUBLE COMMENT 'Distance to nearest existing Little Caesars',

  -- Operational Fit
  store_hours STRING COMMENT 'Partner typical hours: 24/7, Extended, Standard',
  foot_traffic_estimate STRING COMMENT 'Estimated daily foot traffic: Very High, High, Medium, Low',
  parking_availability STRING COMMENT 'Parking: Abundant, Adequate, Limited',

  -- Metadata
  last_updated TIMESTAMP
)
COMMENT 'Partner store analysis for co-location opportunities. Use this to identify which Walmart, 7-Eleven, or other partners offer the best expansion potential.';
```

**Sample Questions This Enables:**
- "Which Walmart locations have the highest partnership potential?"
- "Show me convenience store partners in Boston with over $400K addressable sales"
- "Compare 7-Eleven vs Cumberland Farms partnership opportunities"
- "What are the top 5 partner opportunities by total addressable sales?"

---

### 3. `genie_store_performance`

**Purpose:** Analyze existing store performance for benchmarking and insights

```sql
CREATE TABLE genie_store_performance (
  -- Store Identity
  store_number STRING,
  store_name STRING COMMENT 'Friendly name like "Little Caesars - Cambridge"',
  store_type STRING COMMENT 'Format: Traditional, Express, Partner',

  -- Location
  city STRING,
  region STRING,
  state STRING,
  address STRING,
  latitude DOUBLE,
  longitude DOUBLE,

  -- Performance Metrics
  annual_sales DOUBLE COMMENT 'Actual annual sales in USD',
  monthly_avg_sales DOUBLE COMMENT 'Average monthly sales',
  sales_rank INT COMMENT 'Rank among all stores (1 = highest)',
  sales_percentile DOUBLE,
  performance_tier STRING COMMENT 'Tier: Top Performer, Above Average, Average, Below Average',

  -- Year-over-Year (if available)
  sales_yoy_change_pct DOUBLE COMMENT 'Year-over-year sales change percentage',
  sales_trend STRING COMMENT 'Trend: Growing, Stable, Declining',

  -- Trade Area Characteristics
  trade_area_population INT,
  target_demographic_count INT,
  poi_count INT COMMENT 'Points of interest within trade area',
  competitor_count INT,

  -- Efficiency Metrics
  sales_per_capita DOUBLE COMMENT 'Sales divided by trade area population',
  sales_per_competitor DOUBLE COMMENT 'Sales divided by (1 + competitor count)',
  market_penetration_score DOUBLE COMMENT 'Estimated market share in trade area',

  -- Network Context
  nearest_lce_miles DOUBLE COMMENT 'Distance to nearest other Little Caesars',
  trade_area_overlap_pct DOUBLE COMMENT 'Percent of trade area overlapping with other LCE stores',

  -- Metadata
  store_open_date DATE,
  years_in_operation DOUBLE,
  last_updated TIMESTAMP
)
COMMENT 'Existing Little Caesars store performance metrics. Use this to benchmark stores, identify top performers, and understand what drives success.';
```

**Sample Questions This Enables:**
- "What are our top 5 performing stores in Massachusetts?"
- "Which stores have declining sales?"
- "Show stores with sales per capita above average"
- "Compare Boston Metro stores vs Western MA stores"

---

### 4. `genie_competitive_landscape`

**Purpose:** Understand the competitive environment by area

```sql
CREATE TABLE genie_competitive_landscape (
  -- Area Identity
  area_id STRING,
  area_name STRING COMMENT 'Geographic area name',
  area_type STRING COMMENT 'Type: City, Town, Neighborhood, Region',
  region STRING,
  county STRING,

  -- Little Caesars Presence
  lce_store_count INT COMMENT 'Number of Little Caesars stores in area',
  lce_total_sales DOUBLE COMMENT 'Combined LCE sales in area',
  lce_market_share_estimate DOUBLE COMMENT 'Estimated LCE market share (0-1)',

  -- Competition
  dominos_count INT,
  pizza_hut_count INT,
  papa_johns_count INT,
  local_pizza_count INT COMMENT 'Independent/local pizza shops',
  total_pizza_competitors INT,

  -- Market Metrics
  total_population INT,
  estimated_pizza_market_size DOUBLE COMMENT 'Estimated annual pizza spending in area',
  pizza_spend_per_capita DOUBLE,

  -- Opportunity Assessment
  market_saturation STRING COMMENT 'Saturation level: Oversaturated, Saturated, Balanced, Underserved',
  expansion_potential STRING COMMENT 'Potential: High, Medium, Low',
  recommended_strategy STRING COMMENT 'Strategy: Aggressive Expansion, Selective Growth, Defend Position, Avoid',

  -- Metadata
  last_updated TIMESTAMP
)
COMMENT 'Competitive landscape analysis by geographic area. Use this to understand market saturation and identify underserved areas.';
```

**Sample Questions This Enables:**
- "Which areas are underserved by pizza restaurants?"
- "Where does Domino's have the strongest presence?"
- "Show me areas where we have low market share but high population"
- "What's our market share in Boston Metro?"

---

### 5. `genie_market_summary`

**Purpose:** High-level market metrics and trends for executive dashboards

```sql
CREATE TABLE genie_market_summary (
  -- Time Period
  report_date DATE COMMENT 'Date of this summary',
  report_period STRING COMMENT 'Period: Current, Last Month, Last Quarter, Last Year',

  -- Network Overview
  total_stores INT,
  total_annual_sales DOUBLE,
  avg_store_sales DOUBLE,
  median_store_sales DOUBLE,

  -- Expansion Pipeline
  total_expansion_candidates INT,
  high_priority_candidates INT COMMENT 'Candidates in top 25% by predicted sales',
  partner_opportunities INT,
  new_store_opportunities INT,
  total_pipeline_value DOUBLE COMMENT 'Sum of predicted sales for all candidates',

  -- Market Position
  estimated_market_share DOUBLE,
  primary_competitor STRING COMMENT 'Largest competitor by store count',
  competitive_gap INT COMMENT 'Store count difference vs primary competitor',

  -- Performance Trends
  network_sales_trend STRING COMMENT 'Trend: Growing, Stable, Declining',
  top_performing_region STRING,
  underperforming_region STRING,

  -- Metadata
  last_updated TIMESTAMP
)
COMMENT 'Executive summary of market position, network performance, and expansion pipeline. Use for high-level questions about overall business health.';
```

**Sample Questions This Enables:**
- "How many stores do we have and what's our total sales?"
- "What's in our expansion pipeline?"
- "Which region is performing best?"
- "How do we compare to competitors?"

---

## Sample Business Questions by Persona

### Real Estate / Site Selection Analyst

| Question | Table | Complexity |
|----------|-------|------------|
| "What are the top 10 expansion opportunities by predicted sales?" | `genie_expansion_opportunities` | Simple |
| "Show me opportunities in Boston with low competition" | `genie_expansion_opportunities` | Filter |
| "Which partner locations have the highest total addressable sales?" | `genie_partnership_analysis` | Simple |
| "Compare new store vs partner opportunities in Greater Boston" | `genie_expansion_opportunities` | Group By |
| "Find locations within 2 miles of a Walmart with predicted sales over $400K" | `genie_expansion_opportunities` | Complex Filter |
| "What's the average predicted sales for top-tier opportunities by region?" | `genie_expansion_opportunities` | Aggregate |
| "Show opportunities where we'd be the only pizza option within 3 miles" | `genie_expansion_opportunities` | Filter |

### Operations / Regional Manager

| Question | Table | Complexity |
|----------|-------|------------|
| "Which of my stores are underperforming?" | `genie_store_performance` | Filter |
| "Show stores ranked by sales per capita" | `genie_store_performance` | Sort |
| "Compare my region's performance to the network average" | `genie_store_performance` | Aggregate |
| "Which stores have declining sales trends?" | `genie_store_performance` | Filter |
| "What's the total sales for Boston Metro stores?" | `genie_store_performance` | Aggregate |

### Strategy / Executive

| Question | Table | Complexity |
|----------|-------|------------|
| "How big is our expansion pipeline?" | `genie_market_summary` | Simple |
| "Where should we focus expansion efforts?" | `genie_expansion_opportunities` | Aggregate |
| "What's our market share compared to Domino's?" | `genie_competitive_landscape` | Simple |
| "Which markets are underserved?" | `genie_competitive_landscape` | Filter |
| "What's the total potential revenue from partner opportunities?" | `genie_partnership_analysis` | Aggregate |

### Partnership / Business Development

| Question | Table | Complexity |
|----------|-------|------------|
| "Which convenience store chains offer the best partnership potential?" | `genie_partnership_analysis` | Group By |
| "Show me all Walmart partnership opportunities ranked by potential sales" | `genie_partnership_analysis` | Filter + Sort |
| "Compare 7-Eleven vs Cumberland Farms as partners" | `genie_partnership_analysis` | Group By |
| "What's the total addressable market through partnerships?" | `genie_partnership_analysis` | Aggregate |

---

## Implementation Approach

### Phase 1: Core Tables (Week 1)
1. Create `genie_expansion_opportunities` from `viz_expansion_candidates`
   - Add human-readable names via reverse geocoding or city/region lookup
   - Pre-compute tiers, ranks, and formatted metrics
   - Add column comments for Genie context

2. Create `genie_store_performance` from `viz_existing_stores`
   - Add performance tiers and benchmarks
   - Calculate efficiency metrics

### Phase 2: Partnership & Competition (Week 2)
3. Create `genie_partnership_analysis` from `viz_partners`
   - Flatten array columns
   - Add partnership scoring

4. Create `genie_competitive_landscape` from `viz_competitors`
   - Aggregate by geographic area
   - Add market sizing estimates

### Phase 3: Summary & Refinement (Week 3)
5. Create `genie_market_summary` as aggregate view
6. Add Genie Space with table descriptions and sample questions
7. Test with target personas and refine based on feedback

---

## Genie Space Configuration

### Recommended Instructions for Genie

```
You are a retail analytics assistant for Little Caesars Pizza. Help users explore expansion opportunities, analyze store performance, and understand the competitive landscape in Massachusetts.

Key concepts:
- "Opportunities" or "candidates" refer to potential new store locations
- "Partners" are existing retail stores (Walmart, 7-Eleven, etc.) where we could co-locate
- "Trade area" is the 5-minute drive time zone around a location
- "Predicted sales" are ML model predictions, not guarantees
- Sales figures are annual unless specified otherwise

When comparing locations, consider:
1. Predicted sales (higher is better)
2. Competition (fewer competitors is better)
3. Distance from existing stores (farther reduces cannibalization)
4. Partnership opportunities (existing retail reduces build costs)

Default to showing top 10 results unless the user asks for more.
```

### Sample Questions to Seed

Add these to the Genie Space for users to see as examples:
- "What are the top 10 expansion opportunities?"
- "Show me partner opportunities with sales over $500K"
- "Which stores are underperforming?"
- "Where is competition lowest?"
- "Compare Boston vs Western MA opportunities"

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Question success rate | >85% of queries return useful answers |
| Avg questions per session | >5 (indicates engagement) |
| Time to insight | <30 seconds for simple questions |
| User satisfaction (survey) | >4.0/5.0 |
| Reduction in ad-hoc SQL requests | >50% |

---

## Appendix: Column Naming Conventions

| Pattern | Example | Use For |
|---------|---------|---------|
| `*_count` | `competitor_count` | Integer counts |
| `*_pct` | `target_demographic_pct` | Percentages (0-1 scale) |
| `*_rank` | `sales_rank` | Integer rankings (1 = best) |
| `*_percentile` | `sales_percentile` | Percentile (0-1 scale) |
| `*_tier` | `quality_tier` | Categorical buckets |
| `*_miles` | `nearest_lce_miles` | Distances |
| `*_mins` | `drive_time_mins` | Time durations |
| `predicted_*` | `predicted_annual_sales` | ML predictions |
| `estimated_*` | `estimated_market_size` | Approximations |
