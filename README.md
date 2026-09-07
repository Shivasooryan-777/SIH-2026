# Intelligent Freight Forecasting & Vessel Chartering Decision Support System

A Chartering Decision Support System developed for **Smart India Hackathon (SIH) 2026**, Problem Statement **SIH26006** (Ministry of Steel): *"Development of an Intelligent Freight Forecasting Model for Optimized Vessel Chartering and Bulk Cargo Procurement from Overseas to East Coast of India."* Rather than operating as a simple price-prediction tool, this platform is an end-to-end decision cockpit integrating six explainable, backtested modules (Forecast Engine with quantile bands, dynamic Port-Matching Engine, Risk Radar, Decision Engine evaluating `FIX NOW` vs. `WAIT`, Idle-Time & Speed/Fuel Structuring, and an Always-On Market Interaction Layer) to deliver quantified, auditable chartering recommendations for bulk cargo imports into East Coast Indian ports.

---

## Prerequisites

Before setting up the project, ensure you have the following installed:

* **Python:** Version `3.11`, `3.12`, or `3.13`
* **Node.js:** Version `18.x` or `20.x` LTS (with `npm`)
* **Database:** A free-tier [Neon Serverless PostgreSQL](https://neon.tech) database instance
* **Git:** Version `2.30+`

---

## Setup Steps

### 1. Clone the Repository
```bash
git clone <repository-url>
cd sih
```

### 2. Set Up the Backend Virtual Environment
Create a dedicated virtual environment inside `backend/venv`:

```bash
python -m venv backend/venv
```

Activate the virtual environment:
* **Windows (PowerShell):**
  ```powershell
  .\backend\venv\Scripts\Activate.ps1
  ```
* **Windows (Command Prompt):**
  ```cmd
  backend\venv\Scripts\activate.bat
  ```
* **Linux / macOS:**
  ```bash
  source backend/venv/bin/activate
  ```

Install all backend and machine learning dependencies:
```bash
pip install -r backend/requirements.txt -r ml/requirements.txt
```

### 3. Configure Environment Variables
Copy the `.env.example` template to create your local `.env` file in the project root:

```bash
cp .env.example .env
```

Open `.env` and set your Neon PostgreSQL connection string:
```env
DATABASE_URL=postgresql://<user>:<password>@<ep-id>.neon.tech/<dbname>?sslmode=require
```
*(Note: `.env` is strictly excluded in `.gitignore` and must never be committed).*

### 4. Initialize Database Schema & Seed Reference Data
Run the idempotent migration and reference data loader to create all 15 tables and populate master ports, vessel types, routes, and historical risk events:

```bash
python -m backend.database.migrate
python -m backend.database.seed_reference_data
```

### 5. Install Frontend Dependencies
Navigate into the `frontend` directory and install the Node packages:

```bash
cd frontend
npm install
cd ..
```

---

## How to Run

### 1. Start the Backend Development Server
With your virtual environment activated from the project root (`d:\sih`):

```bash
uvicorn backend.app.main:app --reload --port 8000
```
* **API Base URL:** `http://localhost:8000`
* **Interactive Swagger Documentation:** `http://localhost:8000/docs`

### 2. Start the Frontend Development Server
In a separate terminal, start the Vite client:

```bash
cd frontend
npm run dev
```
* **Decision Cockpit UI:** `http://localhost:5173`

### 3. Run the Automated Test Suite
To verify the entire backend integration, execute `pytest` across all 12 test suites:

```bash
pytest backend/tests -v
```

---

## Prototype Status & Disclosed Limitations

This system is an evaluated prototype developed for SIH 2026:

* **Freight Data Scope (No Fabricated Multipliers):** Real-world Baltic Exchange freight indices (e.g., BDI, BPI, BSI) reside behind proprietary commercial paywalls. In strict accordance with project credibility guidelines, this prototype uses the publicly traded **Breakwave Dry Bulk Shipping ETF (`BDRY`)** via Yahoo Finance as an open, verifiable proxy series. Artificial scalar multipliers ($22k/$15k/$12.5k) are strictly avoided.
* **Geographic & Vessel Scope:** The system models 6 East Coast Indian ports (Paradip, Vizag, Gangavaram, Gopalpur, Dhamra, Sagar-Sandheads/Haldia), 4 bulk carrier classes (Handysize, Supramax, Panamax, Capesize), and 5 overseas origin countries (Australia, US, Mozambique, Russia, Indonesia).
* **Technical Blueprint & Amendments:** For complete mathematical formulas (Expected Value of Waiting, Admiralty coefficient fuel formulas), data schemas, and backtest logs, refer to [docs/blueprint.md](docs/blueprint.md).
