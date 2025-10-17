#!/usr/bin/env python3
import argparse
from xml.etree import ElementTree as ET
from pathlib import Path

def find_conn(root, src_id, dst_id):
    for c in root.findall("connection"):
        s = c.find("source_block_id").text if c.find("source_block_id") is not None else ""
        d = c.find("sink_block_id").text if c.find("sink_block_id") is not None else ""
        if s == src_id and d == dst_id:
            return c
    return None

def add_epy_block(root, block_id, source_path, class_name, args):
    pyblk = ET.SubElement(root, "block")
    ET.SubElement(pyblk, "key").text = "epy_block"
    p = ET.SubElement(pyblk, "param"); ET.SubElement(p, "key").text="id"; ET.SubElement(p, "value").text=block_id
    p = ET.SubElement(pyblk, "param"); ET.SubElement(p, "key").text="source"; ET.SubElement(p, "value").text=source_path
    p = ET.SubElement(pyblk, "param"); ET.SubElement(p, "key").text="class_name"; ET.SubElement(p, "value").text=class_name
    p = ET.SubElement(pyblk, "param"); ET.SubElement(p, "key").text="args"; ET.SubElement(p, "value").text=args

def main():
    ap = argparse.ArgumentParser(description="Inject/Remove MER/EVM EPY block in a .grc")
    ap.add_argument("grc")
    ap.add_argument("--insert", action="store_true", help="Insert block between --src and --dst")
    ap.add_argument("--remove", action="store_true", help="Remove block by --block-id and reconnect --src -> --dst")
    ap.add_argument("--block-id", default="mer_logger")
    ap.add_argument("--src", default="ofdm")
    ap.add_argument("--dst", default="tx_bpf")
    ap.add_argument("--source-path", default="grc/blocks/mer_evm_logger.py")
    ap.add_argument("--class-name", default="mer_evm_logger")
    ap.add_argument("--args", default='"metrics/tx_metrics.csv", 4096, "qpsk"')
    args = ap.parse_args()

    path = Path(args.grc)
    tree = ET.parse(path)
    root = tree.getroot()

    if args.insert:
        # Replace connection src->dst by src->block, block->dst
        conn = find_conn(root, args.src, args.dst)
        if conn is None:
            raise SystemExit(f"No connection {args.src} -> {args.dst} found")
        root.remove(conn)
        add_epy_block(root, args.block_id, args.source_path, args.class_name, args.args)
        c1 = ET.SubElement(root, "connection")
        ET.SubElement(c1, "source_block_id").text=args.src
        ET.SubElement(c1, "source_key").text="out"
        ET.SubElement(c1, "sink_block_id").text=args.block_id
        ET.SubElement(c1, "sink_key").text="in"
        c2 = ET.SubElement(root, "connection")
        ET.SubElement(c2, "source_block_id").text=args.block_id
        ET.SubElement(c2, "source_key").text="out"
        ET.SubElement(c2, "sink_block_id").text=args.dst
        ET.SubElement(c2, "sink_key").text="in"
        tree.write(path, encoding="utf-8", xml_declaration=True)
        print(f"[OK] Inserted {args.block_id} between {args.src} and {args.dst}")
        return

    if args.remove:
        # Remove the EPY block and reconnect src->dst
        # Remove connections involving block-id; add src->dst if missing
        to_delete = []
        for c in root.findall("connection"):
            s = c.find("source_block_id").text if c.find("source_block_id") is not None else ""
            d = c.find("sink_block_id").text if c.find("sink_block_id") is not None else ""
            if s == args.block_id or d == args.block_id:
                to_delete.append(c)
        for c in to_delete:
            root.remove(c)
        # Remove the block itself
        for b in root.findall("block"):
            kid = b.find("key").text if b.find("key") is not None else ""
            bid = None
            for p in b.findall("param"):
                if p.find("key").text == "id":
                    bid = p.find("value").text
            if kid == "epy_block" and bid == args.block_id:
                root.remove(b)
                break
        # Ensure src->dst exists
        if find_conn(root, args.src, args.dst) is None:
            c = ET.SubElement(root, "connection")
            ET.SubElement(c, "source_block_id").text=args.src
            ET.SubElement(c, "source_key").text="out"
            ET.SubElement(c, "sink_block_id").text=args.dst
            ET.SubElement(c, "sink_key").text="in"
        tree.write(path, encoding="utf-8", xml_declaration=True)
        print(f"[OK] Removed {args.block_id} and reconnected {args.src} -> {args.dst}")
        return

    print("Specify --insert or --remove")

if __name__ == "__main__":
    main()
