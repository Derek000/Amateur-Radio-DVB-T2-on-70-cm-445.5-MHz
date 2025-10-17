# Architecture

## TX
UDP TS (ffmpeg H.264) → DVB‑T2 BB frame encoder → OFDM mod (FFT 8k, GI 1/32, QPSK, CR 1/2) → TX BPF (~7 MHz) → Lime/Pluto sink (RF‑BW ≈ 7.5 MHz; gain back‑off).

## RX
Lime/Pluto source (RF‑BW ≈ 7.5 MHz) → RX BPF → DVB‑T2 demod → UDP TS → VLC/STB.

## Device selection
Both device blocks are present; disable the unused one when running.
