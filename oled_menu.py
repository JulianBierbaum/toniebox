"""
OLED display and menu system for the RFID Audio Player with KY-040 encoder.

This module provides a UI for the RFID Audio Player using an OLED display
and a rotary encoder for navigation.
"""

import time
from gpiozero import Button, RotaryEncoder
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import sh1106
from PIL import ImageFont

class OLEDMenu:
    """
    A class to handle the OLED display and menu system with rotary encoder.
    
    This class provides methods to display and navigate menus on the OLED 
    screen using a KY-040 rotary encoder for navigation and its switch
    for confirmation.
    """
    
    def __init__(self, encoder_clk=21, encoder_dt=20, confirm_pin=16):
        """
        Initialize the OLED display and input controls.
        
        Args:
            encoder_clk (int): GPIO pin for encoder CLK (rotary pin A)
            encoder_dt (int): GPIO pin for encoder DT (rotary pin B)
            confirm_pin (int): GPIO pin for encoder switch (confirm button)
        """
        # Initialize OLED
        self.serial = i2c(port=1, address=0x3C)
        self.device = sh1106(self.serial)
        self.font = ImageFont.load_default()
        
        # Menu state (same as original)
        self.menu_options = ["Currently Playing", "Add/Update Audio", "List Audios"]
        self.menu_selection = 0
        self.yes_no_options = ["Yes", "No"]
        self.yes_no_selection = 0
        self.file_selection = 0
        self.file_options = []
        self.option_confirmed = False
        self.current_menu = "main"
        
        # Input controls setup
        self.encoder = RotaryEncoder(encoder_clk, encoder_dt, bounce_time=0.05)
        self.confirm = Button(confirm_pin, bounce_time=0.05)
        
        # Event handlers
        self.encoder.when_rotated = self.handle_rotation
        self.confirm.when_pressed = self.on_confirm_pressed

    def handle_rotation(self):
        """
        Handle rotary encoder rotation events.
        """
        # Get the current state of the encoder
        if self.encoder.steps > 0:
            # Clockwise rotation
            for _ in range(self.encoder.steps):
                self.on_down_pressed()
        elif self.encoder.steps < 0:
            # Counter-clockwise rotation
            for _ in range(abs(self.encoder.steps)):
                self.on_up_pressed()
        
        # Reset the encoder steps after processing
        self.encoder.steps = 0

    def on_up_pressed(self):
        """Handle upward navigation (original logic preserved)"""
        if self.current_menu == "main":
            self.menu_selection = (self.menu_selection - 1) % len(self.menu_options)
        elif self.current_menu == "yes_no":
            self.yes_no_selection = (self.yes_no_selection - 1) % len(self.yes_no_options)
        elif self.current_menu == "files" and self.file_options:
            self.file_selection = (self.file_selection - 1) % len(self.file_options)
        self.update_display()

    def on_down_pressed(self):
        """Handle downward navigation (original logic preserved)"""
        if self.current_menu == "main":
            self.menu_selection = (self.menu_selection + 1) % len(self.menu_options)
        elif self.current_menu == "yes_no":
            self.yes_no_selection = (self.yes_no_selection + 1) % len(self.yes_no_options)
        elif self.current_menu == "files" and self.file_options:
            self.file_selection = (self.file_selection + 1) % len(self.file_options)
        self.update_display()

    def on_confirm_pressed(self):
        """Handle confirmation (original logic preserved)"""
        self.option_confirmed = True

    # All display methods remain unchanged from original
    def display_menu(self):
        """Display the main menu on the OLED screen."""
        with canvas(self.device) as draw:
            draw.text((0, 0), "RFID Audio Player", font=self.font, fill="white")
            for i, option in enumerate(self.menu_options):
                y_pos = 16 + (i * 12)
                prefix = ">" if i == self.menu_selection else " "
                draw.text((0, y_pos), f"{prefix} {option}", font=self.font, fill="white")

    def display_yes_no_menu(self):
        """Display a yes/no confirmation menu on the OLED screen."""
        with canvas(self.device) as draw:
            draw.text((0, 0), "Overwrite?", font=self.font, fill="white")
            draw.text((0, 16), "Entry exists", font=self.font, fill="white")
            for i, option in enumerate(self.yes_no_options):
                y_pos = 32 + (i * 12)
                prefix = ">" if i == self.yes_no_selection else " "
                draw.text((0, y_pos), f"{prefix} {option}", font=self.font, fill="white")

    def display_file_menu(self, files):
        """
        Display a menu of files on the OLED screen.
        
        Args:
            files (list): List of filenames to display
        """
        with canvas(self.device) as draw:
            draw.text((0, 0), "Files:", font=self.font, fill="white")
            start_idx = max(0, min(self.file_selection, len(files) - 3))
            visible_files = files[start_idx:start_idx + 3]
            for i, file in enumerate(visible_files):
                y_pos = 16 + (i * 12)
                prefix = ">" if start_idx + i == self.file_selection else " "
                truncated_file = file[:18] if len(file) > 18 else file
                draw.text((0, y_pos), f"{prefix} {truncated_file}", font=self.font, fill="white")
            if start_idx > 0:
                draw.text((120, 16), "^", font=self.font, fill="white")
            if start_idx + 3 < len(files):
                draw.text((120, 40), "v", font=self.font, fill="white")

    def display_current_audio(self, current_audio):
        """
        Display the currently playing audio on the OLED screen.
        
        Args:
            current_audio (str or None): Currently playing audio filename or None
        """
        with canvas(self.device) as draw:
            draw.text((0, 0), "Now Playing:", font=self.font, fill="white")
            if current_audio:
                if len(current_audio) > 18:
                    draw.text((0, 16), current_audio[:18], font=self.font, fill="white")
                    draw.text((0, 28), current_audio[18:36], font=self.font, fill="white")
                else:
                    draw.text((0, 16), current_audio, font=self.font, fill="white")
            else:
                draw.text((0, 16), "No audio playing", font=self.font, fill="white")
            draw.text((0, 48), "Press OK to return", font=self.font, fill="white")

    def display_message(self, message):
        """
        Display a message on the OLED screen.
        
        Args:
            message (str): Message to display
        """
        with canvas(self.device) as draw:
            words = message.split()
            lines = []
            current_line = []
            for word in words:
                if len(' '.join(current_line + [word])) <= 18:
                    current_line.append(word)
                else:
                    lines.append(' '.join(current_line))
                    current_line = [word]
            if current_line:
                lines.append(' '.join(current_line))
            for i, line in enumerate(lines[:4]):
                draw.text((0, i * 16), line, font=self.font, fill="white")

    def update_display(self):
        """Update the display based on current menu state."""
        if self.current_menu == "main":
            self.display_menu()
        elif self.current_menu == "yes_no":
            self.display_yes_no_menu()
        elif self.current_menu == "files" and self.file_options:
            self.display_file_menu(self.file_options)
            
    def wait_for_confirmation(self, timeout=None):
        """
        Wait for confirmation with optional timeout.
        
        Args:
            timeout (float, optional): Maximum time to wait in seconds
            
        Returns:
            bool: True if confirmed, False if timed out
        """
        self.option_confirmed = False
        start_time = time.time()
        while not self.option_confirmed:
            if timeout and (time.time() - start_time > timeout):
                return False
            time.sleep(0.1)
        return True
