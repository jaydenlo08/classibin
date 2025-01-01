#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time

PIN = 14
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN, GPIO.OUT)

servo = GPIO.PWM(PIN, 50) # GPIO 17 for PWM with 50Hz
servo.start(0) # Initialization

def turn(angle, dur):
    print(f"Turning {angle}° for {dur} ms")
    duty = 2.5*(1+(angle/45))
    servo.ChangeDutyCycle(duty)
    time.sleep(dur/1000)

try:
    while True:
      turn(45, 500)
      turn(90, 500)
      turn(135, 500)
      turn(90, 500)

except KeyboardInterrupt:
    servo.stop()
    GPIO.cleanup()
