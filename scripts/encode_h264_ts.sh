#!/usr/bin/env bash
set -euo pipefail
IN="${1:-sample.mp4}"
HOST="127.0.0.1"
PORT="5004"
ffmpeg -re -i "$IN" -c:v libx264 -preset veryfast -pix_fmt yuv420p -b:v 1000k -maxrate 1500k -bufsize 2000k   -g 50 -keyint_min 50 -x264-params "nal-hrd=cbr:force-cfr=1"   -c:a aac -b:a 128k -ar 48000 -ac 2   -f mpegts "udp://$HOST:$PORT?pkt_size=1316"
