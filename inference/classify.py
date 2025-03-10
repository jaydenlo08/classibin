#!/usr/bin/env python3
enable_gpio = True

import cv2
import os
import sys
from motor import turnServo, turnStepper, sortPos
from PIL import Image
from pycoral.adapters.common import input_size
from pycoral.adapters.classify import get_classes
from pycoral.utils.dataset import read_label_file
from pycoral.utils.edgetpu import make_interpreter
from pycoral.utils.edgetpu import run_inference
    
def main():
    # Define constants
    model_dir = '../train'
    model_file = 'mobilenet_v2_recycle_edgetpu.tflite'
    model_labels = 'recycle.txt'
    camera_idx = 0 # As in /dev/videoX
    inference_threshold = 80 # Threshold, in %
    
    # Initialise GPIO
    if enable_gpio == True:
        pass
        
    # Prepare model
    print(f'===== {model_file} =====')
    interpreter = make_interpreter(os.path.join(model_dir,model_file))
    interpreter.allocate_tensors()
    labels = read_label_file(os.path.join(model_dir,model_labels))
    inference_size = input_size(interpreter)
    turnServo(90)
    
    # Prepare camera
    camera = cv2.VideoCapture(camera_idx)
    previous_text_length = 0
    previous_object_name = ""
    
    # Main loop
    while camera.isOpened():
        # Picture from camera
        working_result, frame = camera.read()
        if not working_result:
            break
        cv2_im = frame
        cv2_im_rgb = cv2.cvtColor(cv2_im, cv2.COLOR_BGR2RGB)
        cv2_im_rgb = cv2.resize(cv2_im_rgb, inference_size)
        
        # Run inference
        run_inference(interpreter, cv2_im_rgb.tobytes())
        results = get_classes(interpreter, 1, inference_threshold/100)
        
        # Process results
        if len(results) == 0:
            # No results
            result = False
            text = "--.--% - no match"
            object_score = 0
            object_name = "none"
        elif len(results) > 0:
            # Yes results
            result = True
            object_score = results[0].score
            object_name = labels.get(results[0].id)
            text = f"{object_score * 100:.2f}% - {object_name}"
        
        # Display result
        if len(text) < previous_text_length:
            sys.stdout.write('\x1b[2K')
        print(f'\r{text}', end='', flush=True)
        previous_text_length = len(text)
        
        # Action
        if (enable_gpio == True) and (previous_object_name != object_name):
            if result == True:
                if object_name == "paper":
                    sortPos(1)
                if object_name == "plastic":
                    sortPos(2)
                if object_name == "metal":
                    sortPos(3)
                if object_name == "rubbish":
                    sortPos(4)
                if object_name == "cardboard":
                    pass
                else:
                    sortPos(4)
            previous_object_name = object_name
            
            
    # Post-processing
    camera.release()
    cv2.destroyAllWindows()
    
    
if __name__ == '__main__':
    main()
