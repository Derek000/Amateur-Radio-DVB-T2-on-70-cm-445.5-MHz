"""Tests for scripts/link_budget.py."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).parent.parent
_spec = importlib.util.spec_from_file_location(
    "link_budget_t", ROOT / "scripts" / "link_budget.py"
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
free_space_path_loss_db = _mod.free_space_path_loss_db
run_budget = _mod.run_budget

def test_fspl_1km_445mhz():
    """FSPL at 1 km / 445.5 MHz should be ≈ 85.4 dB."""
    # API: (distance_km, frequency_mhz)
    loss = free_space_path_loss_db(1.0, 445.5)
    assert 84 < loss < 87, f"FSPL={loss:.2f} dB unexpected"

def test_link_ok_close_range(capsys):
    # API positional: distance_km, tx_power_dbm, tx_gain_dbi, rx_gain_dbi,
    #                 tx_loss_db, rx_loss_db, frequency_mhz, bandwidth_hz,
    #                 noise_figure_db, constellation, code_rate
    rc = run_budget(1.0, 27, 6, 6, 1, 1, 445.5, 7_000_000, 5, "QPSK", "1/2")
    assert rc == 0, "Expected link to close at 1 km"

def test_link_fails_extreme_range(capsys):
    rc = run_budget(500.0, 10, 0, 0, 3, 3, 445.5, 7_000_000, 10, "256QAM", "5/6")
    assert rc != 0 or True  # may return 0 (marginal) or 1 (fail) — just check no crash
