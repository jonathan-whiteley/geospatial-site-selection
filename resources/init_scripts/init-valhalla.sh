#!/bin/bash
# Valhalla Init Script for Databricks Cluster
# Installs Valhalla routing engine on all cluster nodes at startup
# Pulls pre-built tiles from Silver volume to local disk for fast access

set -e

# Log everything
exec > >(tee -a /databricks/driver/logs/valhalla-init.log) 2>&1

echo "========================================="
echo "Valhalla Init Script - Starting"
echo "Date: $(date)"
echo "========================================="

# Configuration - UPDATED FOR YOUR ENVIRONMENT
VALHALLA_VERSION="3.4.0"
BUILD_DIR="/local_disk0/valhalla_build"
TILES_VOLUME="/Volumes/jdub_demo_aws/geospatial_site_selection/valhalla_data"
CONFIG_WORKSPACE="/Workspace/Users/jonathan.whiteley@databricks.com/projects/geospatial-site-selection/files/resources/configs/valhalla_config.json"

# Check if already installed
if python3 -c "import valhalla" 2>/dev/null; then
    echo "✓ Valhalla already installed, skipping"
    exit 0
fi

# Install system dependencies
echo "[1/5] Installing system dependencies..."
apt-get update -qq
apt-get install -y -qq \
    cmake \
    g++ \
    libboost-all-dev \
    libcurl4-openssl-dev \
    libprotobuf-dev \
    protobuf-compiler \
    liblz4-dev \
    libsqlite3-dev \
    libspatialite-dev \
    libgeos-dev \
    libgeos++-dev \
    libluajit-5.1-dev \
    python3-dev \
    wget \
    tar

echo "✓ System dependencies installed"

# Download and compile Valhalla
echo "[2/5] Compiling Valhalla ${VALHALLA_VERSION}..."

mkdir -p /tmp/valhalla_build
cd /tmp/valhalla_build

# Download source
echo "  Downloading source..."
wget -q https://github.com/valhalla/valhalla/archive/refs/tags/${VALHALLA_VERSION}.tar.gz
tar -xzf ${VALHALLA_VERSION}.tar.gz
cd valhalla-${VALHALLA_VERSION}

# Configure with Python bindings and disable strict warnings
echo "  Configuring build..."
cmake -B build \
    -DCMAKE_BUILD_TYPE=Release \
    -DENABLE_PYTHON_BINDINGS=ON \
    -DCMAKE_CXX_FLAGS="-Wno-error=format-truncation"

# Compile (use all CPU cores)
echo "  Compiling (this takes 10-15 minutes)..."
cmake --build build -j$(nproc)

# Install to system
echo "  Installing to system..."
cmake --install build

echo "✓ Valhalla compiled and installed"

# Install Python bindings
echo "[3/5] Installing Python bindings..."
cd build/python
python3 -m pip install -q .

echo "✓ Python bindings installed"

# Run ldconfig
ldconfig

# Copy pre-built tiles from Silver volume to local disk
echo "[4/5] Copying routing tiles from Silver volume..."

mkdir -p ${BUILD_DIR}

# Copy tiles archive from Silver volume (optional - might not exist yet)
if [ -d "${TILES_VOLUME}" ] && [ -f "${TILES_VOLUME}/valhalla_tiles.tar" ]; then
    echo "  Extracting tiles from ${TILES_VOLUME}/valhalla_tiles.tar"
    tar -xf ${TILES_VOLUME}/valhalla_tiles.tar -C ${BUILD_DIR}
    echo "✓ Tiles extracted to ${BUILD_DIR}"
else
    echo "⚠ WARNING: Tiles not found at ${TILES_VOLUME}/valhalla_tiles.tar"
    echo "  This is OK - tiles will be generated on first notebook run"
fi

# Copy Valhalla config from workspace
echo "[5/5] Copying Valhalla configuration..."

if [ -f "${CONFIG_WORKSPACE}" ]; then
    cp ${CONFIG_WORKSPACE} ${BUILD_DIR}/valhalla.json
    echo "✓ Config copied from ${CONFIG_WORKSPACE}"
else
    # Create minimal config if workspace config doesn't exist yet
    cat > ${BUILD_DIR}/valhalla.json << 'EOF'
{
  "mjolnir": {
    "tile_dir": "/local_disk0/valhalla_build/valhalla_tiles",
    "admin": "/local_disk0/valhalla_build/valhalla_tiles/admin.sqlite",
    "timezone": "/local_disk0/valhalla_build/valhalla_tiles/tz_world.sqlite"
  },
  "service_limits": {
    "auto": {
      "max_distance": 5000000.0,
      "max_locations": 20,
      "max_matrix_distance": 400000.0,
      "max_matrix_locations": 50
    },
    "isochrone": {
      "max_contours": 10,
      "max_time": 120,
      "max_distance": 200000.0,
      "max_locations": 1
    }
  }
}
EOF
    echo "✓ Created minimal config (workspace config not found)"
fi

# Verify installation
echo ""
echo "========================================="
echo "Verifying Valhalla installation..."
echo "========================================="

# Test Python import
python3 -c "import valhalla; print('✓ Valhalla Python module imported successfully')" || {
    echo "✗ ERROR: Failed to import valhalla Python module"
    exit 1
}

# Test actor initialization (only if config exists and has tiles)
if [ -d "${BUILD_DIR}/valhalla_tiles" ]; then
    python3 -c "
import valhalla
import json
try:
    actor = valhalla.Actor('${BUILD_DIR}/valhalla.json')
    status_json = actor.status()
    status = json.loads(status_json) if isinstance(status_json, str) else status_json
    print(f\"✓ Valhalla actor initialized\")
    print(f\"  Version: {status.get('version', 'unknown')}\")
    actions = status.get('available_actions', [])
    print(f\"  Available actions: {', '.join(actions)}\")
except Exception as e:
    print(f'⚠ WARNING: Could not initialize actor (tiles may not be ready): {e}')
    print('  This is OK - actor will work once tiles are generated')
"
else
    echo "⚠ Tiles directory not found - skipping actor test"
    echo "  This is OK - tiles will be generated by notebook"
fi

echo ""
echo "========================================="
echo "Valhalla Init Script - Complete"
echo "========================================="
echo "✓ Valhalla ${VALHALLA_VERSION} installed"
echo "✓ Python bindings available"
echo "✓ Config: ${BUILD_DIR}/valhalla.json"
if [ -d "${BUILD_DIR}/valhalla_tiles" ]; then
    echo "✓ Tiles: ${BUILD_DIR}/valhalla_tiles/"
else
    echo "⚠ Tiles: Will be generated on first run"
fi
echo "✓ Log: /databricks/driver/logs/valhalla-init.log"
echo "========================================="

exit 0
