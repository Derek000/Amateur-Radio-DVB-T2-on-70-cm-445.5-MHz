# Spectral Purity Checklist
- **Calibrate**: Lime `LimeUtil --cal`; Pluto auto-cal on tune; prefer shared 10 MHz ref.
- **Digital BPF**: ~3.3 MHz cutoff at 4 Msps base rate (adjust with Fs).
- **Device RF‑BW**: ≈ 7.5 MHz; enable IQ/DC correction.
- **Back‑off**: keep shoulders ≤ −40 dBc; verify (RBW 10–30 kHz, span 20–30 MHz).
- **Troubleshoot**: high shoulders → steeper filter, lower gain; DC spur → LO offset + digital shift.
