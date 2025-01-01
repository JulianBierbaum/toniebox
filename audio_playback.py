import pygame as pg
import threading as th
from mfrc522 import SimpleMFRC522
import sqlite3
import time

def initialize_database():
    conn = sqlite3.connect("rfid_audio.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rfid_audio (
            id TEXT PRIMARY KEY,
            file_path TEXT NOT NULL
        )
    """)

    cursor.execute("SELECT COUNT(*) FROM rfid_audio")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO rfid_audio (id, file_path) VALUES (?, ?)", [
            ("631430949643", "outro.mp3"),
        ])
    conn.commit()
    conn.close()

class Audio:
    def __init__(self):
        pg.mixer.init()

    def play(self, file_id):
        file_path = self.get_file_path(file_id)
        if not file_path:
            print(f"No audio file mapped for ID: {file_id}")
            return

        self.file_path = f"files/{file_path}"
        self.audio_thread = th.Thread(target=self._play_audio).start()

    def _play_audio(self):
        try:
            pg.mixer.music.load(self.file_path)
            pg.mixer.music.play()
            print("playing audio: " + self.file_path)

            while pg.mixer.music.get_busy():
                pg.time.Clock().tick(10)
        except Exception as e:
            print(f"An error occurred: {str(e)}")

    def stop(self):
        pg.mixer.music.stop()

    def get_file_path(self, file_id):
        conn = sqlite3.connect("rfid_audio.db")
        cursor = conn.cursor()
        cursor.execute("SELECT file_path FROM rfid_audio WHERE id = ?", (file_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None

    def __del__(self):
        pg.mixer.quit()


initialize_database()

audio = Audio()
reader = SimpleMFRC522()
current_id = 0
none_counter = 0

while True:
    id, text = reader.read_no_block()
    print(id)

    if id is not None:
        if id != current_id:
            current_id = id
            audio.play(str(id))
        time.sleep(2)

    if id is None:
        none_counter += 1
    else:
        none_counter = 0

    if none_counter >= 2:
        audio.stop()
        none_counter = 0
        current_id = 0

    time.sleep(0.1)
