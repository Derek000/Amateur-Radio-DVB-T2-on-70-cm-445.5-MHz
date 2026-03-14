#!/usr/bin/env python3
"""Insert or remove the MER/EVM logger EPY block in a GRC flowgraph.

The block is spliced *between* two existing connected blocks, intercepting the
IQ stream for measurement without altering the signal path.

Usage
-----
    # Insert the logger between the 'ofdm' and 'tx_bpf' blocks:
    python3 scripts/inject_metrics_block.py grc/tx_dvbt2_445_5MHz.grc \\
        --insert \\
        --src ofdm --dst tx_bpf \\
        --args '"metrics/tx_metrics.csv", 4096, "qpsk"'

    # Remove it and restore the original direct connection:
    python3 scripts/inject_metrics_block.py grc/tx_dvbt2_445_5MHz.grc --remove
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional
from xml.etree import ElementTree as ET


# ---------------------------------------------------------------------------
# XML helpers
# ---------------------------------------------------------------------------

def _find_connection(
    root: ET.Element,
    src_id: str,
    dst_id: str,
) -> Optional[ET.Element]:
    """Return the connection element linking *src_id* → *dst_id*, or None."""
    for conn in root.findall("connection"):
        src_el = conn.find("source_block_id")
        dst_el = conn.find("sink_block_id")
        src = src_el.text if src_el is not None else ""
        dst = dst_el.text if dst_el is not None else ""
        if src == src_id and dst == dst_id:
            return conn
    return None


def _add_epy_block(
    root: ET.Element,
    block_id: str,
    source_path: str,
    class_name: str,
    args: str,
) -> None:
    """Append an ``epy_block`` element to *root*."""
    blk = ET.SubElement(root, "block")
    ET.SubElement(blk, "key").text = "epy_block"

    def _param(key: str, value: str) -> None:
        p = ET.SubElement(blk, "param")
        ET.SubElement(p, "key").text = key
        ET.SubElement(p, "value").text = value

    _param("id", block_id)
    _param("source", source_path)
    _param("class_name", class_name)
    _param("args", args)


def _add_connection(
    root: ET.Element,
    src_id: str,
    src_key: str,
    dst_id: str,
    dst_key: str,
) -> None:
    """Append a connection element to *root*."""
    conn = ET.SubElement(root, "connection")
    ET.SubElement(conn, "source_block_id").text = src_id
    ET.SubElement(conn, "source_key").text = src_key
    ET.SubElement(conn, "sink_block_id").text = dst_id
    ET.SubElement(conn, "sink_key").text = dst_key


# ---------------------------------------------------------------------------
# Insert / remove logic
# ---------------------------------------------------------------------------

def do_insert(
    root: ET.Element,
    src: str,
    dst: str,
    block_id: str,
    source_path: str,
    class_name: str,
    args: str,
) -> None:
    """Splice *block_id* between existing *src* and *dst* blocks."""
    conn = _find_connection(root, src, dst)
    if conn is None:
        raise SystemExit(
            f"[ERROR] No connection found from '{src}' to '{dst}'. "
            "Check --src and --dst block IDs."
        )

    # Remove the direct connection
    root.remove(conn)

    # Add the EPY block
    _add_epy_block(root, block_id, source_path, class_name, args)

    # Wire: src → logger → dst
    _add_connection(root, src, "out", block_id, "in")
    _add_connection(root, block_id, "out", dst, "in")

    print(f"[OK] Inserted '{block_id}' between '{src}' and '{dst}'.")


def do_remove(
    root: ET.Element,
    src: str,
    dst: str,
    block_id: str,
) -> None:
    """Remove *block_id* and restore the direct *src* → *dst* connection."""
    # Remove all connections that touch the logger block
    removed_conn = False
    for conn in list(root.findall("connection")):
        src_el = conn.find("source_block_id")
        dst_el = conn.find("sink_block_id")
        s = src_el.text if src_el is not None else ""
        d = dst_el.text if dst_el is not None else ""
        if s == block_id or d == block_id:
            root.remove(conn)
            removed_conn = True

    # Remove the EPY block itself
    removed_blk = False
    for blk in list(root.findall("block")):
        key_el = blk.find("key")
        if key_el is None or key_el.text != "epy_block":
            continue
        bid = None
        for p in blk.findall("param"):
            k = p.find("key")
            v = p.find("value")
            if k is not None and k.text == "id" and v is not None:
                bid = v.text
        if bid == block_id:
            root.remove(blk)
            removed_blk = True
            break

    if not removed_blk:
        print(
            f"[WARN] Block '{block_id}' was not found — it may already be removed.",
            file=sys.stderr,
        )

    # Restore direct connection only if it does not already exist
    if _find_connection(root, src, dst) is None:
        _add_connection(root, src, "out", dst, "in")

    print(f"[OK] Removed '{block_id}'; restored '{src}' → '{dst}' connection.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("grc", help="Path to the .grc flowgraph file to modify")

    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--insert", action="store_true", help="Insert the logger block")
    mode.add_argument("--remove", action="store_true", help="Remove the logger block")

    ap.add_argument("--block-id", default="mer_logger",
                    help="GRC block ID for the EPY logger (default: mer_logger)")
    ap.add_argument("--src", default="ofdm",
                    help="Source block ID (upstream neighbour, default: ofdm)")
    ap.add_argument("--dst", default="tx_bpf",
                    help="Sink block ID (downstream neighbour, default: tx_bpf)")
    ap.add_argument("--source-path", default="grc/blocks/mer_evm_logger.py",
                    help="Relative path to the EPY block Python source")
    ap.add_argument("--class-name", default="mer_evm_logger",
                    help="Python class name inside the EPY block source")
    ap.add_argument(
        "--args",
        default='"metrics/tx_metrics.csv", 4096, "qpsk"',
        help="Constructor arguments string, e.g. '\"metrics/tx_metrics.csv\", 4096, \"qpsk\"'",
    )
    return ap


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    path = Path(args.grc)

    if not path.exists():
        print(f"[ERROR] GRC file not found: {path}", file=sys.stderr)
        return 1

    try:
        tree = ET.parse(str(path))
    except ET.ParseError as exc:
        print(f"[ERROR] Failed to parse {path}: {exc}", file=sys.stderr)
        return 1

    root = tree.getroot()

    if args.insert:
        do_insert(
            root,
            src=args.src,
            dst=args.dst,
            block_id=args.block_id,
            source_path=args.source_path,
            class_name=args.class_name,
            args=args.args,
        )
    else:
        do_remove(root, src=args.src, dst=args.dst, block_id=args.block_id)

    tree.write(str(path), encoding="utf-8", xml_declaration=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
