"""Tests for scripts/ts_cc_monitor.py."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).parent.parent
_spec = importlib.util.spec_from_file_location(
    "ts_cc_monitor_t", ROOT / "scripts" / "ts_cc_monitor.py"
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
TsStats = _mod.TsStats
NULL_PID = 0x1FFF

def _pkt(pid: int, cc: int) -> bytes:
    """Build a minimal 188-byte TS packet with payload AFC."""
    afc = 0b01
    return bytes([0x47, (pid >> 8) & 0x1F, pid & 0xFF, (afc << 4) | (cc & 0x0F)]) + b"\x00" * 184

def test_clean_stream_no_errors():
    s = TsStats()
    data = b"".join(_pkt(0x100, cc) for cc in range(16)) * 2
    s.feed(data)
    assert s.sync_errors == 0
    assert s.cc_errors == 0

def test_cc_discontinuity_detected():
    s = TsStats()
    s.feed(_pkt(0x100, 0))   # CC=0
    s.feed(_pkt(0x100, 5))   # expected 1, got 5
    assert s.cc_errors == 1

def test_sync_byte_error():
    s = TsStats()
    s.feed(b"\x00" * 188)
    assert s.sync_errors == 1

def test_null_packets_skipped():
    """NULL PID (0x1FFF) packets should not generate CC errors."""
    s = TsStats()
    for _ in range(4):
        s.feed(_pkt(NULL_PID, 0))
    assert s.cc_errors == 0

def test_pid_filter():
    s = TsStats()
    s.feed(_pkt(0x100, 0) + _pkt(0x200, 0))
    s.feed(_pkt(0x100, 5) + _pkt(0x200, 1), pid_filter=0x100)
    # Only PID 0x100 is watched; it has a CC jump, 0x200 is filtered
    assert s.cc_errors >= 1
