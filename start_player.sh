#!/bin/bash

set -e  # Exit on any error

# Set up logging
LOG_DIR="/home/pi/toniebox/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/startup.log"

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log_message "Starting RFID Audio Player..."

# Change to the correct directory
cd /home/pi/toniebox || {
    log_message "ERROR: Could not change to /home/pi/toniebox directory"
    exit 1
}

# Wait for system to be ready
log_message "Waiting for system initialization..."
sleep 10

# Check if required hardware is available
check_hardware() {
    log_message "Checking hardware availability..."
    
    # Check I2C
    if [ ! -e /dev/i2c-1 ]; then
        log_message "WARNING: I2C device not found, waiting..."
        sleep 5
    fi
    
    # Check SPI
    if [ ! -e /dev/spidev0.0 ]; then
        log_message "WARNING: SPI device not found, waiting..."
        sleep 5
    fi
    
    # Check GPIO
    if [ ! -e /dev/gpiomem ]; then
        log_message "WARNING: GPIO memory device not found"
    fi
}

check_hardware

# Check if UV is available
if ! command -v uv &> /dev/null; then
    log_message "ERROR: UV not found in PATH"
    # Try to source cargo environment
    if [ -f "$HOME/.cargo/env" ]; then
        source "$HOME/.cargo/env"
        log_message "Sourced cargo environment"
    fi
fi

# Verify UV is working
if ! uv --version &> /dev/null; then
    log_message "ERROR: UV is not working properly"
    exit 1
fi

log_message "UV version: $(uv --version)"

# Check if .env file exists
if [ ! -f .env ]; then
    log_message "WARNING: .env file not found, creating default..."
    cat > .env << 'EOF'
# Audio settings
MEDIA_PATH=/media/pi
DEFAULT_AUDIO_DEVICE=speaker
DEFAULT_VOLUME=80

# GPIO pins for rotary encoder
ENCODER_CLK=18
ENCODER_DT=24
ENCODER_CONFIRM=23
ENCODER_BOUNCE_TIME=0.05

# RFID settings
MAX_CONSECUTIVE_ERRORS=3
REINIT_INTERVAL=300
READ_TIMEOUT=30
READ_WITH_TIMEOUT_MAX_RETRIES=3

# Database
DATABASE_URL=sqlite:///rfid_audio.db
EOF
fi

# Wait a bit more for audio system to be ready
log_message "Waiting for audio system..."
sleep 5

# Start the application with proper error handling
log_message "Starting main application..."
exec uv run main.py 2>&1 | tee -a "$LOG_FILE"