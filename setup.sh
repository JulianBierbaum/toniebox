#!/bin/bash
# Toniebox Setup Script for Raspberry Pi 4B (Modern Version with UV)
# This script automates the setup process for the Toniebox project
# Exit on any error
set -e

# Get current user and home directory
CURRENT_USER=$(whoami)
USER_HOME=$HOME
PROJECT_DIR=$PWD

echo "<--- Toniebox Setup --->"
echo "User: $CURRENT_USER"
echo "Home: $USER_HOME"
echo "Project Dir: $PROJECT_DIR"

# Check if uv is installed, install if necessary
if ! command -v uv &> /dev/null; then
    echo "Installing UV package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Add to PATH if not already there
    export PATH="$USER_HOME/.cargo/bin:$PATH"
fi

# Install dependencies with UV
echo "Installing dependencies..."
uv sync

# Enable SPI and I2C interfaces
echo "Enabling SPI and I2C interfaces..."
if command -v raspi-config &> /dev/null; then
    sudo raspi-config nonint do_spi 0
    sudo raspi-config nonint do_i2c 0
else
    echo "Warning: raspi-config not found. Skipping interface enablement."
fi

# Create systemd service for audio player
echo "Setting up audio player service..."
SERVICE_FILE="/etc/systemd/system/audio_player.service"

sudo tee $SERVICE_FILE > /dev/null << EOT
[Unit]
Description=Python Audio Player (Continuous)
After=media-pi.mount
Wants=sound.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR
ExecStart=/usr/bin/bash $PROJECT_DIR/start_player.sh
Restart=on-failure
User=$CURRENT_USER
Group=$CURRENT_USER
Environment="DISPLAY=:0"
Environment="XDG_RUNTIME_DIR=/run/user/$(id -u)"
TimeoutStartSec=30
TimeoutStopSec=10
KillMode=process
SendSIGKILL=yes

[Install]
WantedBy=multi-user.target
EOT

# Add user to audio group
echo "Adding $CURRENT_USER to audio group..."
sudo usermod -a -G audio $CURRENT_USER

# Optimize system services for faster boot and reduced overhead
echo "Optimizing system services..."
SERVICES_TO_DISABLE=(
    "NetworkManager-wait-online.service"
    "ModemManager.service"
    "e2scrub_reap.service"
    "rpi-eeprom-update.service"
    "bluetooth.service"
    "avahi-daemon.service"
)

for service in "${SERVICES_TO_DISABLE[@]}"; do
    if systemctl list-unit-files | grep -q "$service"; then
        sudo systemctl disable "$service" || true
    fi
done

# Enable and start audio player service
echo "Enabling and starting audio player service..."
sudo systemctl daemon-reload
sudo systemctl enable audio_player.service

# Set up USB auto-mount
echo "Setting up USB auto-mount..."
# Try to find a USB drive (sda1, sdb1, etc.)
USB_DEV=$(lsblk -rno NAME,TRAN | grep 'usb' | awk '{print $1}' | grep '[0-9]$' | head -n 1)

if [ -n "$USB_DEV" ]; then
    USB_DEV="/dev/$USB_DEV"
    echo "Found USB device: $USB_DEV"
    USB_UUID=$(sudo blkid $USB_DEV | awk -F'UUID="' '{print $2}' | awk -F'"' '{print $1}')
    
    if [ -n "$USB_UUID" ]; then
        echo "USB UUID detected: $USB_UUID"
        # Create mount point if it doesn't exist
        MOUNT_POINT="${USB_MOUNT_POINT:-/media/usb}"
        sudo mkdir -p $MOUNT_POINT
        
        # Add entry to fstab
        echo "Updating fstab..."
        if ! grep -q "$USB_UUID" /etc/fstab; then
            echo "UUID=$USB_UUID $MOUNT_POINT vfat defaults,uid=$(id -u),gid=$(id -g),umask=022,noatime,nofail 0 2" | sudo tee -a /etc/fstab
        else
            echo "USB entry already exists in fstab. Skipping."
        fi
    else
        echo "Warning: Could not get UUID for $USB_DEV."
    fi
else
    echo "Warning: No USB storage device found. Please connect one and run setup again if needed."
fi

# Configure ALSA for external speaker
echo "Configuring ALSA for onboard and external audio..."
CONFIG_FILE="/boot/firmware/config.txt"
if [ ! -f "$CONFIG_FILE" ]; then
    CONFIG_FILE="/boot/config.txt"
fi

if [ -f "$CONFIG_FILE" ]; then
    # Ensure onboard audio is enabled
    if grep -q "dtparam=audio" "$CONFIG_FILE"; then
        sudo sed -i 's/^#\?dtparam=audio=.*/dtparam=audio=on/' $CONFIG_FILE
    else
        echo "dtparam=audio=on" | sudo tee -a "$CONFIG_FILE"
    fi

    # Enable high-speed I2C (400kHz)
    if grep -q "dtparam=i2c_arm_baudrate" "$CONFIG_FILE"; then
        sudo sed -i 's/dtparam=i2c_arm_baudrate.*/dtparam=i2c_arm_baudrate=400000/' "$CONFIG_FILE"
    else
        echo "dtparam=i2c_arm_baudrate=400000" | sudo tee -a "$CONFIG_FILE"
    fi

    # Add HiFiBerry DAC with card=1 if not present
    if grep -q "dtoverlay=hifiberry-dac" "$CONFIG_FILE"; then
        sudo sed -i 's/dtoverlay=hifiberry-dac.*/dtoverlay=hifiberry-dac,card=1/' "$CONFIG_FILE"
    else
        echo "dtoverlay=hifiberry-dac,card=1" | sudo tee -a "$CONFIG_FILE"
    fi
else
    echo "Warning: Could not find config.txt file. You'll need to manually configure ALSA settings."
fi

echo "=== Setup Complete ==="
echo "A reboot is recommended to apply all changes."
echo "Do you want to reboot now? (y/n)"
read -r answer
if [[ "$answer" =~ ^[Yy]$ ]]; then
    sudo reboot
fi
