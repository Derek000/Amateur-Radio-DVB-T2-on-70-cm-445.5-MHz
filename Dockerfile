FROM ghcr.io/gnuradio/gnuradio:3.10
RUN apt-get update && apt-get install -y git cmake g++ libboost-all-dev libvolk2-dev \
    soapysdr-tools soapysdr-module-lms7 limesuite libiio-utils gnuradio-dev python3-pip && \
    pip3 install pandas matplotlib && rm -rf /var/lib/apt/lists/*
# Build gr-dvbt2 and gr-dvbs2rx (example)
RUN git clone https://github.com/drmpeg/gr-dvbt2.git /opt/gr-dvbt2 && cd /opt/gr-dvbt2 && mkdir build && cd build && cmake .. && make -j$(nproc) && make install && ldconfig &&     git clone https://github.com/drmpeg/gr-dvbs2rx.git /opt/gr-dvbs2rx && cd /opt/gr-dvbs2rx && mkdir build && cd build && cmake .. && make -j$(nproc) && make install && ldconfig
WORKDIR /workspace
