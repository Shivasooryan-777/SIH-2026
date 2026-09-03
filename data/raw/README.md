# Raw Data Directory (`data/raw`)

This directory is designated for raw source data references.

> [!IMPORTANT]
> **Data Scope & Design Decision Notice:**
> - **Sole Freight Data Source**: This project uses the Breakwave Dry Bulk Shipping ETF (**BDRY**, 2018–present) as its sole freight-rate proxy data source.
> - **Pre-2018 BDI Scoped Out**: Pre-2018 historical Baltic Dry Index (BDI) data is intentionally out of scope for this prototype.
> - **Documented Architecture Decision**: This is a deliberate, documented design decision to rely strictly on verifiable, publicly accessible financial market data rather than synthetic or paywalled historical series — not a missing feature or an unresolved gap.
> - **Commodity Proxy Disclosure (Coal & Iron Ore)**: `VALE` (Vale S.A.) and `BTU` (Peabody Energy) are company equity prices used as commodity-price proxies because yfinance has no continuous coal/iron-ore futures ticker available. Unlike BDRY (a freight-tracking fund) or Brent crude (a direct commodity future), equity prices carry company-specific noise in addition to commodity signal. This is a disclosed limitation, not implied equivalence to a real futures price.
> - **General Dry-Bulk Series Scope (No Fabricated Multipliers)**: Freight rate records in `FreightRateData` and `ForecastResults` have `vessel_type_id = NULL`, representing a single, verifiable, general dry-bulk market series. Distinct per-vessel class day rates (BCI, BPI, BSI, BHSI) require proprietary Baltic Exchange feeds and are explicitly scoped out. Artificial scalar multipliers ($22k/$15k/$12.5k/$9.5k) are strictly prohibited per project credibility rules.

---

## Directory Policies
- All raw datasets placed here are excluded from version control via `.gitignore`.
- No fabricated, synthetic, or invented datasets should ever be placed or committed in this repository.

