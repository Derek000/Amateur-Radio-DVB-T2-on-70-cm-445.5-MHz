#!/usr/bin/env bash
# encode_h264_ts.sh — Encode a video file to H.264/AAC MPEG-TS and send via UDP.
#
# The output is a CBR-constrained MPEG-TS stream suitable for DVB-T2 input.
# Bitrates are chosen to stay well within a 7 MHz / QPSK CR-1/2 channel
# (~3.8 Mbit/s useful payload).
#
# Usage:
#   ./scripts/encode_h264_ts.sh [INPUT] [HOST] [PORT]
#
# Defaults:
#   INPUT = sample.mp4
#   HOST  = 127.0.0.1
#   PORT  = 5004

set -euo pipefail

# ---------------------------------------------------------------------------
# Arguments
# ---------------------------------------------------------------------------
INPUT="${1:-sample.mp4}"
HOST="${2:-127.0.0.1}"
PORT="${3:-5004}"

# ---------------------------------------------------------------------------
# Dependency check
# ---------------------------------------------------------------------------
if ! command -v ffmpeg &>/dev/null; then
    echo "[ERROR] ffmpeg not found. Install it with:"
    echo "  sudo apt-get install ffmpeg"
    exit 1
fi

if [[ ! -f "$INPUT" ]]; then
    echo "[ERROR] Input file not found: $INPUT"
    exit 1
fi

echo "[INFO] Source   : $INPUT"
echo "[INFO] Sink     : udp://$HOST:$PORT"
echo "[INFO] Video    : H.264 CBR 1000 kbit/s (max 1500), yuv420p, 50fps key-int"
echo "[INFO] Audio    : AAC 128 kbit/s 48 kHz stereo"
echo "[INFO] Starting — press Ctrl-C to stop."
echo ""

ffmpeg -re -i "$INPUT" \
    -c:v libx264 \
    -preset veryfast \
    -pix_fmt yuv420p \
    -b:v 1000k \
    -maxrate 1500k \
    -bufsize 2000k \
    -g 50 \
    -keyint_min 50 \
    -x264-params "nal-hrd=cbr:force-cfr=1" \
    -c:a aac \
    -b:a 128k \
    -ar 48000 \
    -ac 2 \
    -f mpegts \
    "udp://$HOST:$PORT?pkt_size=1316"
