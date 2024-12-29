from gpiozero import Button

up = Button(24)
down = Button(23)
confirm = Button(22)

while 1:
    up.when_pressed = print("up pressed")
    down.when_pressed = print("down pressed")
    confirm.when_pressed = print("confirm pressed")