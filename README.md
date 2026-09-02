# Intelligent Freight Forecasting & Chartering Decision Support System

A Chartering Decision Support System for SIH 2026, Problem Statement SIH26006 (Ministry of Steel): *"Development of an Intelligent Freight Forecasting Model for Optimized Vessel Chartering and Bulk Cargo Procurement from Overseas to East Coast of India."* Rather than a basic price-prediction tool, this platform consists of six integrated, explainable modules (Forecast Engine, Port-Matching Engine, Risk Radar, Decision Engine, Idle-Time & Contract Structuring, and Interaction Layer) producing quantified, backtested decision recommendations for dry bulk cargo shipments across key East Coast India ports.

## Setup

### 1. Environment Configuration
Copy the `.env.example` template to create your `.env` file in the root directory:
```bash
cp .env.example .env
```
Populate the environment variables in `.env` (e.g., `DATABASE_URL` for the Neon serverless PostgreSQL instance). Do not commit `.env` to version control.

### 2. Backend Virtual Environment
A dedicated Python virtual environment is maintained locally inside `backend/venv`.

**Activate on Windows (PowerShell):**
```powershell
.\backend\venv\Scripts\Activate.ps1
```

**Activate on Windows (CMD):**
```cmd
backend\venv\Scripts\activate.bat
```

**Activate on Linux / macOS:**
```bash
source backend/venv/bin/activate
```
