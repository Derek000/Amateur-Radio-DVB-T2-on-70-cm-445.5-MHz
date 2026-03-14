#!/usr/bin/env python3
"""Patch GRC flowgraph variable blocks from params.yaml.

Reads ``params.yaml`` (or any YAML file) and updates matching ``variable``
blocks plus ``soapy_sink`` / ``soapy_source`` / ``iio_pluto_sink`` /
``iio_pluto_source`` block parameters in one or more ``.grc`` files.

Usage
-----
    python3 scripts/patch_grc_from_params.py params.yaml grc/*.grc

Exit codes
----------
0   One or more files were patched (or ``--check-only`` found no drift).
1   Fatal error (bad file path, invalid YAML, XML parse failure).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree as ET

import yaml

# ---------------------------------------------------------------------------
# YAML key → GRC variable-block ID mapping
# ---------------------------------------------------------------------------
VARIABLE_MAP: Dict[str, str] = {
    "rf_frequency_hz": "rf_freq",
    "channel_bandwidth_hz": "chan_bw",
}
SAMP_RATE_VAR = "samp_rate"


# ---------------------------------------------------------------------------
# Low-level GRC helpers
# ---------------------------------------------------------------------------

def _get_param_value(block: ET.Element, key: str) -> Optional[str]:
    """Return the text content of the <value> element for *key*, or None."""
    for p in block.findall("param"):
        k = p.find("key")
        v = p.find("value")
        if k is not None and k.text == key and v is not None:
            return v.text
    return None


def _set_param_value(block: ET.Element, key: str, value: Any) -> bool:
    """Set the <value> element for *key* in *block*.

    Returns True when a change was made, False when the param was not found.
    """
    for p in block.findall("param"):
        k = p.find("key")
        v = p.find("value")
        if k is not None and k.text == key and v is not None:
            if v.text != str(value):
                v.text = str(value)
                return True
            return False  # value already correct — no change
    return False


def _block_id(block: ET.Element) -> Optional[str]:
    """Return the ``id`` param value for *block*, or None."""
    return _get_param_value(block, "id")


# ---------------------------------------------------------------------------
# Per-file patcher
# ---------------------------------------------------------------------------

def update_grc(path: Path, params: Dict[str, Any], check_only: bool = False) -> bool:
    """Apply *params* to the GRC file at *path*.

    Parameters
    ----------
    path:
        Path to a ``.grc`` XML file.
    params:
        Parsed contents of ``params.yaml``.
    check_only:
        When True, detect drift but do not write changes.

    Returns
    -------
    bool
        True if changes were made (or detected in check-only mode).
    """
    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        print(f"[ERROR] Cannot parse {path}: {exc}", file=sys.stderr)
        sys.exit(1)

    root = tree.getroot()
    changed = False

    for blk in root.findall("block"):
        block_key = blk.find("key")
        if block_key is None:
            continue
        key_text = block_key.text or ""
        block_id_val = _block_id(blk)

        # -- variable blocks --------------------------------------------------
        if key_text == "variable" and block_id_val:
            # YAML-mapped variables (rf_freq, chan_bw …)
            for yaml_key, var_id in VARIABLE_MAP.items():
                if block_id_val == var_id and yaml_key in params:
                    changed |= _set_param_value(blk, "value", params[yaml_key])

            # Sample rate: prefer TX, fall back to RX
            if block_id_val == SAMP_RATE_VAR:
                dev = params.get("device", {})
                sr = (
                    dev.get("tx", {}).get("sample_rate")
                    or dev.get("rx", {}).get("sample_rate")
                )
                if sr is not None:
                    changed |= _set_param_value(blk, "value", sr)

        # -- SoapySDR sink/source ---------------------------------------------
        elif key_text in ("soapy_sink", "soapy_source"):
            side = "tx" if key_text.endswith("sink") else "rx"
            profile = params.get("device", {}).get(side, {})
            if "gain_db" in profile:
                changed |= _set_param_value(blk, "gain", profile["gain_db"])
            if "rf_bw_hz" in profile:
                changed |= _set_param_value(blk, "bandwidth", profile["rf_bw_hz"])

        # -- PlutoSDR (libiio) sink/source ------------------------------------
        elif key_text in ("iio_pluto_sink", "iio_pluto_source"):
            side = "tx" if key_text.endswith("sink") else "rx"
            profile = params.get("device", {}).get(side, {})
            if "gain_db" in profile:
                changed |= _set_param_value(blk, "rf_gain", profile["gain_db"])
            if "rf_bw_hz" in profile:
                changed |= _set_param_value(blk, "bw", profile["rf_bw_hz"])

    if changed and not check_only:
        tree.write(str(path), encoding="utf-8", xml_declaration=True)

    return changed


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("params", help="Path to params.yaml")
    ap.add_argument("grc", nargs="+", help="One or more .grc flowgraph files to patch")
    ap.add_argument(
        "--check-only",
        action="store_true",
        help="Report drift without writing any files (exits 1 if drift found)",
    )
    return ap


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    # Load YAML
    params_path = Path(args.params)
    if not params_path.exists():
        print(f"[ERROR] params file not found: {params_path}", file=sys.stderr)
        return 1
    try:
        with params_path.open("r", encoding="utf-8") as fh:
            params = yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        print(f"[ERROR] YAML parse error in {params_path}: {exc}", file=sys.stderr)
        return 1
    if not isinstance(params, dict):
        print(f"[ERROR] {params_path} must contain a YAML mapping.", file=sys.stderr)
        return 1

    any_changed = False
    any_missing = False

    for grc_str in args.grc:
        grc_path = Path(grc_str)
        if not grc_path.exists():
            print(f"[WARN] GRC file not found, skipping: {grc_path}", file=sys.stderr)
            any_missing = True
            continue

        changed = update_grc(grc_path, params, check_only=args.check_only)

        if changed:
            any_changed = True
            verb = "drift detected" if args.check_only else "patched"
            print(f"[OK]   {verb}: {grc_path}")
        else:
            print(f"[INFO] no changes needed: {grc_path}")

    if args.check_only and any_changed:
        print(
            "\n[FAIL] GRC files are out of sync with params.yaml. "
            "Run without --check-only to patch them.",
            file=sys.stderr,
        )
        return 1

    if any_missing:
        return 1  # warn caller that some files were skipped

    return 0


if __name__ == "__main__":
    sys.exit(main())
