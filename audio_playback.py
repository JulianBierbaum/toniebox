import pygame as pg
import threading as th
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
import time

class Audio:
    def __init__(self):
        pg.mixer.init()

    def play(self, audio_name):
        self.file_path = f"files/{audio_name}.mp3"

        self.audio_thread = th.Thread(target=self._play_audio).start()

    def _play_audio(self):
        try:
            pg.mixer.music.load(self.file_path)
            pg.mixer.music.play()

            while pg.mixer.music.get_busy():
                pg.time.Clock().tick(10)
        except Exception as e:
            print(f"An error occurred: {str(e)}")

    def stop(self):
        pg.mixer.music.stop()

    def __del__(self):
        pg.mixer.quit()

audio = Audio()
reader = SimpleMFRC522()
current_id = 0
none_counter = 0

while (True):
    id, text = reader.read_no_block()
    print(id)

    if id != None:
        # text = text.rstrip()

        if id != current_id:
            current_id = id
            audio.play(id)
        time.sleep(2)

    if id == None:
        none_counter += 1
    else:
        none_counter = 0

    if none_counter >= 2:
        audio.stop()
        none_counter = 0
        current_id = 0

    time.sleep(0.1)
