#!/bin/bash

# =============================================================================
# ADAM3-GPIO - Python Project Installer
# Balanced approach - not too simple, not too complex
# Adapted for GPIO hardware projects
# =============================================================================

set -e

# Configuration
PROJECT_NAME="ADAM3-GPIO"
VENV_DIR="venv"
REQUIREMENTS_FILE="requirements.txt"
PYTHON_CMD="python3"
BASE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DEFAULT_USER="pi"

# GPIO-specific configuration
GPIO_GROUPS=("gpio" "dialout" "tty")
SYSTEM_PKGS=("python3-venv" "python3-dev" "build-essential" "netcat-openbsd")
RECOMMENDED_PKGS=("mpd" "mpc" "ashuffle")

# Service configuration
SERVICE_EXAMPLE="$BASE_DIR/examples/adam3-gpio.example.service"
SERVICE_FILE="/etc/systemd/system/adam3-gpio.service"
SERVICE_NAME="adam3-gpio"

# Options
QUIET_MODE=false
SKIP_SERVICE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -q|--quiet)
      QUIET_MODE=true
      shift
      ;;
    --skip-service)
      SKIP_SERVICE=true
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "IMPORTANT: Run as regular user, not with sudo!"
      echo "  ./install.sh                     # Correct way"
      echo "  sudo ./install.sh                # Causes permission issues"
      echo ""
      echo "Options:"
      echo "  -q, --quiet        Quiet mode"
      echo "  --skip-service      Skip systemd service"
      echo "  -h, --help          Show help"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Logging functions
log_info() { if [ "$QUIET_MODE" != "true" ]; then echo "[INFO] $1"; fi; }
log_warn() { if [ "$QUIET_MODE" != "true" ]; then echo "[WARN] $1"; fi; }
log_error(){ echo "[ERROR] $1"; exit 1; }
log_ok()   { if [ "$QUIET_MODE" != "true" ]; then echo "[OK] $1"; fi; }

# Utility functions
execute_cmd() {
  local desc=$1; shift
  local cmd="$@"
  if [ "$QUIET_MODE" = "true" ]; then
    if eval "$cmd" &> /dev/null; then return 0; else log_error "Failed to $desc"; fi
  else
    log_info "Executing: $desc"
    if eval "$cmd"; then return 0; else log_error "Failed to $desc"; fi
  fi
}

# Check system requirements
check_system() {
  log_info "Checking system requirements..."
  
  # Check Python
  if ! command -v python3 &> /dev/null; then
    log_error "python3 not found. Please install Python 3."
  fi
  
  # Check pip
  if ! command -v pip3 &> /dev/null; then
    log_error "pip3 not found. Please install pip."
  fi

  # Check if running as regular user (not root)
  if [ "$EUID" -eq 0 ]; then
    echo "Error: Please run as regular user, not with sudo"
    echo "Usage: ./install.sh [OPTIONS]"
    exit 1
  fi

  # Check recommended packages
  for pkg in "${RECOMMENDED_PKGS[@]}"; do
    if ! command -v "$pkg" &> /dev/null; then
      log_warn "$pkg not found. Install with: sudo apt install $pkg"
    fi
  done

  log_ok "System requirements OK"
}

# Install system packages
install_system_packages() {
  log_info "Installing system packages..."
  
  MISSING_PACKAGES=()
  for pkg in "${SYSTEM_PKGS[@]}"; do
    if ! dpkg -s "$pkg" &> /dev/null; then
      MISSING_PACKAGES+=("$pkg")
    fi
  done
  
  if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    execute_cmd "update package list" "sudo apt update"
    execute_cmd "install system packages" "sudo apt install -y ${MISSING_PACKAGES[*]}"
  fi
  
  log_ok "System packages ready"
}

# Setup Python environment
setup_python_env() {
  log_info "Setting up Python virtual environment..."
  
  if [ -d "$BASE_DIR/$VENV_DIR" ]; then
    log_info "Virtual environment already exists."
    rm -rf "$BASE_DIR/$VENV_DIR"
  fi
  
  execute_cmd "create virtual environment" "$PYTHON_CMD -m venv $VENV_DIR"
  
  # Install requirements
  if [ -f "$BASE_DIR/$REQUIREMENTS_FILE" ]; then
    log_info "Installing dependencies..."
    execute_cmd "install requirements" "$BASE_DIR/$VENV_DIR/bin/pip install -r $REQUIREMENTS_FILE"
    
    # Install GPIO-specific dependencies
    log_info "Installing GPIO libraries..."
    execute_cmd "install lgpio" "$BASE_DIR/$VENV_DIR/bin/pip install lgpio>=0.2.0"
  else
    log_info "No requirements.txt found, skipping dependencies"
  fi
  
  log_ok "Python environment ready"
}

# Setup GPIO permissions
setup_gpio_permissions() {
  log_info "Setting up GPIO permissions..."
  
  TARGET_USER=${SUDO_USER:-$USER}
  if [ "$TARGET_USER" = "root" ]; then TARGET_USER=$DEFAULT_USER; fi

  # Add user to GPIO groups
  for group in "${GPIO_GROUPS[@]}"; do
    if ! groups "$TARGET_USER" | grep -q "$group"; then
      log_info "Adding user to $group group..."
      execute_cmd "add user to $group group" "sudo usermod -a -G $group $TARGET_USER"
    fi
  done

  # Set ownership (excluding __pycache__ directories)
  find "$BASE_DIR" -type f ! -path "*/__pycache__/*" ! -name "*.pyc" -exec chown "$TARGET_USER:$TARGET_USER" {} \; 2>/dev/null || true
  find "$BASE_DIR" -type d ! -path "*/__pycache__" -exec chown "$TARGET_USER:$TARGET_USER" {} \; 2>/dev/null || true

  # Set permissions
  find "$BASE_DIR" -type d -exec chmod 755 {} \;
  find "$BASE_DIR" -type f -name "*.py" -exec chmod 644 {} \;
  
  # Make scripts executable
  chmod 755 "$BASE_DIR/install.sh" 2>/dev/null || true
  chmod 755 "$BASE_DIR/src/main.py" 2>/dev/null || true
  chmod 755 "$BASE_DIR/status.sh" 2>/dev/null || true

  log_ok "GPIO permissions configured"
  log_warn "You may need to log out and back in for group changes to take effect"
}

# Setup systemd service
setup_service() {
  if [ "$SKIP_SERVICE" = "true" ]; then
    log_info "Skipping systemd service setup..."
    return 0
  fi

  if [ -f "$SERVICE_EXAMPLE" ]; then
    log_info "Installing systemd service..."
    TMP_SERVICE="$(mktemp)"
    sed "s|/home/pi/adam3-gpio|$BASE_DIR|g" "$SERVICE_EXAMPLE" > "$TMP_SERVICE"
    
    execute_cmd "install service file" "sudo cp '$TMP_SERVICE' '$SERVICE_FILE'"
    execute_cmd "reload systemd daemon" "sudo systemctl daemon-reload"
    execute_cmd "enable service" "sudo systemctl enable $SERVICE_NAME.service"
    execute_cmd "start service" "sudo systemctl start $SERVICE_NAME.service"
    
    rm -f "$TMP_SERVICE"
    log_ok "Service installed and started"
  else
    log_info "No service example found, skipping systemd setup"
  fi
}

# Main execution
log_info "Starting installation of $PROJECT_NAME..."

# Check system
check_system

# Install system packages
install_system_packages

# Setup Python environment
setup_python_env

# Setup GPIO permissions
setup_gpio_permissions

# Setup service
setup_service

# Summary
echo ""
echo "==================================================================="
echo " Installation complete: $PROJECT_NAME"
echo " Directory: $BASE_DIR"
echo " Python Environment: $VENV_DIR"
if [ "$SKIP_SERVICE" != "true" ] && [ -f "$SERVICE_FILE" ]; then
  echo " Service installed and activated: $SERVICE_NAME.service"
  echo " Service commands:"
  echo "   sudo systemctl status $SERVICE_NAME.service"
  echo "   sudo journalctl -u $SERVICE_NAME.service -f"
  echo "   sudo systemctl restart $SERVICE_NAME.service"
else
  echo " Manual run:"
  echo "   $BASE_DIR/$VENV_DIR/bin/python3 $BASE_DIR/src/main.py"
fi
echo ""
echo " Hardware Setup:"
echo "   TM1652 Display: GPIO14 (UART TX), 5V, GND"
echo "   Status LEDs: GPIO21 (Data), 5V, GND"
echo "   Button: GPIO20, GND"
echo ""
echo " Note: You may need to log out and back in for GPIO group changes"
echo "==================================================================="

exit 0