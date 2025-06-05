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

### 2. Raspberry Pi Interface Configuration

Enable necessary interfaces:

```bash
sudo raspi-config
```

* Navigate to: `Interface Options`

  * Enable **SPI**
  * Enable **I2C**

---

## Systemd Watchdog Service

Create a `systemd` service to auto-start the player.

### Step-by-step:

1. Create a new file:

```bash
sudo nano /etc/systemd/system/audio_player.service
```

2. Add the following content:

```ini
[Unit]
Description=Python Audio Player (Continuous)
After=media-pi.mount
Wants=sound.target

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
```

3. Reload and enable the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable audio_player.service
```

4. Check status:

```bash
systemctl status audio_player.service
```

5. Add the `pi` user to the `audio` group:

```bash
sudo usermod -a -G audio pi
```

---

## Boot Optimization

Disable unnecessary services to reduce startup time:

```bash
sudo systemctl disable NetworkManager-wait-online.service
sudo systemctl disable ModemManager.service
sudo systemctl disable e2scrub_reap.service
sudo systemctl disable rpi-eeprom-update.service
sudo systemctl disable bluetooth.service
sudo systemctl disable avahi-daemon.service
```

---

## USB Auto-Mount

1. Identify the UUID of your USB device:

```bash
sudo blkid /dev/sda1
```

2. Edit the `/etc/fstab` file:

```bash
sudo nano /etc/fstab
```

3. Add the following line (replace `USB_UUID` with the actual UUID):

```fstab
UUID=USB_UUID /media/pi vfat defaults,noatime,nofail 0 2
```

---

## Audio Output Configuration (ALSA + MAX98357A)

1. Edit the Raspberry Pi firmware config:

```bash
sudo nano /boot/firmware/config.txt
```

2. Add the following:

```bash
dtparam=audio=on
dtoverlay=hifiberry-dac,card=1
```

3. Reboot:

```bash
sudo reboot
```

4. Verify audio output:

```bash
aplay -l
```

---

## Debugging

Logs are written to the `logs` directory. To watch logs live:

```bash
tail -f logs/rfid_player.log
```
