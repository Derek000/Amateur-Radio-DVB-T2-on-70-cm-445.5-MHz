# Spectral Purity Checklist

See also the in‑repo README quick notes.

- **Calibrate**: Lime `LimeUtil --cal`; Pluto auto‑cal upon tune. Use a shared 10 MHz ref if available.
- **Digital BPF**: ~3.3 MHz low‑pass at 4 Msps base rate (adjust if you change Fs).
- **Device RF‑BW**: ≈ 7.5 MHz to confine skirts; enable IQ/DC correction.
- **Back‑off**: keep shoulders ≤ −40 dBc. Verify on a spectrum analyser, RBW 10–30 kHz, span 20–30 MHz.
- **Troubleshoot**: high shoulders → increase filter order, reduce gain, check PA linearity; DC spur → LO offset + digital shift.
