#!/bin/bash
# OSRM Init Script for Databricks Cluster
# Installs OSRM routing engine - MUCH easier than Valhalla!

# Better error handling - don't exit on first error
set +e

# Log everything
exec > >(tee -a /databricks/driver/logs/osrm-init.log) 2>&1

echo "========================================="
echo "OSRM Init Script - Starting"
echo "Date: $(date)"
echo "User: $(whoami)"
echo "Working directory: $(pwd)"
echo "========================================="

# Function to check if command succeeded
check_status() {
    if [ $? -ne 0 ]; then
        echo "❌ ERROR: $1 failed"
        return 1
    else
        echo "✓ $1 succeeded"
        return 0
    fi
}

# Check if already installed
if command -v osrm-routed &> /dev/null; then
    echo "✓ OSRM already installed at: $(which osrm-routed)"
    exit 0
fi

# Install dependencies
echo ""
echo "[1/4] Installing system dependencies..."
echo "Running: apt-get update"

apt-get update -qq
check_status "apt-get update" || exit 1

echo "Installing build dependencies..."
apt-get install -y -qq \
    build-essential git cmake \
    libboost-all-dev \
    libtbb-dev \
    liblua5.3-dev \
    libluajit-5.1-dev \
    libstxxl-dev \
    libbz2-dev \
    libxml2-dev \
    libzip-dev \
    wget curl

check_status "Package installation" || exit 1

# Download OSRM
echo ""
echo "[2/4] Downloading OSRM source..."
cd /tmp || exit 1

if [ -d "osrm-backend" ]; then
    echo "Removing old OSRM source..."
    rm -rf osrm-backend
fi

git clone --depth 1 --branch v5.27.1 https://github.com/Project-OSRM/osrm-backend.git
check_status "Git clone" || exit 1

cd osrm-backend || exit 1

# Build OSRM
echo ""
echo "[3/4] Building OSRM (this takes 5-10 minutes)..."
mkdir -p build
cd build || exit 1

echo "Running cmake..."
cmake .. \
    -DCMAKE_BUILD_TYPE=Release \
    -DENABLE_LTO=Off

check_status "CMake configuration" || exit 1

echo "Compiling with $(nproc) cores..."
make -j$(nproc)
check_status "Compilation" || exit 1

echo "Installing binaries..."
make install
check_status "Installation" || exit 1

# Verify installation
if ! command -v osrm-extract &> /dev/null; then
    echo "❌ ERROR: osrm-extract not found after installation"
    exit 1
fi

echo "✓ OSRM installed successfully"
echo "  - osrm-extract: $(which osrm-extract)"
echo "  - osrm-routed: $(which osrm-routed)"

# Download and prepare routing data
echo ""
echo "[4/4] Preparing routing data..."

BUILD_DIR="/local_disk0/osrm_data"
mkdir -p ${BUILD_DIR}
cd ${BUILD_DIR} || exit 1

# Download OSM data
OSM_FILE="massachusetts.osm.pbf"

if [ ! -f "${OSM_FILE}" ]; then
    echo "Downloading Massachusetts OSM data (~200MB)..."
    wget --progress=dot:mega \
        https://download.geofabrik.de/north-america/us/massachusetts-latest.osm.pbf \
        -O ${OSM_FILE}

    check_status "OSM data download" || exit 1
else
    echo "✓ OSM data already exists"
fi

# Extract routing graph
echo "Extracting routing graph..."
osrm-extract -p /usr/local/share/osrm/profiles/car.lua massachusetts.osm.pbf
check_status "OSRM extract" || exit 1

# Partition graph
echo "Partitioning graph..."
osrm-partition massachusetts.osrm
check_status "OSRM partition" || exit 1

# Customize graph
echo "Customizing graph..."
osrm-customize massachusetts.osrm
check_status "OSRM customize" || exit 1

echo ""
echo "========================================="
echo "OSRM Init Script - COMPLETED SUCCESSFULLY"
echo "========================================="
echo "✓ OSRM binaries installed to /usr/local/bin"
echo "✓ Routing data ready: ${BUILD_DIR}/massachusetts.osrm"
echo "✓ Ready for isochrone generation"
echo ""
echo "To start OSRM server:"
echo "  osrm-routed --algorithm=MLD ${BUILD_DIR}/massachusetts.osrm"
echo "========================================="

exit 0
