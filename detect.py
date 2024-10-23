# Recycling detection

import collections
import io
import argparse
import gstreamer
import os
import time

from pycoral.adapters.common import input_size
from pycoral.adapters.detect import get_objects
from pycoral.utils.dataset import read_label_file
from pycoral.utils.edgetpu import make_interpreter
from pycoral.utils.edgetpu import run_inference

class SVG:
    SVG_HEADER = '<svg width="{w}" height="{h}" version="1.1" >'
    SVG_RECT = '<rect x="{x}" y="{y}" width="{w}" height="{h}" stroke="{s}" stroke-width="{sw}" fill="none" />'
    SVG_TEXT = '''
    <text x="{x}" y="{y}" font-size="{fs}" dx="0.05em" dy="0.05em" fill="black">{t}</text>
    <text x="{x}" y="{y}" font-size="{fs}" fill="white">{t}</text>
    '''
    SVG_FOOTER = '</svg>'
    def __init__(self, size):
        self.io = io.StringIO()
        self.io.write(self.SVG_HEADER.format(w=size[0] , h=size[1]))

    def add_rect(self, x, y, w, h, stroke, stroke_width):
        self.io.write(self.SVG_RECT.format(x=x, y=y, w=w, h=h, s=stroke, sw=stroke_width))

    def add_text(self, x, y, text, font_size):
        self.io.write(self.SVG_TEXT.format(x=x, y=y, t=text, fs=font_size))

    def finish(self):
        self.io.write(self.SVG_FOOTER)
        return self.io.getvalue()
        
def generate_svg(src_size, inference_box, objs, labels, text_lines):
    svg = SVG(src_size)
    src_w, src_h = src_size
    box_x, box_y, box_w, box_h = inference_box
    scale_x, scale_y = src_w / box_w, src_h / box_h

    for y, line in enumerate(text_lines, start=1):
        svg.add_text(10, y * 20, line, 20)
    for obj in objs:
        bbox = obj.bbox
        if not bbox.valid:
            continue
        # Absolute coordinates, input tensor space.
        x, y = bbox.xmin, bbox.ymin
        w, h = bbox.width, bbox.height
        # Subtract boxing offset.
        x, y = x - box_x, y - box_y
        # Scale to source coordinate space.
        x, y, w, h = x * scale_x, y * scale_y, w * scale_x, h * scale_y
        percent = int(100 * obj.score)
        label = f'{percent}% {labels.get(obj.id, obj.id)}'
        svg.add_text(x, y - 5, label, 20)
        svg.add_rect(x, y, w, h, 'red', 2)
    return svg.finish()

def main():
    default_model_dir = './models'
    default_model_name = 'coco'
    #default_model_name = 'rubbish'
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', help='.tflite model path',
                        default=os.path.join(default_model_dir,default_model_name+".tflite"))
    parser.add_argument('--labels', help='label file path',
                        default=os.path.join(default_model_dir, default_model_name+".txt"))
    parser.add_argument('--top_k', type=int, default=1,
                        help='number of categories with highest score to display')
    parser.add_argument('--threshold', type=float, default=0.75,
                        help='classifier score threshold')
    parser.add_argument('--videosrc', help='Which video source to use. ',
                        default='/dev/video0')
    args = parser.parse_args()

    print('Loading {} with {} labels.'.format(args.model, args.labels))
    interpreter = make_interpreter(args.model)
    interpreter.allocate_tensors()
    labels = read_label_file(args.labels)
    inference_size = input_size(interpreter)


    def user_callback(input_tensor, src_size, inference_box):
      start_time = time.monotonic()
      run_inference(interpreter, input_tensor)
      # For larger input image sizes, use the edgetpu.classification.engine for better performance
      objs = get_objects(interpreter, args.threshold)[:args.top_k]
      end_time = time.monotonic()
      text_lines = [ f'Inference: {round((end_time - start_time) * 1000)} ms' ]
      print(f"\r\033[K{text_lines[0]}", end="") # Print & clear line
      return generate_svg(src_size, inference_box, objs, labels, text_lines)

    result = gstreamer.run_pipeline(user_callback,
                                    src_size=(640, 480),
                                    appsink_size=inference_size,
                                    videosrc=args.videosrc,
                                    videofmt='raw')

if __name__ == '__main__':
    main()
