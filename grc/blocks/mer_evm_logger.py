#!/usr/bin/env python3
from gnuradio import gr
import numpy as np, csv, os, time

def ref_points(constellation="qpsk"):
    c=constellation.lower()
    if c=="qpsk":
        ang=np.array([np.pi/4,3*np.pi/4,5*np.pi/4,7*np.pi/4]); return np.exp(1j*ang)
    if c=="16qam":
        a=np.array([-3,-1,1,3],float); grid=np.array([x+1j*y for x in a for y in a],np.complex64)
        grid/=np.sqrt(np.mean(np.abs(grid)**2)); return grid
    if c=="64qam":
        a=np.array([-7,-5,-3,-1,1,3,5,7],float); grid=np.array([x+1j*y for x in a for y in a],np.complex64)
        grid/=np.sqrt(np.mean(np.abs(grid)**2)); return grid
    raise ValueError("Unsupported constellation")

def hard_decide(s, ref):
    out=np.empty_like(s,dtype=np.complex64)
    blk=4096
    for i in range(0,len(s),blk):
        chunk=s[i:i+blk]
        d=np.abs(chunk[:,None]-ref[None,:])**2
        idx=np.argmin(d,axis=1)
        out[i:i+blk]=ref[idx]
    return out

class mer_evm_logger(gr.sync_block):
    def __init__(self, csv_path="metrics/tx_metrics.csv", window=4096, constellation="qpsk"):
        gr.sync_block.__init__(self, name="mer_evm_logger", in_sig=[np.complex64], out_sig=[np.complex64])
        self.csv_path=csv_path; self.window=max(256,int(window)); self.constellation=constellation.lower()
        self.ref=ref_points(self.constellation); self.buf=np.zeros(self.window,dtype=np.complex64); self.idx=0
        os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
        if not os.path.exists(self.csv_path):
            with open(self.csv_path,"w",newline="") as f:
                csv.writer(f).writerow(["ts_unix","samples","constellation","evm_pct","mer_db"])
    def work(self, ins, outs):
        x=ins[0]; y=outs[0]; y[:]=x; n=len(x); 
        if n==0: return 0
        start=0
        while start<n:
            take=min(self.window-self.idx, n-start)
            self.buf[self.idx:self.idx+take]=x[start:start+take]; self.idx+=take; start+=take
            if self.idx==self.window:
                s=self.buf; r=hard_decide(s,self.ref); err=s-r
                evm_rms=np.sqrt(np.mean(np.abs(err)**2)); ref_rms=np.sqrt(np.mean(np.abs(r)**2))
                evm_pct=100.0*evm_rms/(ref_rms+1e-12); mer_db=20.0*np.log10((ref_rms+1e-12)/(evm_rms+1e-12))
                with open(self.csv_path,"a",newline="") as f:
                    csv.writer(f).writerow([time.time(), self.window, self.constellation, f"{evm_pct:.3f}", f"{mer_db:.3f}"])
                self.idx=0
        return n
