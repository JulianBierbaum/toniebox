"""
OLED display and menu system for the RFID Audio Player.

This module provides a UI for the RFID Audio Player using an OLED display
and buttons for navigation.
"""

import time
from gpiozero import Button
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import sh1106
from PIL import ImageFont

class OLEDMenu:
    """
    A class to handle the OLED display and menu system.
    
    This class provides methods to display and navigate menus on the OLED 
    screen using physical buttons.
    """
    
    def __init__(self, up_pin=24, down_pin=23, confirm_pin=22):
        """
        Initialize the OLED display and buttons.
        
        Args:
            up_pin (int): GPIO pin for the up button
            down_pin (int): GPIO pin for the down button
            confirm_pin (int): GPIO pin for the confirm button
        """
        # Initialize OLED
        self.serial = i2c(port=1, address=0x3C)
        self.device = sh1106(self.serial)
        self.font = ImageFont.load_default()
        
        # Menu state
        self.menu_options = ["Currently Playing", "Add/Update Audio", "List Audios"]
        self.menu_selection = 0
        self.yes_no_options = ["Yes", "No"]
        self.yes_no_selection = 0
        self.file_selection = 0
        self.file_options = []
        self.option_confirmed = False
        self.current_menu = "main"
        
        # Button setup with debounce
        self.up = Button(up_pin, bounce_time=0.05)
        self.down = Button(down_pin, bounce_time=0.05)
        self.confirm = Button(confirm_pin, bounce_time=0.05)
        
        # Button handlers
        self.up.when_pressed = self.on_up_pressed
        self.down.when_pressed = self.on_down_pressed
        self.confirm.when_pressed = self.on_confirm_pressed

    def display_menu(self):
        """Display the main menu on the OLED screen."""
        with canvas(self.device) as draw:
            draw.text((0, 0), "RFID Audio Player", font=self.font, fill="white")
            for i, option in enumerate(self.menu_options):
                y_pos = 16 + (i * 12)  # Start menu items below title
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
            
            # Calculate start index to show files with selection visible
            start_idx = max(0, min(self.file_selection, len(files) - 3))
            
            # Show up to 3 files at a time
            visible_files = files[start_idx:start_idx + 3]
            for i, file in enumerate(visible_files):
                y_pos = 16 + (i * 12)
                prefix = ">" if start_idx + i == self.file_selection else " "
                # Truncate filename to fit screen
                truncated_file = file[:18] if len(file) > 18 else file
                draw.text((0, y_pos), f"{prefix} {truncated_file}", font=self.font, fill="white")
            
            # Show scroll indicators if needed
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
                # Split long filenames across multiple lines
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
            # Split message into multiple lines if needed
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
            
            for i, line in enumerate(lines[:4]):  # Show up to 4 lines
                draw.text((0, i * 16), line, font=self.font, fill="white")

    def on_up_pressed(self):
        """Handle up button press based on current menu."""
        if self.current_menu == "main":
            self.menu_selection = (self.menu_selection - 1) % len(self.menu_options)
        elif self.current_menu == "yes_no":
            self.yes_no_selection = (self.yes_no_selection - 1) % len(self.yes_no_options)
        elif self.current_menu == "files" and self.file_options:
            self.file_selection = (self.file_selection - 1) % len(self.file_options)
        self.update_display()

    def on_down_pressed(self):
        """Handle down button press based on current menu."""
        if self.current_menu == "main":
            self.menu_selection = (self.menu_selection + 1) % len(self.menu_options)
        elif self.current_menu == "yes_no":
            self.yes_no_selection = (self.yes_no_selection + 1) % len(self.yes_no_options)
        elif self.current_menu == "files" and self.file_options:
            self.file_selection = (self.file_selection + 1) % len(self.file_options)
        self.update_display()

    def on_confirm_pressed(self):
        """Handle confirm button press."""
        self.option_confirmed = True

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
        Wait for button confirmation with optional timeout.
        
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
