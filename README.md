# **Toniebox**
Toniebox project using a Raspberry pi 4B
Setup is using Raspberry PI OS Lite (64-Bit)

github:
```git clone https://github.com/JulianBierbaum/toniebox.git```

### Setup
- create venv with name ```.venv``` in toniebox directory
- install ```requirements.txt```
- in the ```raspi-config``` enable ```Interface->SPI``` and ```Interface->I2C```

### Start script

- create ```start_player.sh``` in toniebox directory

Code:
```sh
#!/bin/bash
source ~/toniebox/.venv/bin/activate
python ~/toniebox/main.py
```
<br> 

- go to ```/etc/systemd/system```
- create ```audio_player.service``` file

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

TimeoutStartSec=30
TimeoutStopSec=10
KillMode=process
SendSIGKILL=yes

[Install]
WantedBy=multi-user.target
```

<br>

- reload the systemd configuration with ```sudo systemctl daemon-reload```
- enable the service to start on boot ```sudo systemctl enable audio_player.service```
- start the service immediately (for testing) ```sudo systemctl start audio_player.service```
- check with ```systemctl status audio_player.service```
- run ```sudo usermod -a -G audio pi```


### Auto-mount USB

- get USB_UUID with ```sudo blkid /dev/sda1```
- open ```/etc/fstab```

Code:
``````bash
UUID=USB_UUID /media/pi vfat defaults,noatime,nofail 0 2
``````
