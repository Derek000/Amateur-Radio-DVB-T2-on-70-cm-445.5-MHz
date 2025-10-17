#!/usr/bin/env python3
import argparse, socket, sys
TS_SIZE=188; SYNC=0x47
def parse(data, pid_filter, state):
    pkts=errs=ccerrs=0; i=0
    while i+TS_SIZE<=len(data):
        pkt=data[i:i+TS_SIZE]; i+=TS_SIZE; pkts+=1
        if pkt[0]!=SYNC: errs+=1; continue
        pid=((pkt[1]&0x1F)<<8)|pkt[2]; cc=pkt[3]&0x0F
        if pid_filter is not None and pid!=pid_filter: continue
        last=state.get(pid)
        if last is not None and ((last+1)&0x0F)!=cc: ccerrs+=1
        state[pid]=cc
    return pkts,errs,ccerrs
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--udp"); ap.add_argument("--pid",type=int,default=None); a=ap.parse_args()
    state={}
    if a.udp:
        host,port=a.udp.split(":"); port=int(port)
        sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); sock.bind((host,port)); sock.settimeout(1.0)
        total=(0,0,0)
        try:
            while True:
                try: data,_=sock.recvfrom(65535)
                except socket.timeout: continue
                p,e,c=parse(data,a.pid,state)
                total=(total[0]+p,total[1]+e,total[2]+c)
                if p: print(f"pkts={total[0]} sync_errs={total[1]} cc_errs={total[2]}",end="\r",flush=True)
        except KeyboardInterrupt: print("\nDone.")
    else:
        data=sys.stdin.buffer.read(); p,e,c=parse(data,a.pid,state); print(f"pkts={p} sync_errs={e} cc_errs={c}")
if __name__=="__main__": main()
