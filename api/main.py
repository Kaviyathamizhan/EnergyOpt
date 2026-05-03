r"""
FastAPI Initializer
===================
Loads models, mounts routers, and runs the application.
"""
import os
import json
import joblib
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import warnings
from contextlib import asynccontextmanager

# Suppress harmless sklearn warnings about passing numpy arrays to models trained on DataFrames
warnings.filterwarnings("ignore", message="X does not have valid feature names")

from api.state import set_state
from api.routers import predict, anomaly, optimize

# Load core modules by file path to sidestep package namespace conflicts with uvicorn
import importlib.util as _ilu
def _load(name, rel_path):
    path = os.path.join(os.path.dirname(__file__), rel_path)
    spec = _ilu.spec_from_file_location(name, path)
    mod  = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_buffer_mod = _load("api_buffer", "core/buffer.py")
StateBuffer = _buffer_mod.StateBuffer

ROOT          = os.path.join(os.path.dirname(__file__), '..')
ARTIFACTS_DIR = os.path.join(ROOT, 'artifacts')
MODELS_DIR    = os.path.join(ARTIFACTS_DIR, 'models')
SCALERS_DIR   = os.path.join(ARTIFACTS_DIR, 'scalers')
CSV_PATH      = os.path.join(ROOT, 'data', 'processed', 'recent_history.csv')

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Load configuration and feature lists
    with open(os.path.join(SCALERS_DIR, 'feature_columns.json'), 'r') as f:
        feature_columns = json.load(f)
    set_state('feature_columns', feature_columns)

    with open(os.path.join(ARTIFACTS_DIR, 'metadata.json'), 'r') as f:
        meta = json.load(f)
        anomaly_config = meta.get('anomaly_detection', {})
    set_state('anomaly_config', anomaly_config)
    
    with open(os.path.join(SCALERS_DIR, 'anomaly_feature_columns.json'), 'r') as f:
        anomaly_feature_columns = json.load(f)
    set_state('anomaly_feature_columns', anomaly_feature_columns)

    # 2. Load Models
    set_state('model',      joblib.load(os.path.join(MODELS_DIR, 'forecast_winner.pkl')))
    set_state('q05_model',  joblib.load(os.path.join(MODELS_DIR, 'xgb_q05.pkl')))
    set_state('q95_model',  joblib.load(os.path.join(MODELS_DIR, 'xgb_q95.pkl')))
    set_state('iso_forest', joblib.load(os.path.join(MODELS_DIR, 'isolation_forest.pkl')))

    # 3. Load Scaler
    scaler = joblib.load(os.path.join(SCALERS_DIR, 'main_scaler.pkl'))
    set_state('scaler', scaler)

    assert scaler.n_features_in_ == len(feature_columns), (
        f"CRITICAL: Scaler expects {scaler.n_features_in_} features, "
        f"but feature_columns.json has {len(feature_columns)}."
    )

    # 4. Initialize Buffer
    buffer = StateBuffer(csv_path=CSV_PATH if os.path.exists(CSV_PATH) else None)
    set_state('buffer', buffer)

    yield

app = FastAPI(
    title="AI Energy Optimizer API",
    description="Inference engine for time-series forecasting, anomaly detection, and LP cost optimization.",
    version="2.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(predict.router)
app.include_router(anomaly.router)
app.include_router(optimize.router)

@app.get("/health")
def health_check():
    import api.state
    state = api.state.get_state()
    buf = state.get('buffer')
    return {
        "status": "ok",
        "buffer_ready": buf.is_ready if buf else False,
        "buffer_rows": len(buf) if buf else 0
    }

@app.get("/buffer/status")
def get_buffer_status():
    import api.state
    state = api.state.get_state()
    buf = state.get('buffer')
    if not buf:
         return {"error": "Buffer not initialized"}
    return {
        "is_ready": buf.is_ready,
        "total_readings": len(buf),
        "oldest_timestamp": buf._buffer[0]['datetime'].isoformat() if len(buf) > 0 else None,
        "newest_timestamp": buf._buffer[-1]['datetime'].isoformat() if len(buf) > 0 else None,
    }
