# Toniebox (Raspberry Pi 4B Project)

A DIY audio player project inspired by the Toniebox, using a **Raspberry Pi 4B** and **Raspberry Pi OS Lite (64-bit)**.

---

## Repository

Clone the GitHub repository into your home directory:

```bash
git clone https://github.com/JulianBierbaum/toniebox.git
```

---

## Initial Setup

Run the provided `setup.sh` script from within the `toniebox` directory:

```bash
cd ~/toniebox
source setup.sh
```

> If the script fails, follow the manual steps below.

---

## Manual Setup Guide

### 1. Dependency Installation

Install project dependencies with [**uv**](https://github.com/astral-sh/uv):

```bash
uv sync
```

### 2. Configuration

Create a `.env` file from the example (or manually):

```bash
cp .env.example .env
# Edit .env to set I2C_ADDRESS, USB_MOUNT_POINT, etc.
```

### 3. Raspberry Pi Interface Configuration

Enable necessary interfaces:

```bash
sudo raspi-config
```

* Navigate to: `Interface Options`

  * Enable **SPI**
  * Enable **I2C**

### 4. Systemd Watchdog Service

Create a `systemd` service to auto-start the player.

1. Create a new file:

```bash
sudo nano /etc/systemd/system/audio_player.service
```

2. Add the following content (replace `<USER>` and `<PATH_TO_PROJECT>`):

```ini
[Unit]
Description=Python Audio Player (Continuous)
After=media-usb.mount
Wants=sound.target

[Service]
Type=simple
WorkingDirectory=/home/<USER>/toniebox
ExecStart=/usr/bin/bash /home/<USER>/toniebox/start_player.sh
Restart=on-failure
User=<USER>
Group=<USER>
Environment="DISPLAY=:0"
Environment="XDG_RUNTIME_DIR=/run/user/1000"

TimeoutStartSec=30
TimeoutStopSec=10
KillMode=process
SendSIGKILL=yes

[Install]
WantedBy=multi-user.target
```

3. Reload and enable the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable audio_player.service
```

4. Add your user to the `audio` group:

```bash
sudo usermod -a -G audio $(whoami)
```

### 5. USB Auto-Mount

1. Identify the UUID of your USB device:

```bash
sudo blkid /dev/sda1
```

2. Edit `/etc/fstab`:

```bash
sudo nano /etc/fstab
```

3. Add the following line (replace `USB_UUID`):

```fstab
UUID=USB_UUID /media/usb vfat defaults,noatime,nofail 0 2
```

### 6. Audio & I2C Configuration

1. Edit `/boot/firmware/config.txt`:

```bash
sudo nano /boot/firmware/config.txt
```

2. Add/Update the following:

```bash
# Audio
dtparam=audio=on
dtoverlay=hifiberry-dac,card=1

# High-Speed I2C (for smooth UI)
dtparam=i2c_arm_baudrate=400000
```

3. Reboot:

```bash
sudo reboot
```

## Debugging

Logs are written to the `logs` directory. To watch logs live:

```bash
tail -f logs/rfid_player.log
```
