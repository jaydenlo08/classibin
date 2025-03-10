#!/usr/bin/env python3
from motor import turnServo, turnStepper, sortPos
import time

while True:
    time.sleep(2)
    sortPos(3)
