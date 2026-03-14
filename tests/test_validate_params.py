"""Tests for scripts/validate_params.py."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).parent.parent
_spec = importlib.util.spec_from_file_location(
    "validate_params_t", ROOT / "scripts" / "validate_params.py"
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
Validator = _mod.Validator

BASE = {
    "rf_frequency_hz": 445_500_000, "channel_bandwidth_hz": 7_000_000,
    "constellation": "QPSK", "code_rate": "1/2",
    "fft_size": 8192, "guard_interval": "1/32", "pilot_pattern": "PP7",
    "plp_count": 1,
    "device": {
        "tx": {"sample_rate": 8_000_000, "gain_db": -6,  "rf_bw_hz": 7_500_000},
        "rx": {"sample_rate": 8_000_000, "gain_db": 35, "rf_bw_hz": 7_500_000},
    },
    "udp_ts_in":  {"host": "127.0.0.1", "port": 5004},
    "udp_ts_out": {"host": "127.0.0.1", "port": 5006},
}

def _v(params):
    v = Validator(); v.validate(params); return v

def test_valid_baseline():
    assert _v(BASE).errors == []

def test_invalid_bandwidth():
    assert _v({**BASE, "channel_bandwidth_hz": 3_000_000}).errors

def test_invalid_constellation():
    assert _v({**BASE, "constellation": "1024QAM"}).errors

def test_invalid_fft_size():
    assert _v({**BASE, "fft_size": 999}).errors

def test_sample_rate_below_nyquist():
    p = dict(BASE)
    p["device"] = {"tx": {"sample_rate": 1_000_000, "gain_db":-6, "rf_bw_hz":7_500_000},
                   "rx": {"sample_rate": 8_000_000, "gain_db":35, "rf_bw_hz":7_500_000}}
    assert any("sample_rate" in e for e in _v(p).errors)
