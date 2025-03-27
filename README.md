# toniebox
Toniebox project using a Raspberry pi 4B

# SETUP
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
Description=Start Python Script in venv
After=media-pi.mount
Requires=media-pi.mount
ConditionPathExists=/media/pi

[Service]
WorkingDirectory=/home/pi/toniebox
StandardOutput=inherit
StandardError=inherit
Restart=on-failure
User=pi
Group=pi
Environment="DISPLAY=:0"
Environment="XDG_RUNTIME_DIR=/run/user/1000"
ExecStart=/usr/bin/bash /home/pi/toniebox/start_player.sh
ProtectSystem=false
ProtectHome=false
NoNewPrivileges=false

[Install]
WantedBy=multi-user.target
```

<br>

- reload the systemd configuration with ```sudo systemctl daemon-reload```
- enable the service to start on boot ```sudo systemctl enable audio_player.service```
- start the service immediately (for testing) ```sudo systemctl start audio_player.service```
- check with ```systemctl status audio_player.service```


### Auto-mount USB

- get USB_UUID with ```sudo blkid /dev/sda1```
- open ```/etc/fstab```

Code:
``````bash
UUID=USB_UUID /media/pi vfat defaults,noatime,nofail 0 2
``````
