#!/usr/bin/env python3
# Recycling detection

import argparse
import os
import time
import common
import faulthandler
import sys
from pycoral.utils.dataset import read_label_file
from pycoral.utils.edgetpu import make_interpreter
from pycoral.utils.edgetpu import run_inference
from pycoral.adapters.common import input_size
from pycoral.adapters.classify import get_classes

def generate_svg(size, text_lines):
    svg = common.SVG(size)
    for y, line in enumerate(text_lines, start=1):
      svg.add_text(10, y * 20, line, 20)
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
    parser.add_argument('--top_k', type=int, default=1,
                        help='number of categories with highest score to display')
    parser.add_argument('--threshold', type=float, default=0.7,
                        help='classifier score threshold')
    parser.add_argument('--videosrc', help='Which video source to use. ',
                        default='/dev/video0')
    parser.add_argument('--headless', help='Run without displaying the video.',
                        default=True, type=bool)
    parser.add_argument('--videofmt', help='Input video format.',
                        default='raw',
                        choices=['raw', 'h264', 'jpeg'])
    args = parser.parse_args()

    print('Loading {} with {} labels.'.format(args.model, args.labels))
    interpreter = make_interpreter(args.model)
    interpreter.allocate_tensors()
    labels = read_label_file(args.labels)
    inference_size = input_size(interpreter)
    previous_output_length = 0

    def user_callback(input_tensor, src_size, inference_box):
        nonlocal previous_output_length
        start_time = time.monotonic()
        run_inference(interpreter, input_tensor)

        results = get_classes(interpreter, args.top_k, args.threshold)
        end_time = time.monotonic()
        inference_time = (end_time - start_time) * 1000
        
        if results:
            text_lines = ['[{:.2f}ms]'.format(inference_time)]
            for result in results:
                text_lines.append('{:.2f}% - {}'.format(result.score * 100, labels.get(result.id, result.id)))
        else:
            text_lines = ['[{:.2f}ms] (no match)'.format(inference_time)]

        # Join the text lines into one output string
        output = ' '.join(text_lines)
        
        # Calculate the current output length
        current_output_length = len(output)
        
        # Clear the previous line if it's longer than the current output
        if current_output_length < previous_output_length:
            # Print spaces to clear the rest of the line
            #sys.stdout.write('\x1b[1A')
            sys.stdout.write('\x1b[2K')
            #print(' ' * (previous_output_length), end='', flush=True)
            #print("\033[A\033[A")
        # Print the current output
        print('\r' + output, end='', flush=True)
        
        # Update the previous output length
        previous_output_length = current_output_length




    result = common.run_pipeline(user_callback,
                                    src_size=(640, 480),
                                    appsink_size=inference_size,
                                    videosrc=args.videosrc,
                                    videofmt=args.videofmt,
                                    headless=args.headless)

if __name__ == '__main__':
    main()
