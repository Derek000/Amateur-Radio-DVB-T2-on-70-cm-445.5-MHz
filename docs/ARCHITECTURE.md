# Architecture

## TX (base profile)
UDP TS (ffmpeg H.264) → DVB‑T2 BB frame encoder → OFDM modulator (FFT 8k, GI 1/32, QPSK, CR 1/2) → digital BPF (~7 MHz) → Soapy/Lime or Pluto sink with RF‑BW ≈ 7.5 MHz and gain back‑off.

## RX
Soapy/Lime or Pluto source (RF‑BW ≈ 7.5 MHz) → digital BPF → DVB‑T2 demodulator → UDP TS → VLC/mpv or STB.

## Device Selection
Both **LimeSDR** and **PlutoSDR** blocks are present in the flowgraphs to ease switching. Disable the unused sink/source when running.
