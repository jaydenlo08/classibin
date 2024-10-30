import sys
import gi

gi.require_version('Gst', '1.0')
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gst, GLib

class Feed(Gtk.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect('activate', self.on_activate)
        Gst.init(None)

    def on_activate(self, app):
        # Create a window
        self.window = Gtk.ApplicationWindow(application=app)
        self.window.set_title("Classibin")
        self.window.set_default_size(800, 600)

        # Initialize video pipeline
        self.pipeline = Gst.Pipeline.new()
        self.videoSrc = Gst.ElementFactory.make('v4l2src', None)
        self.videoSrc.set_property("device", "/dev/video0")
        
        # Create elements for the pipeline
        self.convert = Gst.ElementFactory.make('videoconvert', None)
        self.gtksink = Gst.ElementFactory.make('gtk4paintablesink', None)

        # Create a bin to hold the sink and convert elements
        self.sink = Gst.Bin.new()
        self.sink.add(self.convert)
        self.sink.add(self.gtksink)

        # Link the convert and gtksink elements
        self.convert.link(self.gtksink)
        
        # Add a ghost pad to the sink bin
        self.sink.add_pad(Gst.GhostPad.new('sink', self.convert.get_static_pad('sink')))

        # Add elements to the pipeline
        self.pipeline.add(self.videoSrc)
        self.pipeline.add(self.sink)

        # Link the video source to the sink
        self.videoSrc.link(self.sink)

        # Create a Gtk.Box and a Gtk.Picture to display the video
        self.video = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.picture = Gtk.Picture.new()
        self.picture.set_paintable(self.gtksink.get_property('paintable'))
        self.video.append(self.picture)

        # Set the video box as the window's child
        self.window.set_child(self.video)

        # Set the pipeline state to playing
        self.pipeline.set_state(Gst.State.PLAYING)

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

    def on_close(self):
        self.pipeline.set_state(Gst.State.NULL)
        self.quit()

app = Feed(application_id="com.jaydenlo08.Classibin")
app.run(sys.argv)

