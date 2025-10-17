#!/usr/bin/env bash
set -euo pipefail
if [ ! -d "extern/sdr_receiver_dvb_t2" ]; then
  echo "Submodule not found. Add it with:"
  echo "  git submodule add https://github.com/Oleg-Malyutin/sdr_receiver_dvb_t2 extern/sdr_receiver_dvb_t2"
  exit 1
fi
echo "Refer to extern/sdr_receiver_dvb_t2 README for build instructions (Qt/FFTW/libiio/libusb)."
