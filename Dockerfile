# ── Stage 1: build gr-dvbt2 and gr-dvbs2rx ───────────────────────────────────
FROM ghcr.io/gnuradio/gnuradio:3.10 AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        git cmake g++ ninja-build \
        libboost-all-dev \
        libvolk-dev \
        libspdlog-dev \
        libfmt-dev \
        gnuradio-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Build gr-dvbt2
RUN git clone --depth 1 https://github.com/drmpeg/gr-dvbt2.git gr-dvbt2 \
    && cmake -S gr-dvbt2 -B gr-dvbt2/build -GNinja \
    && cmake --build gr-dvbt2/build -j"$(nproc)" \
    && cmake --install gr-dvbt2/build

# Build gr-dvbs2rx (optional GRC-only RX variant)
RUN git clone --depth 1 https://github.com/drmpeg/gr-dvbs2rx.git gr-dvbs2rx \
    && cmake -S gr-dvbs2rx -B gr-dvbs2rx/build -GNinja \
    && cmake --build gr-dvbs2rx/build -j"$(nproc)" \
    && cmake --install gr-dvbs2rx/build

# ── Stage 2: runtime image ────────────────────────────────────────────────────
FROM ghcr.io/gnuradio/gnuradio:3.10

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
        soapysdr-tools \
        soapysdr-module-lms7 \
        limesuite \
        libiio-utils \
        ffmpeg \
        python3-pip \
    && pip3 install --no-cache-dir pyyaml numpy pandas matplotlib \
    && rm -rf /var/lib/apt/lists/*

# Copy OOT modules from builder
COPY --from=builder /usr/local/lib/python3/dist-packages/ \
                    /usr/local/lib/python3/dist-packages/
COPY --from=builder /usr/local/lib/ /usr/local/lib/
COPY --from=builder /usr/local/share/gnuradio/ /usr/local/share/gnuradio/
RUN ldconfig

# Run as non-root user
RUN useradd -m -u 1000 -s /bin/bash hamradio
USER hamradio
WORKDIR /workspace

# Copy project
COPY --chown=hamradio:hamradio . .

# Validate params on container start (non-fatal)
RUN python3 scripts/validate_params.py || true

ENTRYPOINT ["/bin/bash"]
