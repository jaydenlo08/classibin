#!/usr/bin/env python3
'''
@@ TEST SCRIPT @@

Connections:
N = NEMA-17
L = L298N
P = Pi (GPIO)

N_BLK - L_OUT1; N_GRN - L_OUT2
N_BLU - L_OUT4; N_RED - L_OUT3

L_IN1 - P_17; L_IN2 - P_27
L_IN3 - P_22; L_IN4 - P_18
'''
import RPi.GPIO as GPIO
GPIO.setwarnings(False)
import time

speed = 20
min_delay = 0.0008
max_delay = 0.0022
step_delay = max_delay-((max_delay-min_delay)*speed/100)
print(f"STEP_DELAY: {step_delay}")
nema_pins = [18, 27, 17, 22]

# setting up
GPIO.setmode(GPIO.BCM)
for gpio in range(4):
    GPIO.setup(nema_pins[gpio], GPIO.OUT)
    GPIO.output(nema_pins[gpio], GPIO.LOW)
 
def turn(distance, mode="FULL"):
    angle = distance*90
    print(f"Turning {angle} deg")
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
    
def manual():
    while True:
        try:
            distance = input("Enter in cm: ")
            print(int(distance))
            turn(int(distance), "FULL")
        except KeyboardInterrupt:
            print("\nCanceled by the user.")
            # Cleanup
            for gpio in range(4):
                GPIO.output(nema_pins[gpio], GPIO.LOW)
            GPIO.cleanup()
            exit(0)
            
def test():
    try:
        # Magic algorithm for calculating stops
        s = 4 # number of stops
        wt = 500 # width of tray
        t = 10 # thickness of MDF
        wd = (wt-t)/4-t # Width of each divider
        start_pos = wt/2 # In mm
        for stop in range(s):
            distance = ((stop+1)*(wd+t)-(wd/2)) # In mm
            move_distance = (distance-start_pos) / 10 # In cm
            return_distance = move_distance * -1
            print(f"n={stop}; move={round(move_distance)}; back={round(return_distance)}")
            turn(move_distance)
            time.sleep(1)
            turn(return_distance)
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nCanceled by the user.")
        # Cleanup
        for gpio in range(4):
            GPIO.output(nema_pins[gpio], GPIO.LOW)
        GPIO.cleanup()
        exit(0)
    
        
if __name__ == '__main__':
    manual()
