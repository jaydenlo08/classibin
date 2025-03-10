# Module to control motors

'''
@@ CONNECTIONS @@

N = NEMA-17
L = L298N
S = Servo
P = Pi (BOARD)

N_BLK - L_OUT1; N_GRN - L_OUT2
N_BLU - L_OUT4; N_RED - L_OUT3

L_IN1 - P_11; L_IN2 - P_13
L_IN3 - P_15; L_IN4 - P_12

S_+VE - P_4; S_-VE - P_6; S_DAT - P_8

'''

import RPi.GPIO as GPIO
import time

# Settings
enable_servo = True
enable_stepper = True

# Define constants
servo_pin = 14 # GPIO pin number
step1 = 17
step2 = 18
step3 = 27
step4 = 22
speed = 10
min_delay = 0.0005
max_delay = 0.0022
step_delay = max_delay-((max_delay-min_delay)*speed/100)
nema_pins = [18, 27, 17, 22]

# Initialise GPIO

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(servo_pin, GPIO.OUT)
servo = GPIO.PWM(servo_pin, 50)
servo.start(0)

for gpio in range(4):
    GPIO.setup(nema_pins[gpio], GPIO.OUT)
    GPIO.output(nema_pins[gpio], GPIO.LOW)

def sortPos(position): # 1, 2, 3, 4
    if (position >= 1 and position <= 4):
        if position == 1:
            distance = -16# In cm
        if position == 2:
            distance = -6.5
        if position == 3:
            distance = 6
        if position == 4:
            distance = 17
        if enable_stepper == True:
            turnStepper(distance)
        if enable_servo == True:
            turnServo(60)
            time.sleep(1)
            turnServo(90)
            time.sleep(0.5)
        if enable_stepper == True:
            turnStepper(distance*-1)
        time.sleep(1)
    else:
        print("Invalid compartment input")
    
# Helper function for servo
def turnServo(angle):
    duty = 2.5*(1+(angle/45))
    servo.ChangeDutyCycle(duty)
    time.sleep(0.5)
    servo.ChangeDutyCycle(0)
    
def turnStepper(distance, mode="FULL"):
    angle = distance*90
    if mode == "HALF":
        step_count = round(angle/0.9)
    else:
        step_count = round(angle/1.8)
    if step_count >= 0:
        step_range = range(step_count)
        i = step_range[0]
    elif step_count <= 0:
        step_range = range(abs(step_count), 0, -1)
        i = step_range[-1]
    half_seq = [
        [1,0,0,0], [1,1,0,0], [0,1,0,0], [0,1,1,0],
        [0,0,1,0], [0,0,1,1], [0,0,0,1], [1,0,0,1]
    ]
    wave_seq = [[1,0,0,0], [0,1,0,0], [0,0,1,0], [0,0,0,1]]
    full_seq = [[1,1,0,0], [0,1,1,0], [0,0,1,1], [1,0,0,1]]
        
    if mode == "HALF":
        for phrase in step_range:
            for pin in range(4):
                GPIO.output(nema_pins[pin], half_seq[phrase%8][pin])
            time.sleep(step_delay)
    elif mode == "WAVE":
        for phrase in step_range:
            for pin in range(4):
                GPIO.output(nema_pins[pin], wave_seq[phrase%4][pin])
            time.sleep(step_delay)
    elif mode == "FULL":
        for phrase in step_range:
            for pin in range(4):
                GPIO.output(nema_pins[pin], full_seq[phrase%4][pin])
            time.sleep(step_delay)
                
    
    # Cleanup
    for gpio in range(4):
        GPIO.output(nema_pins[gpio], GPIO.LOW)
