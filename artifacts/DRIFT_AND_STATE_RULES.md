# System State & Version Control Fixes

This documentation outlines the critical systemic rules enacted on this setup to bridge the separation of Colab (Training) and Local (FastAPI). Adherence to these constraints prevents temporal scaling bugs, anomaly blindspots, and model mismatch.

### 1. Artifact Management (Metadata Linker)
Instead of relying on strict path trees (`v1/`), all artifacts are placed in their respective base folders:
- `artifacts/models/xgb.pkl`
- `artifacts/scalers/scaler.pkl`

**FastAPI Runtime Rule:** The API uses a central manifest file (`artifacts/metadata.json`) at startup to explicitly locate which model matches which scaler. Under no circumstance should a developer update `metadata.json` without verifying the parity of both elements.

### 2. Recent History Buffer
The FastAPI service simulates continuous real-time execution via an in-memory Pandas buffer tracking the last 168 hours.
**Data Flow Rule:**
- **Bootstrap:** On server startup, the API initializes its buffer by loading local `data/processed/recent_history.csv` (provided during training).
- **Runtime Updates:** As new readings or predictions come into the API, this in-memory buffer dynamically slides forward, generating seamless lag/rolling features on the fly.

### 3. Anomaly Context Window
The Anomaly Detection endpoint uses a 24-hour mean and standard deviation.
**Rule:** The API natively maintains this 24-hour internal memory cache from the global history buffer. It strictly receives a single input or a small batch input without forcing the client/React frontend to transmit 24 historic readings on every POST request.
