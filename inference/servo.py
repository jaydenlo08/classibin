#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time

PIN = 14
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN, GPIO.OUT)

servo = GPIO.PWM(PIN, 50) # GPIO 17 for PWM with 50Hz
servo.start(0) # Initialization

def turn(angle):
    duty = 2.5*(1+(angle/45))
    servo.ChangeDutyCycle(duty)
    time.sleep(0.2)
    servo.ChangeDutyCycle(0)

def turnMode(mode):
    if mode == 1:
        turn(45)
    elif mode == 2:
        turn(90)
    elif mode == 3:
        turn(135)

def turnLoop():
    while True:
        angle = int(input("Enter a value between 0° to 180°: "))
        if isinstance(mode, int):
            if (angle >= 0) and (angle <= 180):
                turn(angle)

def turnModeLoop():
    while True:
        inputMode = input("Enter a mode: ")
        if inputMode.isdigit():
            mode = int(inputMode)
            if (mode >= 0) and (mode <= 3):
                turnMode(mode)
            
turnModeLoop()
servo.stop()
GPIO.cleanup()
