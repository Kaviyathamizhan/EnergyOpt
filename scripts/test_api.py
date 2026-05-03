"""
Phase 6.5 — Final Backend Validation
=====================================
Tests: edge cases, buffer stability, optimizer sanity
"""
import urllib.request
import urllib.error
import json
import sys

BASE_URL = "http://127.0.0.1:8000"

PASS = "[PASS]"
FAIL = "[FAIL]"
SKIP = "[SKIP]"

def _request(method, endpoint, payload=None):
    url  = f"{BASE_URL}{endpoint}"
    data = None
    headers = {}
    if payload is not None:
        data    = json.dumps(payload).encode('utf-8')
        headers = {'Content-Type': 'application/json'}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            body = json.loads(body)
        except Exception:
            pass
        return e.code, body


failures = []

def check(name, condition, msg=""):
    if condition:
        print(f"  {PASS} {name}")
    else:
        print(f"  {FAIL} {name}  {msg}")
        failures.append(name)


# ── 1. Health ────────────────────────────────────────────────────────────────
print("\n=== 1. Health Check ===")
status, data = _request("GET", "/health")
check("HTTP 200",                status == 200)
check("status == ok",            data.get('status') == 'ok')
check("buffer_ready == True",    data.get('buffer_ready') is True)
check("buffer_rows >= 169",      data.get('buffer_rows', 0) >= 169)


# ── 2. Edge Cases ────────────────────────────────────────────────────────────
print("\n=== 2. Edge Case Inputs ===")

# 2a. Near-zero
status, data = _request("POST", "/predict", {
    "datetime": "2023-06-01T08:00:00", "consumption": 0.01, "run_optimizer": False
})
check("Near-zero: no crash (200)", status == 200)
check("Near-zero: is_anomaly=False", data.get('anomaly', {}).get('flag') is False)

# 2b. Extreme spike
status, data = _request("POST", "/predict", {
    "datetime": "2023-06-01T09:00:00", "consumption": 50.0, "run_optimizer": False
})
check("Extreme spike: no crash (200)", status == 200)
check("Extreme spike: anomaly flagged", data.get('anomaly', {}).get('flag') is True)
check("Extreme spike: severity == high", data.get('anomaly', {}).get('severity') == 'high')

# 2c. Out-of-range (>100 rejected by Pydantic le=100)
status, data = _request("POST", "/predict", {
    "datetime": "2023-06-01T10:00:00", "consumption": 999.0, "run_optimizer": False
})
check("Out-of-range (999): returns 422", status == 422,
      f"got status={status}")

# 2d. Negative consumption (rejected by ge=0)
status, data = _request("POST", "/predict", {
    "datetime": "2023-06-01T11:00:00", "consumption": -5.0, "run_optimizer": False
})
check("Negative consumption: returns 422", status == 422,
      f"got status={status}")

# 2e. Bad datetime
status, data = _request("POST", "/predict", {
    "datetime": "not-a-date", "consumption": 1.0, "run_optimizer": False
})
check("Invalid datetime: returns 422", status == 422,
      f"got status={status}")


# ── 3. Buffer Stability ──────────────────────────────────────────────────────
print("\n=== 3. Buffer Stability (5 sequential reads) ===")
prev_forecast = None
prev_buffer   = None

for i in range(5):
    hour = 12 + i
    status, data = _request("POST", "/predict", {
        "datetime": f"2023-06-15T{hour:02d}:00:00",
        "consumption": round(1.0 + i * 0.1, 2),
        "run_optimizer": False
    })
    buf_rows = data.get('metadata', {}).get('buffer_rows', 0)
    forecast = data.get('forecast')

    check(f"  iter {i+1}: no crash", status == 200)
    check(f"  iter {i+1}: buffer rows > 0", buf_rows > 0)
    if prev_buffer is not None:
        check(f"  iter {i+1}: buffer grew by 1", buf_rows == prev_buffer + 1 or buf_rows == 200,
              f"prev={prev_buffer} now={buf_rows}")
    prev_forecast = forecast
    prev_buffer   = buf_rows


# ── 4. Optimizer Sanity ──────────────────────────────────────────────────────
print("\n=== 4. Optimizer Sanity Checks ===")
status, data = _request("POST", "/predict", {
    "datetime": "2023-06-01T14:00:00", "consumption": 1.5, "run_optimizer": True
})
check("Status 200", status == 200)

opt = data.get('optimization')
if opt is None:
    print(f"  {SKIP} Optimization block is None (buffer or model not ready)")
else:
    orig_profile = opt.get('original_profile', [])
    opt_profile  = opt.get('optimized_profile', [])

    check("Total energy conserved",
          abs(sum(orig_profile) - sum(opt_profile)) < 0.01,
          f"orig_sum={sum(orig_profile):.3f} opt_sum={sum(opt_profile):.3f}")
    check("No negative allocations",
          all(v >= 0 for v in opt_profile),
          str([v for v in opt_profile if v < 0]))
    check("Optimized cost <= original cost",
          opt.get('optimized_cost', 9999) <= opt.get('original_cost', 0) + 0.01,
          f"orig={opt['original_cost']} opt={opt['optimized_cost']}")
    check("Savings >= 0",
          opt.get('savings', -1) >= 0)


# ── 5. Standardised Response Schema ─────────────────────────────────────────
print("\n=== 5. Standardised Response Schema ===")
status, data = _request("POST", "/predict", {
    "datetime": "2023-06-01T15:00:00", "consumption": 1.2, "run_optimizer": True
})
check("Has 'forecast'",            'forecast' in data)
check("Has 'confidence_interval'", 'confidence_interval' in data)
check("CI has lower + upper",
      'lower' in data.get('confidence_interval', {}) and 'upper' in data.get('confidence_interval', {}))
check("Has 'anomaly'",             'anomaly' in data)
check("  anomaly.flag is bool",    isinstance(data.get('anomaly', {}).get('flag'), bool))
check("  anomaly.severity str",    data.get('anomaly', {}).get('severity') in ('low', 'medium', 'high'))
check("Has 'optimization'",        'optimization' in data)
if data.get('optimization'):
    check("  opt has original_cost",  'original_cost' in data['optimization'])
    check("  opt has optimized_cost", 'optimized_cost' in data['optimization'])
    check("  opt has savings",        'savings' in data['optimization'])


# ── SUMMARY ──────────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
if failures:
    print(f"[RESULT] {len(failures)} TEST(S) FAILED:")
    for f in failures:
        print(f"   - {f}")
    sys.exit(1)
else:
    print("[RESULT] ALL PHASE 6.5 VALIDATION TESTS PASSED")
    print("         Backend is ready for frontend integration.")
print('='*50)
