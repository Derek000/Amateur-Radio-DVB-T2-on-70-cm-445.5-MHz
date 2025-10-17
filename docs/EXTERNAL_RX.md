# External DVB‑T2 Receiver (GPL‑3.0) – Optional

- Repo: https://github.com/Oleg-Malyutin/sdr_receiver_dvb_t2 (GPL‑3.0)
- Keep it external; do not copy source here (MIT project).

## Submodule
```bash
git submodule add https://github.com/Oleg-Malyutin/sdr_receiver_dvb_t2 extern/sdr_receiver_dvb_t2
git commit -m "Add optional DVB-T2 RX submodule (GPL-3.0, external)"
```

## Linux build (example)
```bash
sudo apt-get update && sudo apt-get install -y build-essential qtbase5-dev qtchooser qt5-qmake   libfftw3-dev libusb-1.0-0-dev libiio-dev
cd extern/sdr_receiver_dvb_t2 && qmake && make -j$(nproc)
```

## Windows quick start
Use their prebuilt `win_x64/` and README; install device drivers as required.

## Use with this repo
- Run our TX with metrics
- Run external RX (Pluto/SDRplay/Airspy)
- Watch TS continuity: `python3 scripts/ts_cc_monitor.py --udp 127.0.0.1:5010`
