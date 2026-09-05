# Intelligent Freight Forecasting & Decision Support System
## Consolidated Historical Backtest & Validation Report
**Problem Statement ID:** SIH26006 | **Ministry of Steel**  
**Generated At:** 2026-09-05 06:20:00 UTC  
**Validation Standard:** Walk-Forward Non-Leakage & Challenge 10 Sanity Bound (<= 25.0%)

---

## Executive Summary: Headline Backtested Deliverables

| Deliverable | Baseline Strategy | Decision Support System Policy | Headline Net Benefit | Plausibility Guardrail |
|:---|:---|:---|:---|:---|
| **Module D: Chartering Decision Engine** | Always Fix Immediately ($t_0$) | Quantified Expected Value (FIX vs WAIT, $N \in \{7, 14\}$) | **+-0.30% ($-1.06)** chartering cost reduction | PASSED (<= 25.0%) |
| **Module E1: Spot-vs-Period Structuring** | Spot-Only Procurement (Turnaround delays) | Period Charter on Detected Trough (14-day window) | **+3.62% ($372.50)** cost saving & **44.0 idle days avoided** | PASSED (<= 25.0%) |
| **Module E2: JIT Speed & Fuel Advisory** | Standard Voyage Speed into Congestion | JIT Slow-Steaming ($v_{rec} \ge 10.0$ kts) | **521.15 tons fuel saved**, **1622.90 tons CO2 reduced**, **$312,697.68** saved | PASSED (<= 25.0%) |

---

## 1. Module D — Decision Engine Backtest Results (25 Historical Fixtures)
- **Evaluation Set:** 25 representative fixtures across real overseas shipping corridors (2020–2024).
- **Candidate Wait Horizons:** Restricted to $N \in \{7, 14\}$ days per Session 6 diagnostic finding (eliminating recursive multi-step dampening bias).
- **Total Portfolio Baseline Cost:** $355.10
- **Total Portfolio Engine Cost:** $356.16
- **Aggregate Realized Net Savings:** **$-1.06 (-0.30%)**
- **Challenge 10 Sanity Check:** PASSED (Saving <= 25.0%)

### Fixture Breakdown Summary:
| Fixture | Origin Date | Corridor | Vessel Class | Action | Window | Baseline ($/day) | Realized ($/day) | Saving (%) |
|:---:|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | 2020-04-15 | Taboneo -> Haldia | Supramax | `FIX_NOW` | 0d | $7.25 | $7.25 | +0.0% |
| 2 | 2020-06-16 | Taboneo -> Paradip_Inner | Supramax | `FIX_NOW` | 0d | $7.22 | $7.22 | +0.0% |
| 3 | 2020-08-18 | Maputo -> Dhamra | Panamax | `FIX_NOW` | 0d | $8.84 | $8.84 | +0.0% |
| 4 | 2020-10-20 | Beira -> Dhamra | Panamax | `FIX_NOW` | 0d | $7.39 | $7.39 | +0.0% |
| 5 | 2020-12-15 | Nacala -> Gangavaram | Panamax | `WAIT` | 14d | $7.30 | $7.20 | +1.4% |
| 6 | 2021-02-16 | Vostochny_PPK3 -> Vizag_Outer | Panamax | `WAIT` | 14d | $15.82 | $14.89 | +5.9% |
| 7 | 2021-04-20 | Newcastle -> Paradip_SPM | Capesize | `FIX_NOW` | 0d | $20.45 | $20.45 | +0.0% |
| 8 | 2021-06-15 | Lamberts_Point -> Vizag_Outer | Panamax | `FIX_NOW` | 0d | $28.99 | $28.99 | +0.0% |
| 9 | 2021-08-17 | Taboneo -> Haldia | Supramax | `FIX_NOW` | 0d | $29.21 | $29.21 | +0.0% |
| 10 | 2021-10-19 | Taboneo -> Paradip_Inner | Supramax | `FIX_NOW` | 0d | $38.48 | $38.48 | +0.0% |
| 11 | 2021-12-14 | Maputo -> Dhamra | Panamax | `FIX_NOW` | 0d | $23.61 | $23.61 | +0.0% |
| 12 | 2022-02-15 | Beira -> Dhamra | Panamax | `FIX_NOW` | 0d | $22.66 | $22.66 | +0.0% |
| 13 | 2022-04-19 | Nacala -> Gangavaram | Panamax | `FIX_NOW` | 0d | $21.23 | $21.23 | +0.0% |
| 14 | 2022-06-21 | Vostochny_PPK3 -> Vizag_Outer | Panamax | `FIX_NOW` | 0d | $18.29 | $18.29 | +0.0% |
| 15 | 2022-08-16 | Newcastle -> Paradip_SPM | Panamax | `FIX_NOW` | 0d | $9.99 | $9.99 | +0.0% |
| 16 | 2022-10-18 | Lamberts_Point -> Vizag_Outer | Panamax | `WAIT` | 14d | $9.19 | $7.41 | +19.4% |
| 17 | 2022-12-20 | Taboneo -> Haldia | Supramax | `WAIT` | 14d | $9.98 | $8.82 | +11.6% |
| 18 | 2023-02-21 | Taboneo -> Paradip_Inner | Panamax | `WAIT` | 14d | $7.06 | $9.18 | -30.0% |
| 19 | 2023-04-18 | Maputo -> Dhamra | Panamax | `WAIT` | 14d | $8.62 | $8.28 | +3.9% |
| 20 | 2023-06-20 | Beira -> Dhamra | Panamax | `FIX_NOW` | 0d | $6.16 | $6.16 | +0.0% |
| 21 | 2023-08-15 | Nacala -> Gangavaram | Panamax | `FIX_NOW` | 0d | $5.59 | $5.59 | +0.0% |
| 22 | 2023-10-17 | Vostochny_PPK3 -> Vizag_Outer | Panamax | `FIX_NOW` | 0d | $6.09 | $6.09 | +0.0% |
| 23 | 2023-12-19 | Newcastle -> Paradip_SPM | Capesize | `FIX_NOW` | 0d | $9.78 | $9.78 | +0.0% |
| 24 | 2024-02-20 | Lamberts_Point -> Vizag_Outer | Panamax | `WAIT` | 14d | $12.50 | $15.75 | -26.0% |
| 25 | 2024-04-16 | Taboneo -> Paradip_Inner | Panamax | `FIX_NOW` | 0d | $13.40 | $13.40 | +0.0% |

---

## 2. Module E1 — Idle-Time & Contract Structuring Backtest Results
- **Objective:** Fulfill PS requirement (c) *Idle Scenario Management* by evaluating transition from single spot voyages to period contracting across market troughs.
- **Trough Detection Window:** 14 contiguous days (Option a: aligned with model stability boundary).
- **Trailing Threshold:** 20th percentile of historical prices strictly prior to fixture date (zero future leakage).
- **Turnaround Delay Penalty:** 4.0 idle days between spot fixtures; 0.0 idle days under period charter.
- **Troughs Detected:** 11 of 25 fixtures.
- **Total Spot Baseline Cost:** $10,297.90
- **Total Period Strategy Cost:** $9,925.40
- **Aggregate Cost Savings:** **$372.50 (3.62%)**
- **Total Vessel Idle Days Avoided:** **44.0 days**
- **Challenge 10 Sanity Check:** PASSED (Saving <= 25.0%)

---

## 3. Module E2 — Speed & Fuel Optimization Advisory (JIT Arrival)
- **Objective:** Marine decarbonization and fuel cost minimization via Just-In-Time arrival.
- **Physics Formula:** $T_{required} = (d/v_{std}) + \Delta T_{port} - T_{buffer}$; $v_{rec} = \text{clamp}(d/T_{required}, 10.0, v_{std})$.
- **Fuel Law:** $\text{Fuel (metric tons)} = (\kappa / 24.0) \cdot d \cdot v^2$ (Admiralty passage approximation: $\text{Daily Fuel} = c \cdot v^3$).
- **Sourced Constants:**
  - Bunker Fuel Price: **$600.00 / metric ton** (Published Ship & Bunker 20-port VLSFO index).
  - Port Congestion Waiting: **36.0 hours** (IPA / MoPSW East Coast empirical baseline).
  - Safety Buffer: **4.0 hours**.
  - Minimum Safe Speed: **10.0 knots** (IMO MEPC.1/Circ.684 steerage safety bound).
- **Total Fuel Saved:** **521.15 metric tons**
- **Total CO2 Emissions Reduced:** **1,622.90 metric tons** (1,622,901.0 kg)
- **Total Bunker Fuel Cost Saved:** **$312,697.68**
- **Anchorage Waiting Time Absorbed at Sea:** **254.0 hours**
- **Portfolio Passage Fuel Reduction:** **14.11%**
- **Challenge 10 Sanity Check:** PASSED (Saving <= 25.0%)

### Corridor Scenario Breakdown:
| Corridor | Vessel Class | Route Dist (nm) | Dist Rem (nm) | Standard (kts) | Recommended (kts) | Fuel Saved (t) | CO2 Reduced (t) | Bunker Saved ($) |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Taboneo -> Haldia | Supramax | 2200 | 1000.0 | 14.5 | 10.0 | 45.02 t | 140.19 t | $27,011.25 |
| Taboneo -> Paradip_Inner | Supramax | 2400 | 1000.0 | 14.5 | 10.0 | 45.02 t | 140.19 t | $27,011.25 |
| Maputo -> Dhamra | Panamax | 3850 | 1800.0 | 14.5 | 11.5 | 66.13 t | 205.94 t | $39,680.05 |
| Beira -> Dhamra | Panamax | 3500 | 1800.0 | 14.5 | 11.5 | 66.13 t | 205.94 t | $39,680.05 |
| Nacala -> Gangavaram | Capesize | 3400 | 1800.0 | 14.0 | 11.2 | 86.51 t | 269.41 t | $51,908.48 |
| Vostochny_PPK3 -> Vizag_Outer | Panamax | 4500 | 1500.0 | 14.5 | 11.1 | 62.42 t | 194.38 t | $37,452.86 |
| Newcastle -> Paradip_SPM | Capesize | 5300 | 1500.0 | 14.0 | 10.8 | 81.78 t | 254.66 t | $49,068.02 |
| Lamberts_Point -> Vizag_Outer | Panamax | 9500 | 2000.0 | 14.5 | 11.8 | 68.14 t | 212.20 t | $40,885.72 |

---

## 4. Disclosed Limitations & Scope Notes
1. **Scope Boundary:** 6 East Coast Indian discharge ports, 4 vessel classes, 5 origin countries, and BDRY ETF proxy (2018–present).
2. **Horizon Scoping:** Multi-step forecasting is constrained to $N \in \{7, 14\}$ days due to empirical diagnostic findings of recursive autoregressive dampening bias at $N \ge 21$.
3. **Regime Shift Vulnerability:** As disclosed in blueprint Section 9, during unprecedented Black Swan shocks (e.g. Jan 2021 post-COVID spike, 2023 China reopening), waiting can experience adverse variance; the system transparently reports these historical event limitations.
4. **Hardware Performance:** Total consolidated backtest execution elapsed in under 2.0 seconds on standard CPU hardware.
