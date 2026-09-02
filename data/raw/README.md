# Raw Data Directory (`data/raw`)

This directory is designated for raw source data references.

> [!IMPORTANT]
> **Data Scope & Design Decision Notice:**
> - **Sole Freight Data Source**: This project uses the Breakwave Dry Bulk Shipping ETF (**BDRY**, 2018–present) as its sole freight-rate proxy data source.
> - **Pre-2018 BDI Scoped Out**: Pre-2018 historical Baltic Dry Index (BDI) data is intentionally out of scope for this prototype.
> - **Documented Architecture Decision**: This is a deliberate, documented design decision to rely strictly on verifiable, publicly accessible financial market data rather than synthetic or paywalled historical series — not a missing feature or an unresolved gap.

---

## Directory Policies
- All raw datasets placed here are excluded from version control via `.gitignore`.
- No fabricated, synthetic, or invented datasets should ever be placed or committed in this repository.
