#!/usr/bin/env python3
import argparse
from xml.etree import ElementTree as ET
from pathlib import Path

def find_conn(root, src, dst):
    for c in root.findall("connection"):
        s = c.find("source_block_id").text if c.find("source_block_id") is not None else ""
        d = c.find("sink_block_id").text if c.find("sink_block_id") is not None else ""
        if s==src and d==dst: return c
    return None

def add_epy(root, block_id, source_path, class_name, args):
    blk = ET.SubElement(root,"block")
    ET.SubElement(blk,"key").text="epy_block"
    p=ET.SubElement(blk,"param"); ET.SubElement(p,"key").text="id"; ET.SubElement(p,"value").text=block_id
    p=ET.SubElement(blk,"param"); ET.SubElement(p,"key").text="source"; ET.SubElement(p,"value").text=source_path
    p=ET.SubElement(blk,"param"); ET.SubElement(p,"key").text="class_name"; ET.SubElement(p,"value").text=class_name
    p=ET.SubElement(blk,"param"); ET.SubElement(p,"key").text="args"; ET.SubElement(p,"value").text=args

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("grc"); ap.add_argument("--insert", action="store_true"); ap.add_argument("--remove", action="store_true")
    ap.add_argument("--block-id", default="mer_logger"); ap.add_argument("--src", default="ofdm"); ap.add_argument("--dst", default="tx_bpf")
    ap.add_argument("--source-path", default="grc/blocks/mer_evm_logger.py"); ap.add_argument("--class-name", default="mer_evm_logger")
    ap.add_argument("--args", default='"metrics/tx_metrics.csv", 4096, "qpsk"')
    a=ap.parse_args()
    path=Path(a.grc); tree=ET.parse(path); root=tree.getroot()
    if a.insert:
        conn=find_conn(root,a.src,a.dst)
        if conn is None: raise SystemExit(f"No connection {a.src}->{a.dst}")
        root.remove(conn); add_epy(root,a.block_id,a.source_path,a.class_name,a.args)
        c1=ET.SubElement(root,"connection"); ET.SubElement(c1,"source_block_id").text=a.src; ET.SubElement(c1,"source_key").text="out"; ET.SubElement(c1,"sink_block_id").text=a.block_id; ET.SubElement(c1,"sink_key").text="in"
        c2=ET.SubElement(root,"connection"); ET.SubElement(c2,"source_block_id").text=a.block_id; ET.SubElement(c2,"source_key").text="out"; ET.SubElement(c2,"sink_block_id").text=a.dst; ET.SubElement(c2,"sink_key").text="in"
        tree.write(path, encoding="utf-8", xml_declaration=True); print("[OK] inserted"); return
    if a.remove:
        # remove connections involving block-id
        for c in list(root.findall("connection")):
            s=c.find("source_block_id").text if c.find("source_block_id") is not None else ""
            d=c.find("sink_block_id").text if c.find("sink_block_id") is not None else ""
            if s==a.block_id or d==a.block_id: root.remove(c)
        for b in list(root.findall("block")):
            kid=b.find("key").text if b.find("key") is not None else ""
            bid=None
            for p in b.findall("param"):
                if p.find("key").text=="id": bid=p.find("value").text
            if kid=="epy_block" and bid==a.block_id: root.remove(b); break
        if find_conn(root,a.src,a.dst) is None:
            c=ET.SubElement(root,"connection"); ET.SubElement(c,"source_block_id").text=a.src; ET.SubElement(c,"source_key").text="out"; ET.SubElement(c,"sink_block_id").text=a.dst; ET.SubElement(c,"sink_key").text="in"
        tree.write(path, encoding="utf-8", xml_declaration=True); print("[OK] removed"); return
    print("Use --insert or --remove")

if __name__=="__main__":
    main()
