#!/bin/bash
# ADAM3-GPIO Status Script
# Quick system status check

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "================================================="
echo "ADAM3-GPIO Status Check"
echo "================================================="
echo

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "[WARNING] Running as root"
else
    echo "[OK] Running as regular user"
fi

# Check virtual environment
if [ -f "venv/bin/activate" ]; then
    echo "[OK] Virtual environment found"
else
    echo "[ERROR] Virtual environment not found"
fi

# Check configuration
if [ -f "config/settings.json" ]; then
    echo "[OK] Configuration file found"
else
    echo "[ERROR] Configuration file missing"
fi

# Check service status
echo
echo "Service Status:"
if systemctl is-active --quiet adam3-gpio.service; then
    echo "[OK] Service is running"
else
    echo "[ERROR] Service is not running"
fi

if systemctl is-enabled --quiet adam3-gpio.service; then
    echo "[OK] Service is enabled"
else
    echo "[WARNING] Service is not enabled"
fi

# Check hardware
echo
echo "Hardware Status:"

# Check UART
if [ -c "/dev/ttyAMA0" ]; then
    echo "[OK] UART device available"
else
    echo "[ERROR] UART device not found"
fi

# Check UART config
if grep -q "enable_uart=1" /boot/firmware/config.txt 2>/dev/null; then
    echo "[OK] UART enabled in config"
else
    echo "[ERROR] UART not enabled in config"
fi

# Check /dev/mem for WS2812B
if [ -c "/dev/mem" ]; then
    echo "[OK] /dev/mem available for LEDs"
else
    echo "[ERROR] /dev/mem not found"
fi

# Check MPD
echo
echo "MPD Status:"
if systemctl is-active --quiet mpd.service; then
    echo "[OK] MPD service is running"
else
    echo "[ERROR] MPD service is not running"
fi

# Test MPD connection
if command -v mpc &> /dev/null; then
    if mpc status &>/dev/null; then
        echo "[OK] MPD connection successful"
    else
        echo "[ERROR] MPD connection failed"
    fi
else
    echo "[WARNING] mpc command not found, cannot test connection"
fi

# Check dependencies
echo
echo "Dependencies:"
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate 2>/dev/null || echo "[ERROR] Failed to activate virtual environment"
    
    # Check Python packages with proper import names
    declare -A packages=(
        ["python-mpd2"]="mpd"
        ["gpiozero"]="gpiozero"
        ["rpi-ws281x"]="rpi_ws281x"
        ["pyserial"]="serial"
        ["lgpio"]="lgpio"
    )
    
    for package_name in "${!packages[@]}"; do
        import_name="${packages[$package_name]}"
        if python -c "import ${import_name}" &>/dev/null; then
            echo "[OK] $package_name is installed"
    else
            echo "[ERROR] $package_name is missing"
    fi
done

deactivate 2>/dev/null
else
    echo "[ERROR] Virtual environment not found - cannot check dependencies"
fi

echo
echo "================================================="
echo "Quick Commands:"
echo "  sudo venv/bin/python3 src/main.py   # Start ADAM3-GPIO"
echo "  sudo systemctl start adam3-gpio     # Start the service"
echo "  sudo systemctl stop adam3-gpio      # Stop the service"
echo "  sudo systemctl restart adam3-gpio   # Restart the service"
echo "  sudo journalctl -u adam3-gpio -f    # View service logs"
echo "  sudo venv/bin/python3 src/main.py   # Run the service manually"
echo "=================================================" 