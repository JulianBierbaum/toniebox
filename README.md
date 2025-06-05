# **/ Toniebox**
- Toniebox project using a Raspberry PI 4B
- setup is using Raspberry PI OS Lite (64-Bit)
<br>

- GitHub: `git clone https://github.com/JulianBierbaum/toniebox.git`
- clone into home dir

### // Debugging
- logs are automatically created under the `logs` directory
- you can live-watch the logs using `tail -f logs/rfid_player.log`

### // Setup
- the `setup.sh` script needs to be run in the toniebox directory the first time the player is used after that it is no longer neccesary
- if the setup file is not working you can follow the steps below:

#### /// General
- run `uv sync` to install dependencies
- in the `raspi-config` enable `Interface->SPI` and `Interface->I2C`

#### /// Watchdog script
- go to `/etc/systemd/system`
- create `audio_player.service` file

Code:
```sh
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

TimeoutStartSec=60
TimeoutStopSec=10
KillMode=process
SendSIGKILL=yes

[Install]
WantedBy=multi-user.target
```

<br>

- reload the systemd configuration with `sudo systemctl daemon-reload`
- enable the service to start on boot `sudo systemctl enable audio_player.service`
- (for testing) start the service immediately `sudo systemctl start audio_player.service`
- check with `systemctl status audio_player.service`
- run `sudo usermod -a -G audio pi`
- for start-up time optimization disable these services:

``````bash
sudo systemctl disable NetworkManager-wait-online.service
sudo systemctl disable ModemManager.service
sudo systemctl disable e2scrub_reap.service
sudo systemctl disable rpi-eeprom-update.service
sudo systemctl disable bluetooth.service
sudo systemctl disable avahi-daemon.service
``````

#### /// Auto-mount USB

- get USB_UUID with `sudo blkid /dev/sda1`
- open `/etc/fstab`

Code:
``````bash
UUID=USB_UUID /media/pi vfat defaults,noatime,nofail 0 2
``````

#### /// ALSA config
Set up ALSA (Advanced Linux Sound Architecture) to work with an external speaker through the MAX98357A amplifier.

- open `/boot/firmware/config.txt`
- add the code to the file

Code:
``````bash
dtparam=audio=on
dtoverlay=hifiberry-dac,card=1
``````

- reboot raspberry pi
- `aplay -l` to verify

