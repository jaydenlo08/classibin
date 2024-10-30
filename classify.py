#!/usr/bin/env python3
# Recycling detection

import argparse
import os
import time
import common3 as common
import faulthandler
import sys
from pycoral.utils.dataset import read_label_file
from pycoral.utils.edgetpu import make_interpreter
from pycoral.utils.edgetpu import run_inference
from pycoral.adapters.common import input_size
from pycoral.adapters.classify import get_classes

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
    parser.add_argument('--threshold', type=float, default=0.7,
                        help='classifier score threshold')
    parser.add_argument('--headless', help='Run without displaying the video.',
                        default=False, type=bool)
    args = parser.parse_args()

    print(f'===== {default_model} =====')
    interpreter = make_interpreter(args.model)
    interpreter.allocate_tensors()
    labels = read_label_file(args.labels)
    inference_size = input_size(interpreter)
    previous_output_length = 0

    def user_callback(input_tensor, src_size):
        nonlocal previous_output_length
        start_time = time.monotonic()
        run_inference(interpreter, input_tensor)

        results = get_classes(interpreter, 1, args.threshold)
        end_time = time.monotonic()
        inference_time = (end_time - start_time) * 1000
        
        if results:
            text = f'[{inference_time:.2f} ms] {results[0].score * 100:.2f}% - {labels.get(results[0].id, results[0].id)}'
        else:
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
        return generate_svg(src_size, text)



    result = common.run_pipeline(user_callback,
                                    src_size=(640, 480),
                                    appsink_size=inference_size,
                                    headless=args.headless)

if __name__ == '__main__':
    main()
