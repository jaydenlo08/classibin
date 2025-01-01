#!/usr/bin/env python3
# Recycling detection

import argparse
import os
import time
import common2 as common
import faulthandler
import sys
import RPi.GPIO as GPIO
from pycoral.utils.dataset import read_label_file
from pycoral.utils.edgetpu import make_interpreter
from pycoral.utils.edgetpu import run_inference
from pycoral.adapters.common import input_size
from pycoral.adapters.classify import get_classes

print("""
┌─────────────────────┐
│  @@ OLD VERSION @@  │
└─────────────────────┘
""")
sys.exit()

PIN = 14
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN, GPIO.OUT)

servo = GPIO.PWM(PIN, 50) # GPIO 17 for PWM with 50Hz
servo.start(0) # Initialization


def turn(angle, dur):
    print(f"Turning {angle}° for {dur} ms")
    duty = 2.5*(1+(angle/45))
    servo.ChangeDutyCycle(duty)
    time.sleep(0.1)
    servo.ChangeDutyCycle(0)
    time.sleep(dur/1000)

def generate_svg(size, text_lines):
    svg = common.SVG(size)
    font = 22
    svg.add_text(10, font, text_lines, font)
    #for y, line in enumerate(text_lines, start=1):
    #  svg.add_text(10, y * 20, line, 20)
    return svg.finish()

def main():
    default_model_dir = './dataset'
    default_model = 'mobilenet_v2_recycle_edgetpu.tflite'
    default_labels = 'recycle.txt'
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', help='.tflite model path',
                        default=os.path.join(default_model_dir,default_model))
    parser.add_argument('--labels', help='label file path',
                        default=os.path.join(default_model_dir, default_labels))
    parser.add_argument('--threshold', type=float, default=0.3,
                        help='classifier score threshold')
    parser.add_argument('--headless', help='Run without displaying the video.',
                        default=True, type=bool)
    args = parser.parse_args()

    print(f'===== {default_model} =====')
    interpreter = make_interpreter(args.model)
    interpreter.allocate_tensors()
    labels = read_label_file(args.labels)
    inference_size = input_size(interpreter)
    previous_output_length = 0
    turning = 0

    def user_callback(input_tensor, src_size):
        nonlocal previous_output_length
        nonlocal turning
        start_time = time.monotonic()
        run_inference(interpreter, input_tensor)

        results = get_classes(interpreter, 2, args.threshold)
        end_time = time.monotonic()
        inference_time = (end_time - start_time) * 1000
        if len(results) > 1:
            material = labels.get(results[0].id, results[0].id)
            text = f'[{inference_time:.2f} ms] {results[0].score * 100:.2f}% - {labels.get(results[0].id, results[0].id)} : {results[1].score * 100:.2f}% - {labels.get(results[1].id, results[1].id)}'
        elif len(results) == 1:
            material = labels.get(results[0].id, results[0].id)
            text = f'[{inference_time:.2f} ms] {results[0].score * 100:.2f}% - {labels.get(results[0].id, results[0].id)}'
        else:
            material = ""
            text = f'[{inference_time:.2f} ms] --.--% - no match'

        # Calculate the current output length
        current_output_length = len(text)

        # Clear the previous line if it's longer than the current output
        if current_output_length < previous_output_length:
            sys.stdout.write('\x1b[2K')

        # Print the current output
        print(f'\r{text}', end='', flush=True)

        # Update the previous output length
        previous_output_length = current_output_length


        try:
            wait = 500
            if turning == 0:
                if material == "paper":
                    turning = 1
                    turn(45, wait)
                    turning = 0
                elif material == "plastic":
                    turning = 1
                    turn(135, wait)
                    turning = 0

        except KeyboardInterrupt:
            servo.stop()
            GPIO.cleanup()

        return generate_svg(src_size, text)

    result = common.run_pipeline(user_callback,
                                    src_size=(640, 480),
                                    appsink_size=inference_size,
                                    headless=args.headless)

if __name__ == '__main__':
    main()
