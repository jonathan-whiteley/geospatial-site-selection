#!/bin/bash
# Simplified Valhalla Init Script for Databricks
# Installs Valhalla routing engine with comprehensive error handling

set -e
exec > >(tee -a /tmp/valhalla-init-simple.log) 2>&1

echo "========================================="
echo "Valhalla Init Script - Starting"
echo "Date: $(date)"
echo "========================================="

# Check if already installed
if python3 -c "import valhalla" 2>/dev/null; then
    echo "✓ Valhalla already installed, exiting"
    exit 0
fi

# Install system dependencies
echo "Installing system dependencies..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq \
    cmake g++ git wget \
    libboost-all-dev \
    libcurl4-openssl-dev \
    libprotobuf-dev protobuf-compiler \
    liblz4-dev libsqlite3-dev \
    libspatialite-dev libgeos-dev \
    libluajit-5.1-dev python3-dev

echo "✓ Dependencies installed"

# Build Valhalla
echo "Building Valhalla 3.4.0..."
cd /tmp
rm -rf valhalla_build
mkdir -p valhalla_build
cd valhalla_build

wget -q https://github.com/valhalla/valhalla/archive/refs/tags/3.4.0.tar.gz
tar -xzf 3.4.0.tar.gz
cd valhalla-3.4.0

echo "Configuring..."
cmake -B build \
    -DCMAKE_BUILD_TYPE=Release \
    -DENABLE_PYTHON_BINDINGS=ON \
    -DCMAKE_CXX_FLAGS="-Wno-error" \
    -DENABLE_SERVICES=OFF \
    -DENABLE_HTTP=OFF

echo "Compiling (10-15 minutes)..."
cmake --build build -j$(nproc)

echo "Installing..."
cmake --install build

echo "Installing Python bindings..."
cd build/python
python3 -m pip install --quiet .

echo "Running ldconfig..."
ldconfig

# Verify installation
echo "Verifying installation..."
if python3 -c "import valhalla; print('Valhalla version:', valhalla.__version__ if hasattr(valhalla, '__version__') else 'installed')"; then
    echo "✓ Valhalla successfully installed!"
    exit 0
else
    echo "✗ Valhalla installation verification failed"
    exit 1
fi
