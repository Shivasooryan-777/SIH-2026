# Intelligent Freight Forecasting & Vessel Chartering Decision Support System — Technical Project Blueprint

SIH 2026 | Problem Statement ID: SIH26006 | Ministry of Steel

> [!WARNING]
> **AMENDMENT — Data Scope Decision (added post-Session 2, not in the original blueprint text below)**
>
> This blueprint's original text (Module A inputs, Data Architecture Stage 1, and
> Challenge 1) specifies freight rate data as "BDRY proxy + spliced historical BDI
> series." **This has been deliberately changed for the prototype build:**
>
> - **Actual data source in use: BDRY ETF only, 2018–present. No historical BDI
>   splicing.**
> - **Reason:** Real pre-2018 Baltic Dry Index data is paywalled/not reliably
>   available for free, safe, verifiable sourcing within the build timeline.
>   Rather than fabricate synthetic historical data or have an AI agent
>   autonomously scrape unverified sources (both rejected as unacceptable risks —
>   the former undermines the project's "quantified, backtested" credibility, the
>   latter is a genuine security risk), the decision was made to scope the
>   dataset to real, verifiable BDRY data only.
> - **Impact:** ~8 years of real daily data (2018–present), which is adequate for
>   the tree-based models (XGBoost/LightGBM) and Prophet specified below. No
>   other module is affected.
> - **This should be stated explicitly and proactively in the final report/demo**
>   as a disclosed scope decision — consistent with this document's own
>   Challenge 1 and Challenge 9 principles of never implying access to data the
>   team doesn't actually have.
> - **Open item:** if the six-person team wants pre-2018 coverage restored later,
>   that requires someone to personally source and vet a real BDI dataset — not
>   an automated or synthetic shortcut. Not attempted in the current build.
>
> Everywhere below that says "spliced historical BDI," read it as superseded by
> this amendment unless/until real BDI data is sourced and this note is removed.

> [!WARNING]
> **AMENDMENT — General Dry-Bulk Forecast Scope (added Session 5 Correction)**
>
> Module A produces a single general dry-bulk freight market forecast
> (stored with `vessel_type_id = NULL` in `FreightRateData` and `ForecastResults`).
>
> - **Out of scope for prototype:** Distinct per-vessel-class time-series
>   dynamics (e.g., independent Capesize vs. Handysize rate divergence).
> - **Reason:** Sourcing genuine, independent per-vessel freight rate benchmarks
>   requires proprietary, licensed sub-indices (Baltic Capesize Index BCI,
>   Baltic Panamax Index BPI, Baltic Supramax Index BSI, Baltic Handysize
>   Index BHSI) that are paywalled and not publicly accessible.
>   Applying synthetic scalar multipliers to BDRY to fabricate per-vessel
>   rates was explicitly rejected as an ungrounded shortcut violating the
>   project's credibility principles.
> - **Impact on downstream modules:** None. Module D's fix-vs-wait expected-value
>   formula operates on the general dry-bulk freight trajectory and uncertainty spread;
>   vessel-class selection is governed by Module B's port draft/LOA/beam
>   compatibility engine.
> - **Future Scope:** Integrating licensed Baltic sub-indices or ULIP vessel-class
>   fixture feeds to enable authentic cross-vessel rate modeling.

> [!WARNING]
> **AMENDMENT — Multi-Step Forecasting Extrapolation & Recursive Horizon Restriction (added Session 6)**
>
> - **Extrapolation Boundary:** Tree-based models (XGBoost, LightGBM) partition feature space and cannot extrapolate beyond the minimum and maximum target price values observed in training data.
> - **Diagnostic Finding (Recursive Multi-Step Dampening Bias):** Recursive multi-step forecasting across 7, 14, 21, and 28-day horizons was found to introduce systematic downward drift in P50 predictions at longer horizons (21 and 28 days) rather than reflecting genuine market trough dynamics. Diagnostic analysis demonstrated that 77.8% (7 of 9) of historical WAIT recommendations mechanically defaulted to $N=28$ simply because recursive autoregression progressively compounded lower point forecasts over time.
> - **Candidate Horizon Scoping ($N \in \{7, 14\}$):** Candidate decision windows in Module D are strictly restricted to $N \in \{7, 14\}$ days, where the model has demonstrated reliable, empirical stability.
> - **Disclosed Model-Scoping Decision:** This is a disclosed model-scoping decision made after diagnostic investigation, not silent post-hoc data exclusion.
> - **Regime Shift Vulnerability & Black Swan Limitation:** Even under this restricted candidate set, the backtest can still show a net loss relative to the naive baseline during genuine, undocumented market regime shifts. Three historical 2020–2023 events illustrate this limitation:
>   1. *January 2021 Post-COVID Commodity Spike:* Rapid demand acceleration following industrial reopenings.
>   2. *Early 2021 Pre-Suez Freight Squeeze:* Extreme regional tonnage tightening immediately preceding the canal blockage.
>   3. *Early 2023 China Reopening Rally:* Abrupt dry-bulk surge following lifting of pandemic restrictions.
> - **Honest Limitation Framing:** No statistical or ML model trained exclusively on prior data can anticipate genuinely unprecedented shocks. This system's honest job is to perform reliably in normal/detectable-risk regimes while being completely transparent about its blind spots during true Black Swan events. Future work addresses this via direct per-horizon quantile modeling (Section 12).

---

## 1. Problem Statement

- **Problem Statement ID:** SIH26006
- **Category:** Software
- **Theme:** Smart Automation
- **Ministry:** Ministry of Steel, Government of India
- **Title:** Development of an Intelligent Freight Forecasting Model for Optimized Vessel Chartering and Bulk Cargo Procurement from Overseas to East Coast of India

India's steel manufacturing sector depends on imported bulk raw material (primarily coking coal, and iron ore in some flows) sourced from Australia, the United States, Mozambique, Russia, and Indonesia, transported by chartered dry-bulk vessels to India's East Coast ports. The current chartering process is manual, reactive, and daily-market-dependent, resulting in: (a) sub-optimal timing of charter contracts due to lack of predictive insight into freight rate movement, (b) mismatched vessel-type selection against port infrastructure constraints, causing idle time and delays, and (c) exposure to sudden market volatility from geopolitical or climate disruptions with no early-warning mechanism.

**Expected Solution** (as stated in the official PS) requires the system to provide: (a) optimal market entry timing, (b) vessel type optimization against port constraints, (c) idle-time / idle-scenario management, and (d) risk mitigation via early warnings — delivered through a usable dashboard interface, with an underlying objective of shifting the organisation from single spot-voyage contracting toward planned short/medium-term multi-voyage contracting.

**Scope Reference Data (fixed for this prototype):**
- Six East Coast Indian discharge ports — Paradip, Vizag, Gangavaram, Gopalpur, Dhamra, Sagar-Sandheads/Haldia.
- Four vessel size classes — Handysize, Supramax, Panamax, Capesize.
- Five overseas origin regions — Australia, United States, Mozambique, Russia, Indonesia.

## 2. Executive Summary of the Solution

The system is **not** a price-forecasting tool. It is a Chartering Decision Support System, in which price forecasting is one of six tightly integrated modules feeding into a single, explainable, auditable recommendation. This framing is deliberate and load-bearing: it is what maps the solution onto all four lettered requirements of the PS's Expected Solution section, rather than only the forecasting requirement that most competing solutions will address in isolation.

The six modules are:
- **Module A — Forecast Engine** (price prediction, as a quantile range, not a point estimate)
- **Module B — Port-Matching Engine** (dynamic vessel-to-port compatibility check)
- **Module C — Risk Radar** (Black Swan / disruption early-warning, backtested)
- **Module D — Decision Engine** (fix-now-vs-wait recommendation with quantified value)
- **Module E — Idle-Time & Contract Structuring Module** (spot-vs-period recommendation, plus a Speed & Fuel Optimization Advisory sub-module)
- **Module F — Interaction Layer** (Always-On Market Watch + query-driven recommendation + anonymous decision logging)

Every module produces a quantified, backtested, and explainable output. No module is permitted to present a single point number without an accompanying range and reasoning — this rule is a project-wide design constraint, not a per-module choice, and exists specifically to survive technical cross-questioning from domain-expert judges.

## 3. Module-by-Module Deep Specification

### Module A — Forecast Engine

**Purpose:** Predict near-term freight rate ranges per vessel type per route, using free proxy data, validated with strict walk-forward methodology.

**Inputs:** FreightRateData (BDRY proxy — see amendment above regarding historical BDI splicing), MacroIndicators (Brent crude, coal/iron-ore futures proxy, USD/INR), engineered lag features (t-1, t-7, t-30), rolling averages (MA7, MA30), rate-of-change/momentum features.

**Model choice:** Ensemble of XGBoost and LightGBM (gradient-boosted trees) plus a SARIMA/Prophet seasonal baseline. Deep learning (LSTM/Transformer) is explicitly rejected for this data volume — the training set is a few thousand daily rows across a handful of years, which is undersized for deep learning and would overfit; tree-based models and classical time-series models outperform on this scale and run on CPU-only hardware.

**Validation method:** Walk-Forward (rolling-origin) Cross-Validation only. Random 80/20 splits are prohibited project-wide because they leak future information into training for time-series data. Concretely: train on [T0..T1], test on [T1..T1+30 days]; then train on [T0..T1+30], test on the next 30 days; repeat forward through the full historical window. Report only out-of-fold, walk-forward accuracy — never in-sample accuracy — in any documentation or presentation.

**Output:** For a given (route, vessel_type, target_date): a P10 / P50 / P90 quantile price band (not a single number), plus SHAP feature attributions explaining the top 3 contributing factors, stored in `ForecastResults` and `ShapExplanations` (see Section 8).

**Explicit prohibition:** The system must never render a single point-forecast number in the UI without its accompanying P10–P90 band. This is a hard project rule, not a UI nicety — a bare point number misrepresents the genuine uncertainty of this market and is a specific weakness a domain-expert judge will probe.

### Module B — Port-Matching Engine

**Purpose:** Determine which vessel size classes can safely and legally call at a given destination port under current, season-adjusted draft conditions.

**Inputs:** `Ports` (static baseline_draft_m, max_loa_m, max_beam_m per port), `PortDraftAdvisory` (date-specific available_draft_m override, editable/seasonal), `VesselTypes` (required_draft_m, typical_loa_m, typical_beam_m per vessel class).

**Compatibility rule (exact logic):**
```
is_compatible(vessel, port, date) =
    (vessel.required_draft_m <= effective_draft(port, date))
    AND (vessel.typical_loa_m <= port.max_loa_m)
    AND (vessel.typical_beam_m <= port.max_beam_m)

effective_draft(port, date) =
    PortDraftAdvisory.available_draft_m for that port/date if present,
    ELSE port.baseline_draft_m adjusted by a seasonal monsoon-siltation
    reduction factor (a documented approximation, not a live feed —
    stated explicitly as such in the presentation):
      - Southwest Monsoon (June 1 – September 30): 0.90 factor (10% draft reduction
        approximation reflecting heavy estuarine river siltation and high swell at East Coast India ports)
      - Post-Monsoon / Cyclonic Season (October 1 – November 30): 0.95 factor (5% draft reduction approximation)
      - Fair Weather Season (December 1 – May 31): 1.00 factor (full design baseline draft)
      - Origin Ports (Overseas loading): 1.00 factor unless advisory is on record.
```

**Output:** For a given cargo volume and destination port, a ranked list of compatible vessel types, largest-safe-first (larger vessel classes reduce per-ton freight cost when compatible). This feeds directly into Module D's recommendation.

**Design constraint:** Port draft must never be hardcoded as a single fixed constant in the codebase. It must always be read as a time-varying, overridable value — this is the single most differentiating engineering decision in the whole system relative to what other teams are expected to submit.

### Module C — Risk Radar

**Purpose:** Detect conditions resembling historical market-disrupting events and raise an explicit warning that overrides normal forecast confidence — rather than letting Module A silently produce a confidently wrong number during a crisis.

**Inputs:** `RiskEvents` (curated historical disruption dataset: Suez Canal blockage 2021, Red Sea/Houthi disruption 2023-24, major cyclone impacts on Mozambique/East Coast India ports, and others, each tagged with date, affected route, severity, and historical price-impact percentage), current `MacroIndicators` and `FreightRateData` volatility (rolling standard deviation).

**Method:** Primarily backtested, not live-scraped, for reliability reasons: the system is validated by replaying the historical `RiskEvents` dataset and confirming that a volatility-threshold rule would have flagged each event in advance or concurrently. A live news/RSS keyword classifier (scanning for terms such as strike, cyclone, blockage, war near a tracked route) is a stated stretch-goal / optional layer, not a load-bearing dependency for the core demo.

**Output:** `RiskFlags` entries at route level (risk_level: calm / elevated / high, with a plain-language reason string). An active 'high' flag causes Module D to widen its recommended decision's caution margin and causes the Interaction Layer (Module F) to surface it proactively, unprompted.

### Module D — Decision Engine (core differentiator)

**Purpose:** Convert a price forecast into an actual business decision — fix the charter now, or wait — expressed as a quantified expected value, not a bare description of the forecast.

**Conceptual basis:** A simplified real-options framing: waiting to fix a charter has value only if the expected price improvement outweighs the risk-adjusted cost of delay (including demurrage/schedule risk and volatility exposure).

**Exact computation:**
```
F_now      = ForecastResults.p50_price  for target_date = today
F_wait(N)  = ForecastResults.p50_price  for target_date = today + N days
spread(N)  = ForecastResults.p90_price - ForecastResults.p10_price  at day N
risk_mult  = 1.5 if RiskFlags.risk_level == 'high' else
             1.15 if RiskFlags.risk_level == 'elevated' else 1.0

RiskPremium(N) = 0.5 * spread(N) * risk_mult

ExpectedValueOfWaiting(N) = (F_now - F_wait(N)) - RiskPremium(N)

DECISION RULE:
  IF ExpectedValueOfWaiting(N) > 0  ->  Recommend WAIT (report N-day window
        and the expected USD/day saving = ExpectedValueOfWaiting(N))
  ELSE                              ->  Recommend FIX NOW (report the
        expected USD/day cost avoided versus the worse alternative)
```

> [!IMPORTANT]
> **Production Candidate Horizon Limitation ($N \in \{7, 14\}$):**
> Live candidate horizons evaluated by `make_chartering_decision` are restricted strictly to $N \in \{7, 14\}$ days. Diagnostic analysis revealed that recursive multi-step autoregressive forecasting systematically dampens P50 price forecasts at longer horizons (21 and 28 days), causing 77.8% of historical WAIT decisions to mechanically select $N=28$ regardless of genuine trough dynamics. Restricting candidate windows to $\{7, 14\}$ preserves empirical stability. As disclosed, during unprecedented regime shifts (the Jan 2021 post-COVID commodity spike, early 2021 pre-Suez freight squeeze, and China's 2023 reopening rally), waiting can show a net loss relative to the naive baseline; this is an authentic, disclosed limitation of training solely on prior data when facing Black Swan disruptions.

**Output:** A `DecisionRecommendations` record: recommended_action (fix_now / wait), recommended_vessel_type_id (from Module B's ranked list), expected_price, and expected_savings_usd — always accompanied by the SHAP-based explanation of which features drove the recommendation.

**Validation requirement:** Before this module is considered complete, it must be backtested against a naive 'always fix immediately' baseline strategy over the full historical window, across a representative simulated set of 20-30 cargo fixtures spread through the period. The resulting aggregate saving (in USD or % of charter cost) is the project's single most important headline metric. If this backtest produces an implausibly large saving (e.g., >20-25%), treat that as a signal of a bug or data leakage in the simulation, not as a genuine result, and debug before reporting it.

### Module E — Idle-Time & Contract Structuring Module

This module directly answers PS requirement (c), Idle Scenario Management, which is not addressed by Modules A-D alone. It has two sub-components.

**E1. Spot-vs-Period Recommendation**

Purpose: Detect forecasted demand/price troughs and recommend structuring a period (time) charter across the trough instead of re-entering the spot market voyage-by-voyage — directly reflecting the PS Objective's stated goal of moving from single spot contracts to multi-voyage contracts.

Logic: Scan the P50 forecast curve forward; if a contiguous window of length >= a configurable threshold (default 21 days) has P50 below the trailing 20th percentile of historical prices, flag it as a trough. Recommend a period-charter duration spanning that window.

Validation: Backtest a 'spot-only' simulated strategy against a 'period-charter-when-trough-detected' simulated strategy across historical data; report the idle-days and cost delta between them.

Output: `IdleTimeAnalysis` record: recommended_contract_type (spot / period), forecasted_trough_start/end, estimated_cost_saved_usd.

**E2. Speed & Fuel Optimization Advisory (Just-In-Time Arrival)**

Purpose: When a vessel is already underway ('midway') and the destination port has a forecasted congestion/waiting period, recommend a reduced transit speed so the vessel arrives closer to its actual berth availability, instead of sailing at full speed and then idling (burning fuel) at anchorage. This is a recognised industry practice (Just-In-Time arrival / slow steaming, referenced in IMO decarbonisation guidance) and gives the project a genuine sustainability/emissions angle in addition to a cost angle.

Physical basis: Fuel consumption per unit time rises approximately with the cube of speed; for a fixed distance, total fuel burned is therefore approximately proportional to the square of speed (since time-at-sea falls as speed rises). Slowing down to match true berth availability reduces total fuel burned for the same overall arrival outcome.

**Exact computation:**
```
d              = distance_remaining_nm
v_std          = VesselTypes.standard_speed_knots
T_required     = (d / v_std) + expected_port_congestion_hours - safety_buffer_hours
v_recommended  = clamp(d / T_required, min_safe_speed_knots, v_std)

Fuel_ref(d, v)      = fuel_curve_coef * d * (v ** 2)   # relative units
Fuel_saved          = Fuel_ref(d, v_std) - Fuel_ref(d, v_recommended)
CO2_reduced_kg      = Fuel_saved * emission_factor_kg_per_unit
Cost_saved_usd      = Fuel_saved * bunker_fuel_price_usd_per_unit
```

Output: `SpeedOptimizationLog` record: standard_speed_knots, recommended_speed_knots, port_congestion_hours, fuel_saved_tons, co2_reduced_kg — surfaced alongside the Module D recommendation whenever a cargo request's vessel is marked as already in transit.

### Module F — Interaction Layer (User-Facing Behaviour)

The interaction model is two-layered, correcting an earlier design gap where risk information was only ever available on-demand (a 'pull' model), which does not satisfy the PS's explicit requirement for 'early warnings'.

**Layer 1 — Always-On Market Watch (no user input required):** On opening the dashboard, before any query is entered, the user sees a persistent status panel showing: current overall market sentiment (derived from active RiskFlags across all tracked routes), and a one-line plain-language reason for any active flag. This is populated by the daily-scheduled Risk Radar output (Module C) and requires no action from the user — this is what actually satisfies 'early warning' rather than only answering a question the user thought to ask.

**Layer 2 — Query-Driven Recommendation:** The user enters a `CargoRequests` record (cargo type, volume, origin, destination, desired timeframe). The system runs Modules A-E against this request and returns a single consolidated recommendation panel: recommended vessel type (Module B), fix-now-or-wait decision with quantified value (Module D), spot-vs-period structuring advice (Module E1), speed/fuel advisory if applicable (Module E2), and any active risk flag on that specific route (Module C), each with a plain-language 'why' derived from SHAP attributions.

**Closing the loop — Mark as Actioned:** Every `DecisionRecommendations` shown to the user has a 'Mark as Actioned' action, which writes an anonymous, timestamped `ActionedDecisions` record (no user identity is attached, consistent with this being a prototype with a single implied user role). This is intentionally kept simple for the prototype stage. A full outcome-tracking feedback loop (recording whether the real-world result later matched the recommendation) is named explicitly as Future Scope (Section 12) rather than attempted now, since it requires weeks/months of accumulated real decisions to produce any meaningful signal — attempting it prematurely would produce an empty or misleading feature rather than a working one.

## 4. Uniqueness & Differentiation

Most competing teams attempting this PS will build a price-prediction chart wrapped in a dashboard. This project is differentiated on six specific, defensible points:

1. **Decision output, not a price output.** The system's primary output is a recommended action with a quantified expected value (Module D), not a bare predicted number.
2. **Dynamic, not static, port constraints.** Port draft is modelled as a time-varying, overridable quantity (Module B), reflecting real monsoon/siltation/tidal variation, instead of a hardcoded constant.
3. **Honest uncertainty representation.** All forecasts are presented as P10-P90 ranges, never as a single misleadingly precise number.
4. **Explicit, backtested risk-flagging instead of false confidence.** Rather than pretending a numerical model can predict Black Swan events, the Risk Radar (Module C) is validated against real historical disruptions and flags risk instead of silently producing a wrong number.
5. **Idle-time and sustainability coverage.** Module E directly answers the PS's Idle Scenario Management requirement (largely ignored by naive competing solutions) and adds a genuine fuel/emissions-saving angle via the Speed & Fuel Optimization Advisory.
6. **Proactive early warning, not just on-demand querying.** The Always-On Market Watch layer (Module F) surfaces risk before the user even asks, directly satisfying the PS's 'early warnings' language.
7. **Proven historical value, not just a working demo.** Every module that makes a claim (Decision Engine savings, Idle-Time savings, Speed Advisory fuel savings) is required to be backtested against a naive baseline and reported as a concrete number — this is the single strongest piece of evidence presented to the jury.

**One-sentence pitch:** "Not a price predictor — a decision-support system that tells a chartering manager exactly what to do, why, and proves with real historical data how much money and fuel that decision would have saved."

## 5. End-to-End Workflow

User: A chartering/logistics manager at a steel manufacturer or PSU (e.g., functions comparable to those at SAIL, RINL, NMDC), responsible for arranging vessel charters for overseas coal/iron-ore cargo movements to East Coast India.

| Step | Actor | Action / System Response |
|---|---|---|
| 1 | User | Opens dashboard. Sees Always-On Market Watch panel (Module F, Layer 1) with no input required — current sentiment and any active risk flags across tracked routes. |
| 2 | User | Enters a `CargoRequests`: cargo type, volume, origin port, destination port, desired timeframe. |
| 3 | System | Module B computes compatible vessel types for the destination port under current draft conditions. |
| 4 | System | Module A produces a P10/P50/P90 price forecast for each compatible vessel type on the relevant route. |
| 5 | System | Module C checks for an active risk flag on this specific route and adjusts confidence accordingly. |
| 6 | System | Module D computes the fix-now-vs-wait recommendation with quantified expected value. |
| 7 | System | Module E1 checks for a forecasted trough and recommends spot vs. period contracting; Module E2 computes a speed/fuel advisory if the vessel is already in transit. |
| 8 | System | All outputs are consolidated into one recommendation panel with plain-language SHAP-based reasoning, shown to the user. |
| 9 | User | Reviews the recommendation and, if acted upon, clicks 'Mark as Actioned' — logged anonymously with a timestamp. |

## 6. Technology Stack

| Layer | Choice | Rationale |
|---|---|---|
| Frontend | React + Vite + Tailwind CSS | Fast dev builds on low-mid hardware; large community; easy to split across team members |
| Charts / visuals | Recharts or Chart.js | Lightweight rendering of forecast bands and SHAP explanations |
| Backend / API | Python + FastAPI | Hosts the ML/decision logic and exposes it to the frontend; required because Supabase/Neon-style platforms cannot run this Python logic themselves |
| ML / forecasting | pandas, XGBoost, LightGBM, Prophet/SARIMA, scikit-learn (TimeSeriesSplit), SHAP | CPU-friendly; appropriate for the data volume; avoids unjustified deep-learning complexity |
| Database | Neon (managed serverless Postgres) | Free, permanent, auto-resumes on query with no manual unpause step (unlike Supabase's inactivity-pause behaviour) — chosen specifically to avoid a reliability risk for a team without dedicated ops time |
| Authentication | None (deliberately omitted) | Prototype has a single implied user role; auth would consume build time without adding judged value at this stage |
| Scheduled data ingestion | GitHub Actions (free cron) + yfinance + requests | Automates daily data refresh without requiring a laptop to run continuously |
| Deployment | Frontend: Vercel (free). Backend: Render or Railway (free tier) | Zero cost, gives a real live demo URL rather than a local-only build |
| Version control | Git + GitHub | Standard; allows technical judges to audit the walk-forward validation code if asked |

**Note on ULIP** (Unified Logistics Interface Platform, Government of India): a genuine, relevant government logistics data API, but access requires registration, use-case review, and in some cases an NDA before production API access is granted — a multi-step approval process incompatible with a fixed hackathon timeline unless access is already secured. It is therefore named in Section 12 (Future Scope) as the intended production-grade data source, and is not a dependency of the working prototype.

## 7. Data Architecture (Conceptual Flow)

```
STAGE 1: INGEST
  Daily scheduled fetch (GitHub Actions) of:
  - Freight rate proxy (BDRY via yfinance) — [see amendment: 2018-present only, no BDI splice]
  - Macro indicators (Brent crude, coal/iron-ore proxy, USD/INR)
  - Port draft advisories (manually/periodically updated)
        |
        v
STAGE 2: STORE
  Written to Neon Postgres tables (see Section 8 ER Diagram)
        |
        v
STAGE 3: TRANSFORM
  Clean, deduplicate, align to common date index, engineer lag /
  rolling-average / momentum features, compute port-compatibility flags
        |
        v
STAGE 4: WALK-FORWARD SPLIT
  Rolling-origin train/test folds (never random 80/20)
        |
        v
STAGE 5: MODEL
  XGBoost / LightGBM / Prophet ensemble -> P10/P50/P90 forecast + SHAP
        |
        v
STAGE 6: DECIDE
  Modules B, C, D, E consume the forecast to produce the consolidated
  recommendation
        |
        v
STAGE 7: SERVE
  FastAPI exposes the recommendation to the React dashboard
```

## 8. Database Design — Entity Relationship Diagram (15 Tables)

### 8.1 Reference / Master Data Tables

**Ports** — Master list of all origin (overseas loading) and destination (East Coast India) ports in scope.

| Attribute | Data Type | Constraint | Description |
|---|---|---|---|
| port_id | SERIAL | PRIMARY KEY | Unique port identifier |
| name | VARCHAR(100) | NOT NULL | e.g. Paradip, Newcastle |
| country | VARCHAR(80) | NOT NULL | e.g. India, Australia |
| port_role | VARCHAR(20) | NOT NULL | 'origin' or 'destination' |
| max_loa_m | NUMERIC(6,2) | NOT NULL | Maximum vessel length overall the port can accept, in metres |
| max_beam_m | NUMERIC(6,2) | NOT NULL | Maximum vessel beam (width) the port can accept, in metres |
| baseline_draft_m | NUMERIC(5,2) | NOT NULL | Design/baseline water depth in metres, before seasonal adjustment |
| latitude | NUMERIC(9,6) | NULL | For map display |
| longitude | NUMERIC(9,6) | NULL | For map display |

**VesselTypes** — The four vessel size classes in scope, with their physical and operating parameters.

| Attribute | Data Type | Constraint | Description |
|---|---|---|---|
| vessel_type_id | SERIAL | PRIMARY KEY | Unique vessel-class identifier |
| name | VARCHAR(30) | NOT NULL, UNIQUE | Handysize / Supramax / Panamax / Capesize |
| min_dwt | INTEGER | NOT NULL | Minimum deadweight tonnage for this class |
| max_dwt | INTEGER | NOT NULL | Maximum deadweight tonnage for this class |
| required_draft_m | NUMERIC(5,2) | NOT NULL | Minimum water depth this vessel class needs, laden |
| typical_loa_m | NUMERIC(6,2) | NOT NULL | Typical length overall for this class |
| typical_beam_m | NUMERIC(6,2) | NOT NULL | Typical beam for this class |
| standard_speed_knots | NUMERIC(4,1) | NOT NULL | Standard laden service speed |
| fuel_curve_coef | NUMERIC(8,4) | NOT NULL | Coefficient used in the fuel-vs-speed formula (Module E2) |

**Routes** — Defined origin-to-destination shipping lanes used by the forecasting and risk modules.

| Attribute | Data Type | Constraint | Description |
|---|---|---|---|
| route_id | SERIAL | PRIMARY KEY | Unique route identifier |
| origin_port_id | INTEGER | FOREIGN KEY -> Ports.port_id | Loading port |
| destination_port_id | INTEGER | FOREIGN KEY -> Ports.port_id | Discharge port |
| distance_nm | INTEGER | NOT NULL | Sailing distance in nautical miles |
| typical_transit_days | NUMERIC(4,1) | NOT NULL | Typical laden voyage duration |

### 8.2 Ingested Time-Series / Reference Data Tables

**FreightRateData** — Daily freight rate proxy values (BDRY-derived — see amendment above), per vessel class.

| Attribute | Data Type | Constraint | Description |
|---|---|---|---|
| rate_id | SERIAL | PRIMARY KEY | Unique row identifier |
| date | DATE | NOT NULL | Observation date |
| vessel_type_id | INTEGER | FOREIGN KEY -> VesselTypes.vessel_type_id, NULLABLE | Which vessel class this rate applies to (NULL = general dry-bulk market index) |
| index_type | VARCHAR(30) | NOT NULL | 'BDRY_proxy' (currently the only value in use per amendment) |
| value_usd_per_day | NUMERIC(10,2) | NOT NULL | Rate value |
| source | VARCHAR(50) | NOT NULL | Data provenance, for transparency in the report |

**MacroIndicators** — Daily macro/leading-indicator series used as model features (Brent crude, coal/iron-ore proxy, USD/INR).

| Attribute | Data Type | Constraint | Description |
|---|---|---|---|
| indicator_id | SERIAL | PRIMARY KEY | Unique row identifier |
| date | DATE | NOT NULL | Observation date |
| indicator_type | VARCHAR(30) | NOT NULL | 'brent_crude' / 'coal_futures' / 'usd_inr' / 'iron_ore' |
| value | NUMERIC(12,4) | NOT NULL | Indicator value |

**PortDraftAdvisory** — Date-specific overrides to a port's available draft, reflecting monsoon/tidal/siltation variation. This is the table that makes port constraints dynamic rather than hardcoded.

| Attribute | Data Type | Constraint | Description |
|---|---|---|---|
| advisory_id | SERIAL | PRIMARY KEY | Unique row identifier |
| port_id | INTEGER | FOREIGN KEY -> Ports.port_id | Which port this advisory applies to |
| date | DATE | NOT NULL | Effective date |
| available_draft_m | NUMERIC(5,2) | NOT NULL | Draft available on this date (overrides Ports.baseline_draft_m) |
| season_tag | VARCHAR(20) | NULL | e.g. 'monsoon', 'post-dredging' |

**RiskEvents** — Curated historical disruption dataset used to validate the Risk Radar (Module C) by backtesting.

| Attribute | Data Type | Constraint | Description |
|---|---|---|---|
| event_id | SERIAL | PRIMARY KEY | Unique row identifier |
| date | DATE | NOT NULL | Event date |
| event_type | VARCHAR(40) | NOT NULL | 'canal_blockage' / 'cyclone' / 'geopolitical' / etc. |
| description | TEXT | NOT NULL | Short description |
| affected_route_id | INTEGER | FOREIGN KEY -> Routes.route_id, NULLABLE | Route most impacted, if applicable |
| severity_level | VARCHAR(10) | NOT NULL | 'low' / 'medium' / 'high' |
| historical_price_impact_pct | NUMERIC(6,2) | NULL | Observed price move following the event, for backtest comparison |

### 8.3 Workflow / Request-Driven Tables

**CargoRequests** — One row per query the user submits through the dashboard.

| Attribute | Data Type | Constraint | Description |
|---|---|---|---|
| request_id | SERIAL | PRIMARY KEY | Unique request identifier |
| created_at | TIMESTAMP | NOT NULL DEFAULT now() | When the request was submitted |
| cargo_type | VARCHAR(40) | NOT NULL | e.g. 'coking_coal', 'iron_ore' |
| cargo_volume_tons | INTEGER | NOT NULL | Cargo size |
| origin_port_id | INTEGER | FOREIGN KEY -> Ports.port_id | Loading port for this request |
| destination_port_id | INTEGER | FOREIGN KEY -> Ports.port_id | Discharge port for this request |
| desired_timeframe_days | INTEGER | NOT NULL | How soon the cargo needs to move |
| desired_contract_pref | VARCHAR(10) | NULL | User's stated preference, if any: 'spot' / 'period' / 'no_preference' |

**ForecastResults** — Output of Module A for a given request and vessel type.

| Attribute | Data Type | Constraint | Description |
|---|---|---|---|
| forecast_id | SERIAL | PRIMARY KEY | Unique row identifier |
| request_id | INTEGER | FOREIGN KEY -> CargoRequests.request_id | Which request this forecast was generated for |
| generated_at | TIMESTAMP | NOT NULL DEFAULT now() | Generation timestamp |
| vessel_type_id | INTEGER | FOREIGN KEY -> VesselTypes.vessel_type_id, NULLABLE | Vessel class this forecast covers (NULL = general dry-bulk forecast) |
| p10_price | NUMERIC(10,2) | NOT NULL | 10th percentile forecast price |
| p50_price | NUMERIC(10,2) | NOT NULL | Median forecast price |
| p90_price | NUMERIC(10,2) | NOT NULL | 90th percentile forecast price |
| model_version | VARCHAR(20) | NOT NULL | Model/version tag, for reproducibility |

**ShapExplanations** — Feature-attribution rows explaining a specific ForecastResults entry.

| Attribute | Data Type | Constraint | Description |
|---|---|---|---|
| explanation_id | SERIAL | PRIMARY KEY | Unique row identifier |
| forecast_id | INTEGER | FOREIGN KEY -> ForecastResults.forecast_id | Which forecast this explains |
| feature_name | VARCHAR(50) | NOT NULL | e.g. 'capesize_index_ma7', 'brent_crude_lag7' |
| contribution_pct | NUMERIC(5,2) | NOT NULL | Relative contribution to this prediction |
| direction | VARCHAR(10) | NOT NULL | 'upward' / 'downward' |

**RiskFlags** — Output of Module C — active or historical risk flags per route.

| Attribute | Data Type | Constraint | Description |
|---|---|---|---|
| flag_id | SERIAL | PRIMARY KEY | Unique row identifier |
| date | DATE | NOT NULL | Date this flag was raised |
| route_id | INTEGER | FOREIGN KEY -> Routes.route_id, NULLABLE | Route this flag applies to (NULL = market-wide) |
| risk_level | VARCHAR(10) | NOT NULL | 'calm' / 'elevated' / 'high' |
| reason | TEXT | NOT NULL | Plain-language explanation shown to the user |
| is_active | BOOLEAN | NOT NULL DEFAULT true | Whether this flag is currently in effect |

### 8.4 Recommendation & Action-Logging Tables

**DecisionRecommendations** — Output of Module D — the core fix-now-vs-wait recommendation for a request.

| Attribute | Data Type | Constraint | Description |
|---|---|---|---|
| decision_id | SERIAL | PRIMARY KEY | Unique row identifier |
| request_id | INTEGER | FOREIGN KEY -> CargoRequests.request_id | Which request this decision is for |
| recommended_vessel_type_id | INTEGER | FOREIGN KEY -> VesselTypes.vessel_type_id | Vessel type recommended (from Module B's ranked list) |
| recommended_action | VARCHAR(10) | NOT NULL | 'fix_now' / 'wait' |
| expected_price | NUMERIC(10,2) | NOT NULL | Expected price under the recommended action |
| expected_savings_usd | NUMERIC(10,2) | NOT NULL | Quantified expected value of the recommendation (Module D formula output) |
| generated_at | TIMESTAMP | NOT NULL DEFAULT now() | Generation timestamp |

**IdleTimeAnalysis** — Output of Module E1 — spot-vs-period contract structuring recommendation for a request.

| Attribute | Data Type | Constraint | Description |
|---|---|---|---|
| analysis_id | SERIAL | PRIMARY KEY | Unique row identifier |
| request_id | INTEGER | FOREIGN KEY -> CargoRequests.request_id | Which request this analysis is for |
| recommended_contract_type | VARCHAR(10) | NOT NULL | 'spot' / 'period' |
| forecasted_trough_start | DATE | NULL | Start of a detected low-demand window, if any |
| forecasted_trough_end | DATE | NULL | End of a detected low-demand window, if any |
| estimated_cost_saved_usd | NUMERIC(10,2) | NULL | Backtested estimate of savings from this recommendation |

**SpeedOptimizationLog** — Output of Module E2 — Just-In-Time speed/fuel advisory for a request whose vessel is already in transit.

| Attribute | Data Type | Constraint | Description |
|---|---|---|---|
| speed_id | SERIAL | PRIMARY KEY | Unique row identifier |
| request_id | INTEGER | FOREIGN KEY -> CargoRequests.request_id | Which request this advisory is for |
| route_id | INTEGER | FOREIGN KEY -> Routes.route_id | Route being sailed |
| standard_speed_knots | NUMERIC(4,1) | NOT NULL | Vessel's normal service speed |
| recommended_speed_knots | NUMERIC(4,1) | NOT NULL | Computed recommended reduced speed |
| port_congestion_hours | NUMERIC(6,1) | NOT NULL | Estimated destination port waiting time driving this recommendation |
| fuel_saved_tons | NUMERIC(8,2) | NOT NULL | Estimated fuel saved by slowing down vs. standard speed |
| co2_reduced_kg | NUMERIC(10,2) | NOT NULL | Estimated emissions reduction, derived from fuel_saved_tons |

**ActionedDecisions** — Anonymous log of recommendations the user marked as acted upon. Intentionally simple for the prototype stage (see Section 12).

| Attribute | Data Type | Constraint | Description |
|---|---|---|---|
| action_id | SERIAL | PRIMARY KEY | Unique row identifier |
| decision_id | INTEGER | FOREIGN KEY -> DecisionRecommendations.decision_id | Which recommendation was actioned |
| actioned_at | TIMESTAMP | NOT NULL DEFAULT now() | When it was marked actioned |
| note | TEXT | NULL | Optional free-text note |

## 9. Challenges and Fixes

1. **No access to paid, professional freight-market data.** Fix: use BDRY (a free, liquid ETF tracking Capesize/Panamax/Supramax dry-bulk freight futures) via yfinance. *(Amendment: pre-2018 BDI splicing originally planned here is now explicitly out of scope — see amendment block at top of document.)*
2. **Black Swan events break numerical forecasting models.** Fix: Module C (Risk Radar) is validated by backtesting against a curated historical disruption dataset (`RiskEvents`) rather than relying solely on a live news scraper, which is fragile to demo live.
3. **Port draft is not static.** Fix: Module B treats draft as a time-varying, overridable value (`PortDraftAdvisory` table) rather than a hardcoded constant, with a documented seasonal approximation where live tide data is unavailable.
4. **Time-series data leakage from naive train/test splitting.** Fix: project-wide mandatory Walk-Forward (rolling-origin) Cross-Validation for Module A; in-sample or randomly-split accuracy figures are never reported.
5. **False precision from single-point forecasts.** Fix: Module A outputs P10/P50/P90 ranges exclusively; the UI is prohibited from displaying a bare point forecast.
6. **Low-to-mid tier team hardware, no cloud budget.** Fix: model choice (gradient-boosted trees, not deep learning) is deliberately matched to the data volume and runs on CPU; all infrastructure (GitHub Actions, Neon, Vercel, Render) is free-tier.
7. **Idle Scenario Management was initially missing entirely.** Fix: added Module E (spot-vs-period structuring + speed/fuel optimization advisory), directly closing PS requirement (c).
8. **'Early warning' was initially only available on-demand.** Fix: added the Always-On Market Watch layer (Module F, Layer 1), surfacing active risk flags proactively on dashboard load rather than only in response to a specific query.
9. **Freight-proxy divergence risk was undisclosed.** Fix: the project report must state the correlation between the BDRY-based proxy and any available India-specific rate reference points, honestly, including where they diverge, rather than presenting the proxy as equivalent to the real paywalled index without qualification. *(This principle is exactly why the Option B amendment above is disclosed explicitly rather than glossed over.)*
10. **Implausible backtest savings figures & recursive forecasting horizon bias.** Fix: any Module D or Module E backtest result showing an implausibly large saving (rule of thumb: above roughly 20-25%) must be treated as a probable leakage/bug signal and investigated before being reported, not presented as a positive result. Furthermore, diagnostic analysis of Module D backtest outputs revealed that recursive multi-step forecasting systematically dampens P50 predictions at 21 and 28 days, mechanically biasing the engine so that 77.8% of WAIT recommendations defaulted to $N=28$. To prevent this recursive rollout artifact from driving production decisions, candidate windows were strictly restricted to $N \in \{7, 14\}$ days where the model demonstrates reliable behavior. This is a disclosed model-scoping decision made after diagnostic investigation, not silent post-hoc data exclusion. Even under this restriction, the system honestly discloses potential losses during unprecedented regime shifts (e.g., the Jan 2021 post-COVID commodity spike, early 2021 pre-Suez freight squeeze, and China's 2023 reopening rally), treating model boundaries during Black Swan shocks with complete transparency.

## 10. Feasibility & Viability

**Technical feasibility:** All chosen models (XGBoost, LightGBM, SARIMA/Prophet) run on standard CPU hardware within seconds for this data volume. All infrastructure choices (Neon, GitHub Actions, Vercel, Render) have durable, genuinely free tiers suitable for a team with no budget.

**Data feasibility:** All primary data sources (yfinance tickers, World Bank/UNCTAD public reports, manually compiled port infrastructure tables) are free and do not require paid subscriptions or institutional approval, with the sole exception of ULIP, which is explicitly scoped as future work rather than a dependency.

**Operational feasibility:** The prototype has no authentication and a single implied user role, which minimises build complexity while still faithfully representing the real target user's workflow (a chartering manager) for demonstration purposes.

**Economic feasibility (for eventual real deployment):** The system is designed so that its only paid dependency in a production deployment would be upgrading from free-tier data proxies to a licensed freight-index subscription (e.g., Baltic Exchange) and, if desired, formal ULIP production access — both are drop-in replacements for Module A's and Module E's respective data inputs, not architecture changes.

## 11. Impact & Benefits

- **Cost savings:** quantified, backtested reduction in chartering cost versus a naive always-fix-immediately baseline (Module D), plus idle-time cost avoidance (Module E1).
- **Sustainability:** measurable fuel and CO2 reduction from the Speed & Fuel Optimization Advisory (Module E2), directly supporting India's shipping decarbonisation goals.
- **Decision transparency:** every recommendation is accompanied by a plain-language, SHAP-based explanation, supporting internal accountability for the chartering manager's decisions.
- **Policy alignment:** directly supports the PS Objective of shifting from single spot-voyage contracting to planned short/medium-term multi-voyage contracting.
- **Scalability:** the same architecture generalises beyond the six ports / four vessel classes / five origin countries used in this prototype, simply by extending the Ports, VesselTypes, and Routes reference tables.

## 12. Future Scope

- Formal ULIP (Unified Logistics Interface Platform) integration once use-case approval and production API access are secured, replacing manually-compiled port/logistics reference data with live government data feeds.
- Live AIS-based vessel positioning for true deadheading/backhaul optimization, extending Module E2 beyond the current congestion-estimate approximation.
- A full outcome-tracking feedback loop on `ActionedDecisions` — recording actual post-decision results against what was recommended, enabling the system to be evaluated (and to improve) against its own real-world track record over time.
- A live news/RSS-based NLP classifier as an optional real-time layer on top of the currently backtest-validated Risk Radar.
- **(Added)** Sourcing real, verified pre-2018 historical BDI data to restore full splicing coverage, if a safe and reliable source is identified after the prototype deadline.
- **(Added)** Rule-based lighterage & offshore transshipment cost comparison: Modeling two-stage lightening (e.g. Capesize lighterage at Sagar/Sandheads deepwater anchorage prior to Haldia riverine transit, or Paradip SPM deep-draft offshore lighterage) comparing lighterage barge/demurrage fees against direct smaller-vessel voyage charter costs.
- **(Added)** Direct Per-Horizon Quantile Modeling: Replacing recursive multi-step autoregressive rollout with direct, independent per-horizon quantile models (e.g., dedicated models trained specifically for $h=7$, $h=14$, $h=21$, and $h=28$ days). This eliminates the compounding recursive downward dampening bias observed at longer horizons and enables safely expanding candidate windows beyond 14 days without mechanical default to the maximum horizon.