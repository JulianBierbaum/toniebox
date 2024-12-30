from gpiozero import Button
from signal import pause

up = Button(24)
down = Button(23)
confirm = Button(22)

def on_up_pressed():
    print("up pressed")

def on_down_pressed():
    print("down pressed")

def on_confirm_pressed():
    print("confirm pressed")

up.when_pressed = on_up_pressed
down.when_pressed = on_down_pressed
confirm.when_pressed = on_confirm_pressed

pause()