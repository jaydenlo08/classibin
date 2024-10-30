import collections
import io
import os
import time
import sys
import threading
import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstBase', '1.0')
gi.require_version('Gtk', '4.0')
from gi.repository import GLib, GObject, Gst, GstBase, Gtk
Gst.init(None)

class SVG:
    # SVG constants
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

class GstPipeline:
    def __init__(self, pipeline, user_function, src_size):
        self.app = Gtk.Application()
        self.app.connect('activate', self.window)
        self.user_function = user_function
        self.running = False
        self.gstsample = None
        self.sink_size = None
        self.src_size = src_size
        self.box = None
        self.condition = threading.Condition()

        self.pipeline = Gst.parse_launch(pipeline)
        self.overlay = self.pipeline.get_by_name('overlay')
        self.mainloop = GLib.MainLoop()

        appsink = self.pipeline.get_by_name('appsink')
        appsink.connect('new-preroll', self.on_new_sample, True)
        appsink.connect('new-sample', self.on_new_sample, False)

        # Set up a pipeline bus watch to catch errors.
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self.on_bus_message)
    
    def run(self):
        # Start inference worker.
        self.running = True
        #self.app.run(sys.argv)
        worker = threading.Thread(target=self.inference_loop)
        worker.start()

        # Run pipeline.
        self.pipeline.set_state(Gst.State.PLAYING)
        
        try:
            self.mainloop.run()
        except KeyboardInterrupt:
            print("\n")
            os._exit(130)
            
        
        # Clean up.
        self.pipeline.set_state(Gst.State.NULL)
        while GLib.MainContext.default().iteration(False):
            pass
        with self.condition:
            self.running = False
            self.condition.notify_all()
        worker.join()

    def window(self, app):
        self.window = Gtk.ApplicationWindow(application=app)
        self.window.set_title("Classibin")
        self.window.set_default_size(800, 600)
        self.display = self.pipeline.get_by_name('display')
        self.video = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.picture = Gtk.Picture.new()
       # self.pipeline.set_state(Gst.State.PLAYING)
        ret, state, pending = self.pipeline.get_state(Gst.CLOCK_TIME_NONE)
        print("Pipeline state:", state)
        self.picture.set_paintable(self.display.get_property('paintable'))
        self.video.append(self.picture)
        self.window.set_child(self.video)
        self.window.present()

    def on_bus_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.EOS:
            self.mainloop.quit()
        elif t == Gst.MessageType.WARNING:
            err, debug = message.parse_warning()
            sys.stderr.write('Warning: %s: %s\n' % (err, debug))
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            sys.stderr.write('Error: %s: %s\n' % (err, debug))
            self.mainloop.quit()
        return True

    def on_new_sample(self, sink, preroll):
        sample = sink.emit('pull-preroll' if preroll else 'pull-sample')
        if not self.sink_size:
            s = sample.get_caps().get_structure(0)
            self.sink_size = (s.get_value('width'), s.get_value('height'))
        with self.condition:
            self.gstsample = sample
            self.condition.notify_all()
        return Gst.FlowReturn.OK

    def get_box(self):
        if not self.box:
            glbox = self.pipeline.get_by_name('glbox')
            if glbox:
                glbox = glbox.get_by_name('filter')
            box = self.pipeline.get_by_name('box')
            assert glbox or box
            assert self.sink_size
            if glbox:
                self.box = (glbox.get_property('x'), glbox.get_property('y'),
                        glbox.get_property('width'), glbox.get_property('height'))
            else:
                self.box = (-box.get_property('left'), -box.get_property('top'),
                    self.sink_size[0] + box.get_property('left') + box.get_property('right'),
                    self.sink_size[1] + box.get_property('top') + box.get_property('bottom'))
        return self.box

    def inference_loop(self):
        while True:
            with self.condition:
                while not self.gstsample and self.running:
                    self.condition.wait()
                    
                if not self.running:
                    break
                gstsample = self.gstsample
                self.gstsample = None

            # Passing Gst.Buffer as input tensor avoids 2 copies of it.
            gstbuffer = gstsample.get_buffer()
            svg = self.user_function(gstbuffer, self.src_size, self.get_box())
            if svg:
                if self.overlay:
                    self.overlay.set_property('data', svg)
        
def run_pipeline(user_function,
                 src_size,
                 appsink_size,
                 videosrc='/dev/video0',
                 videofmt='raw',
                 headless=False):
    pipeline = f'v4l2src device={videosrc} ! video/x-raw,width={src_size[0]},height={src_size[1]},framerate=30/1'
    SINK_ELEMENT = 'appsink name=appsink emit-signals=true max-buffers=1 drop=true'
    sink_caps = f'video/x-raw,format=RGB,width={appsink_size[0]},height={appsink_size[1]}'
    LEAKY_Q = 'queue max-size-buffers=1 leaky=downstream'
    if headless:
        scale = min(appsink_size[0] / src_size[0], appsink_size[1] / src_size[1])
        scale = tuple(int(x * scale) for x in src_size)
        scale_caps = f'video/x-raw,width={scale[0]},height={scale[1]}'

        pipeline += f""" ! decodebin ! queue ! videoconvert ! videoscale
        ! {scale_caps} ! videobox name=box autocrop=true ! {sink_caps} ! {SINK_ELEMENT}
        """
    else:
        scale = min(appsink_size[0] / src_size[0], appsink_size[1] / src_size[1])
        scale = tuple(int(x * scale) for x in src_size)
        scale_caps = f'video/x-raw,width={scale[0]},height={scale[1]}'
        pipeline += f""" ! tee name=t
            t. ! {LEAKY_Q} ! videoconvert ! videoscale ! {scale_caps} ! videobox name=box autocrop=true ! {sink_caps} ! {SINK_ELEMENT}
            t. ! {LEAKY_Q} ! videoconvert ! rsvgoverlay name=overlay ! videoconvert ! gtk4paintablesink name=display
            """
    pipe = GstPipeline(pipeline, user_function, src_size)
    pipe.run()
