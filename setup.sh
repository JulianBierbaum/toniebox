#!/bin/bash
# Toniebox Setup Script for Raspberry Pi 4B
# This script automates the setup process for the Toniebox project

# Exit on any error
set -e

echo "<--- Toniebox Setup --->"

# Create virtual environment and install requirements
echo "Setting up Python virtual environment..."
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Enable SPI and I2C interfaces
echo "Enabling SPI and I2C interfaces..."
sudo raspi-config nonint do_spi 0
sudo raspi-config nonint do_i2c 0

# Create systemd service for audio player
echo "Setting up audio player service..."
sudo tee /etc/systemd/system/audio_player.service > /dev/null << EOT
[Unit]
Description=Python Audio Player (Continuous)
After=media-pi.mount
Wants=network.target sound.target

[Service]
Type=simple
WorkingDirectory=/home/pi/toniebox
ExecStart=/usr/bin/bash /home/pi/toniebox/start_player.sh
Restart=on-failure
User=pi
Group=pi
Environment="DISPLAY=:0"
Environment="XDG_RUNTIME_DIR=/run/user/1000"
TimeoutStartSec=30
TimeoutStopSec=10
KillMode=process
SendSIGKILL=yes

[Install]
WantedBy=multi-user.target
EOT

# Add pi user to audio group
echo "Adding pi user to audio group..."
sudo usermod -a -G audio pi

# Enable and start audio player service
echo "Enabling and starting audio player service..."
sudo systemctl daemon-reload
sudo systemctl enable audio_player.service

# Set up USB auto-mount
echo "Setting up USB auto-mount..."
echo "Getting USB UUID..."
USB_UUID=$(sudo blkid /dev/sda1 | awk -F'"' '{print $2}')

if [ -z "$USB_UUID" ]; then
    echo "Warning: Could not detect USB device. Please make sure it's connected and try again."
    echo "You'll need to manually update /etc/fstab with the correct UUID."
else
    echo "USB UUID detected: $USB_UUID"
    # Create mount point if it doesn't exist
    sudo mkdir -p /media/pi

    # Add entry to fstab
    echo "Updating fstab..."
    if ! grep -q "$USB_UUID" /etc/fstab; then
        echo "UUID=$USB_UUID /media/pi vfat defaults,uid=1000,gid=1000,umask=022,noatime,nofail 0 2" | sudo tee -a /etc/fstab
    else
        echo "USB entry already exists in fstab. Skipping."
    fi
fi

# Configure ALSA for external speaker
echo "Configuring ALSA for external speaker..."
CONFIG_FILE="/boot/firmware/config.txt"
# If the file doesn't exist, try the alternative location
if [ ! -f "$CONFIG_FILE" ]; then
    CONFIG_FILE="/boot/config.txt"
fi

# Check if the file exists
if [ -f "$CONFIG_FILE" ]; then
    # Comment out dtparam=audio=on
    sudo sed -i 's/^dtparam=audio=on/#dtparam=audio=on/' $CONFIG_FILE

    # Add HiFiBerry DAC overlay if not already present
    if ! grep -q "dtoverlay=hifiberry-dac" $CONFIG_FILE; then
        echo "dtoverlay=hifiberry-dac" | sudo tee -a $CONFIG_FILE
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
