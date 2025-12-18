# Databricks notebook source
# MAGIC %md
# MAGIC # Debug Valhalla Installation
# MAGIC This notebook will install Valhalla step-by-step so we can see exactly where it fails

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Check Current State

# COMMAND ----------

import subprocess
import sys

print("Python version:", sys.version)
print("Python path:", sys.executable)

# Check if valhalla already exists
try:
    import valhalla
    print("✓ Valhalla is already installed!")
    print("Version:", valhalla.__version__ if hasattr(valhalla, '__version__') else 'unknown')
except ImportError:
    print("✗ Valhalla not found - will install")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Install System Dependencies

# COMMAND ----------

print("Installing system dependencies (this may take 2-3 minutes)...")

deps = [
    "cmake", "g++", "git", "wget",
    "libboost-all-dev",
    "libcurl4-openssl-dev",
    "libprotobuf-dev", "protobuf-compiler",
    "liblz4-dev", "libsqlite3-dev",
    "libspatialite-dev", "libgeos-dev",
    "libluajit-5.1-dev", "python3-dev"
]

try:
    # Update package list
    subprocess.run(["apt-get", "update", "-qq"], check=True)

    # Install dependencies
    result = subprocess.run(
        ["apt-get", "install", "-y", "-qq"] + deps,
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print("✓ System dependencies installed successfully")
    else:
        print("✗ Error installing dependencies")
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
except Exception as e:
    print(f"✗ Error: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Download Valhalla Source

# COMMAND ----------

import os

BUILD_DIR = "/tmp/valhalla_build_debug"
VALHALLA_VERSION = "3.4.0"

print(f"Downloading Valhalla {VALHALLA_VERSION}...")

# Clean up any previous build
if os.path.exists(BUILD_DIR):
    subprocess.run(["rm", "-rf", BUILD_DIR], check=True)

os.makedirs(BUILD_DIR)
os.chdir(BUILD_DIR)

try:
    # Download
    subprocess.run([
        "wget", "-q",
        f"https://github.com/valhalla/valhalla/archive/refs/tags/{VALHALLA_VERSION}.tar.gz"
    ], check=True)

    # Extract
    subprocess.run(["tar", "-xzf", f"{VALHALLA_VERSION}.tar.gz"], check=True)

    print(f"✓ Downloaded and extracted to {BUILD_DIR}/valhalla-{VALHALLA_VERSION}")

    # List contents
    files = os.listdir(f"{BUILD_DIR}/valhalla-{VALHALLA_VERSION}")
    print(f"Contents: {files[:10]}...")

except Exception as e:
    print(f"✗ Download error: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Configure Build

# COMMAND ----------

os.chdir(f"{BUILD_DIR}/valhalla-{VALHALLA_VERSION}")

print("Configuring CMake build...")

try:
    result = subprocess.run([
        "cmake", "-B", "build",
        "-DCMAKE_BUILD_TYPE=Release",
        "-DENABLE_PYTHON_BINDINGS=ON",
        "-DCMAKE_CXX_FLAGS=-Wno-error",
        "-DENABLE_SERVICES=OFF",
        "-DENABLE_HTTP=OFF"
    ], capture_output=True, text=True, timeout=300)

    if result.returncode == 0:
        print("✓ CMake configuration successful")
        print("Last 20 lines of output:")
        print('\n'.join(result.stdout.split('\n')[-20:]))
    else:
        print("✗ CMake configuration failed")
        print("STDOUT:", result.stdout[-2000:])
        print("STDERR:", result.stderr[-2000:])

except subprocess.TimeoutExpired:
    print("✗ CMake configuration timed out after 5 minutes")
except Exception as e:
    print(f"✗ Configuration error: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Compile Valhalla

# COMMAND ----------

print("Compiling Valhalla (this will take 10-15 minutes)...")
print("Using", os.cpu_count(), "CPU cores")

try:
    result = subprocess.run(
        ["cmake", "--build", "build", f"-j{os.cpu_count()}"],
        capture_output=True,
        text=True,
        timeout=1800  # 30 minute timeout
    )

    if result.returncode == 0:
        print("✓ Compilation successful!")
    else:
        print("✗ Compilation failed")
        # Show last 50 lines of output
        print("Last 50 lines of STDOUT:")
        print('\n'.join(result.stdout.split('\n')[-50:]))
        print("\nLast 50 lines of STDERR:")
        print('\n'.join(result.stderr.split('\n')[-50:]))

except subprocess.TimeoutExpired:
    print("✗ Compilation timed out after 30 minutes")
except Exception as e:
    print(f"✗ Compilation error: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: Install Valhalla

# COMMAND ----------

print("Installing Valhalla to system...")

try:
    result = subprocess.run(
        ["cmake", "--install", "build"],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print("✓ System installation successful")
    else:
        print("✗ Installation failed")
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)

except Exception as e:
    print(f"✗ Installation error: {e}")

# Run ldconfig
try:
    subprocess.run(["ldconfig"], check=True)
    print("✓ ldconfig completed")
except Exception as e:
    print(f"✗ ldconfig error: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 7: Install Python Bindings

# COMMAND ----------

BINDINGS_DIR = f"{BUILD_DIR}/valhalla-{VALHALLA_VERSION}/build/python"

print(f"Installing Python bindings from {BINDINGS_DIR}...")

if os.path.exists(BINDINGS_DIR):
    os.chdir(BINDINGS_DIR)

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "."],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print("✓ Python bindings installed")
        else:
            print("✗ Python bindings installation failed")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)

    except Exception as e:
        print(f"✗ Bindings installation error: {e}")
else:
    print(f"✗ Python bindings directory not found: {BINDINGS_DIR}")
    print("Checking what's in build directory:")
    if os.path.exists(f"{BUILD_DIR}/valhalla-{VALHALLA_VERSION}/build"):
        print(os.listdir(f"{BUILD_DIR}/valhalla-{VALHALLA_VERSION}/build"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 8: Verify Installation

# COMMAND ----------

print("Verifying Valhalla installation...")

try:
    import valhalla
    print("✓✓✓ SUCCESS! Valhalla is installed and working! ✓✓✓")

    # Try to get version
    if hasattr(valhalla, '__version__'):
        print(f"Version: {valhalla.__version__}")

    # Try to create an actor with minimal config
    import json
    config = {
        "mjolnir": {"tile_dir": "/tmp"},
        "service_limits": {
            "isochrone": {"max_contours": 4, "max_time": 120}
        }
    }

    try:
        actor = valhalla.Actor(json.dumps(config))
        print("✓ Valhalla Actor can be initialized")
    except Exception as e:
        print(f"⚠ Actor initialization failed (expected without tiles): {e}")

except ImportError as e:
    print(f"✗ Valhalla import failed: {e}")
    print("\nPython sys.path:")
    print(sys.path)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC
# MAGIC If all steps succeeded, Valhalla is now installed on this cluster!
# MAGIC
# MAGIC Next steps:
# MAGIC 1. Note which step failed (if any)
# MAGIC 2. We'll fix the init script based on what worked
# MAGIC 3. The cluster will have Valhalla available for all future runs
