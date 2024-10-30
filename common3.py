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
        self.io.write(self.SVG_HEADER.format(w=size[0], h=size[1]))

    def add_rect(self, x, y, w, h, stroke, stroke_width):
        self.io.write(self.SVG_RECT.format(x=x, y=y, w=w, h=h, s=stroke, sw=stroke_width))

    def add_text(self, x, y, text, font_size):
        self.io.write(self.SVG_TEXT.format(x=x, y=y, t=text, fs=font_size))

    def finish(self):
        self.io.write(self.SVG_FOOTER)
        return self.io.getvalue()

class Feed(Gtk.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect('activate', self.on_activate)
        self.pipeline = None
        self.user_function = None  # Placeholder for the user function
        self.src_size = None       # Placeholder for source size
        self.sink_size = None
        self.gstsample = None
        self.condition = threading.Condition()
        self.running = False
        self.overlay = None
        self.mainloop = GLib.MainLoop()

    def run_pipeline(self, user_function, src_size, appsink_size, videosrc='/dev/video0', videofmt='raw', headless=False):
        self.user_function = user_function
        self.src_size = src_size
        
        # Construct the GStreamer pipeline
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
        
        self.pipeline = Gst.parse_launch(pipeline)
        self.overlay = self.pipeline.get_by_name('overlay')
        
        # Set up appsink signals
        appsink = self.pipeline.get_by_name('appsink')
        appsink.connect('new-preroll', self.on_new_sample, True)
        appsink.connect('new-sample', self.on_new_sample, False)

        # Set up a pipeline bus watch to catch errors.
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self.on_bus_msg)

        # Start inference worker.
        self.running = True
        worker = threading.Thread(target=self.inference_loop)
        worker.start()

        # Run pipeline.
        self.pipeline.set_state(Gst.State.PLAYING)

        try:
            #self.run()
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

    def on_activate(self, app):
        print("<<< CREATING WINDOW >>>")
        # Create a window
        self.window = Gtk.ApplicationWindow(application=app)
        self.window.set_title("Classibin")
        self.window.set_default_size(800, 600)

        # Create a Gtk.Box and a Gtk.Picture to display the video
        self.video = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.picture = Gtk.Picture.new()
        self.video.append(self.picture)

        # Set the video box as the window's child
        self.window.set_child(self.video)

        # Present the window
        self.window.present()

        # Set up a bus to listen for messages from the pipeline
        self.bus = self.pipeline.get_bus()
        self.bus.add_watch(GLib.PRIORITY_DEFAULT, self.on_bus_msg)

    def on_bus_msg(self, bus, msg):
        match msg.type:
            case Gst.MessageType.EOS:
                print("End of stream")
                self.quit()
            case Gst.MessageType.ERROR:
                err, debug = msg.parse_error()
                print(f"Error: {err}, Debug: {debug}")
                self.quit()
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
            svg = self.user_function(gstbuffer, self.src_size)
            if svg:
                if self.overlay:
                    self.overlay.set_property('data', svg)

def run_pipeline(user_function, src_size, appsink_size, videosrc='/dev/video0', videofmt='raw', headless=False):
    app = Feed(application_id="com.jaydenlo08.Classibin")
    app.run_pipeline(user_function, src_size, appsink_size, videosrc, videofmt, headless)
