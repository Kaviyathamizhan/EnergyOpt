# AI Energy Optimizer

## Problem Statement
The global demand for residential and commercial electricity is rising, resulting in grid instabilities during peak usage hours and inflated consumer pricing. Traditional systems lack predictive foresight and fail to proactively adapt to non-linear anomalies. 

This **AI Energy Optimizer** is an end-to-end Machine Learning intelligence platform designed to:
1. Predict near-term energy fluctuations with gradient boosting.
2. Mathematically optimize and shift loads from expensive peak hours to off-peak periods using Linear Programming.
3. Automatically intercept structural and statistical anomalies before grid destabilization.

---

## Architecture Overview
The architecture is a strictly decoupled, micro-service oriented stack guaranteeing scalability and stateless logic separation.

* **Frontend:** React + Vite. Features a pure dashboard layout plotting optimization savings, continuous session monitoring, and real-time visualization of machine decisions.
* **API Backend:** FastAPI mapping dedicated independent routes (`/predict`, `/anomaly`, `/optimize`) orchestrated by a `predict_full` unified wrapper.
* **AI Engine:** Pre-trained LightGBM, XGBoost, and Isolation Forest models seamlessly pickled. A fast purely-Python `deque`-based memory buffer traces topological lag parameters (up to T-168) cleanly in-memory without pandas overhead.

---

## Pipeline Workflow

The AI engine executes a sequential event cycle at ultra-low latency:
1. **Input:** The dashboard submits a single hourly vector instance.
2. **Predict:** An independent LightGBM ensemble instantly projects the point forecast, while two independent XGBoost Quantile variants map a 90% confidence uncertainty corridor.
3. **Anomaly:** The pipeline checks biological drift boundaries using a rolling 24-hour mean and intercepts topological distortions using an Isolation Forest.
4. **Optimization:** Highs solver evaluates a projected 48-hour horizon, calculating explicit constraints to forcibly migrate 20% of peak energy (16:00 to 21:00) backward into the night, returning an explicitly lower financial trajectory.

---

## Model Comparison

During the ML development lifecycle, different regressors were iteratively validated for accuracy and throughput prior to finalizing the system weights:

| Model Structure | Validation RMSE | MAE | Characteristics |
| :--- | :--- | :--- | :--- |
| **Naïve Baseline** | 0.9023 | 0.6517 | Predicts t-1 verbatim |
| **Linear Regression** | 0.5284 | 0.3809 | Inadequate non-linear handling |
| **Random Forest** | 0.4901 | 0.3540 | Heavy execution weight, slow |
| **XGBoost (Hist)** | 0.4705 | 0.3308 | Strong accuracy |
| **LightGBM (Final)** | **0.4660** | **0.3226** | **Fastest, lightest tree construction** |

## Anomaly Detection Performance
Instead of relying solely on generic boundaries, the system uses a dual-gate topology (Statistical Z-Score Gate AND Isolation Forest Boundary). 

* **Precision:** `0.88`
* **Recall:** `0.85`
* **F1 Score:** `0.865`

## Data Handling & Staleness (Note)
*The system mathematically initializes its warm-up buffer using historical readings (`data/processed/recent_history.csv`) mapped to previous dates.* 
*In a live production rollout, this initialization vector would simply be replaced by a live TCP/Kafka stream from dynamic smart meters, rendering the timestamps continually concurrent.*

---

## Execution Instructions

To deploy the production-ready instance locally:

### 1. Boot ML Backend (FastAPI)
```powershell
.\venv\Scripts\python.exe -m uvicorn api.main:app --port 8000
```
*API docs auto-generate securely at [http://127.0.0.1:8000/docs]*

### 2. Boot React Dashboard (Vite)
```powershell
cd frontend
npm run dev
```
*Navigate your browser to [http://localhost:5173] to interact with the Decision Interface.*
