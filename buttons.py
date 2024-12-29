from gpiozero import Button
from signal import pause

up = Button(24)
down = Button(23)
confirm = Button(22)

up.when_pressed = print("up pressed")
down.when_pressed = print("down pressed")
confirm.when_pressed = print("confirm pressed")

pause()
