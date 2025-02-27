# toniebox
Toniebox project using a Raspberry pi 4B


# SETUP
- create venv with name ```.venv``` in toniebox directory
- install ```requirements.txt```

### Start script

- create ```start_player.sh``` in toniebox directory

Code:
```sh
#!/bin/bash
source ~/toniebox/.venv/bin/activate
python ~/toniebox/oled.py
```
<br> 

- go to ```/etc/systemd/system```
- create ```audio_player.service``` file

Code:
```sh
[Unit]
Description=Start Python Script in venv
After=network.target

[Service]
ExecStart=/bin/bash /home/pi/toniebox/start_player.sh
WorkingDirectory=/home/pi/toniebox
StandardOutput=inherit
StandardError=inherit
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
```

<br>

- reload the systemd configuration with ```sudo systemctl daemon-reload```
- enable the service to start on boot ```sudo systemctl enable audio_player.service```
- start the service immediately (for testing) ```sudo systemctl audio_player.service```


### Auto-mount USB

- get USB_UUID with ```sudo blkid /dev/sda1```
- open ```/etc/fstab```

Code:
``````bash
UUID=USB_UUID /media/pi vfat defaults,noatime 0 2
``````
