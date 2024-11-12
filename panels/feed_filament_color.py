import logging
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from math import pi
from ks_includes.KlippyGcodes import KlippyGcodes
from ks_includes.screen_panel import ScreenPanel

class Panel(ScreenPanel):
    preset_color = [
        [1,1,1,0],
        [0,0,0,0],
        [0.5,0.5,0.5,0],
        [1,0,0,0],
        [1,0.5,0,0],
        [1,1,0,0],
        [0,1,0,0],
        [0,0,1,0],
        [0.3,0,0.8,0],
        [0.5,0,1,0],
        [1,0.75,0.8,0],
        [0.8,0.8,0.4,0],
        [0,0.8,0.4,0],
        [0.8,0,0.4,0],
        [0.6,0.3,0,0],
        [0.5,0.2,0,0],
        [0,0.5,0,0],
        [0,0,0.5,0],
        [0,0.5,0.5,0],
        [0.4,0.2,0.6,0],
        [1, 0, 0.5, 0],
    ]
    def __init__(self, screen, title):
        super().__init__(screen, title)
        self.color_order = 'RGBW'
        self.color_data = [0, 0, 0, 0]
        self.da_size = self._gtk.img_scale * 2
        self.preview = Gtk.DrawingArea(width_request=self.da_size, height_request=self.da_size)
        # self.preview.set_size_request(-1, self.da_size * 2)
        self.preview.connect("draw", self.on_draw)
        self.labels['filament_color'] = Gtk.Grid()
        self.grid = self._gtk.HomogeneousGrid()
        # box = Gtk.Box()
        # box.set_size_request(self.da_size, self.da_size)
        # box.set_image(self.preview)
        self.grid.attach(self.create_title_panel(), 0,0,1,1)
        self.grid.attach(self.create_preset_color_panel(), 0,1,1,3)
        self.content.add(self.grid)

    def activate(self):
        self.color_data = self.hex_to_rgbw(self._screen.feed_filament_allinfo[int(self._screen.feed_filament_index)]['color'])
        self.preview.queue_draw()
        logging.info(f"ac: {self.color_data}")
        return

    def back(self):
        self._screen.feed_filament_allinfo[int(self._screen.feed_filament_index)]['color'] = self.rgb_to_hex(self.color_data)
        logging.info(f"be: {self.rgb_to_hex(self.color_data)}")
        return

    def create_title_panel(self):
        box = Gtk.Box()
        # box.set_size_request(self.da_size, self.da_size)
        # box.set_image(self.preview)
        box.set_halign(Gtk.Align.CENTER)
        box.set_valign(Gtk.Align.CENTER)
        box.add(self.preview)
        self.preview.queue_draw()
        
        return box

    def update_color_data(self, color_data):
        self.color_data = color_data

    def set_color_event(self, widget, event):
        logging.info("color_event")
        self._screen.show_panel("feed_filament_color", _("Set Color"))

    def create_preset_color_panel(self):
        scroll = self._gtk.ScrolledWindow(steppers=False)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        # scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.ALWAYS)
        scroll.get_style_context().add_class('heater-list')

        preset_color_win = self._gtk.HomogeneousGrid()
        preset_color_win.get_style_context().add_class('numpad')
        columns = 4 if self._screen.vertical_mode else 7
        i = 0
        for color in self.preset_color:
            preview = Gtk.DrawingArea(width_request=self.da_size, height_request=self.da_size)
            preview.connect("draw", self.on_draw, color)
            button = self._gtk.Button()
            button.set_image(preview)
            button.connect("button-release-event", self.set_color_event, color)
            button.get_style_context().add_class("numpad_button")
            button.get_style_context().add_class("numpad_key")
            preset_color_win.attach(button, int(i%columns), int(i/columns), 1, 1)
            i += 1


        # self.right_buttons['load'].connect('button-release-event', self.load_event)
        # self.right_buttons['unload'].connect('button-release-event', self.unload_event)
        # self.right_buttons['edit'].connect('button-release-event', self.edit_event)
        # self.labels['filament_box'].show_all()
        scroll.add(preset_color_win)
        return scroll

    def on_draw(self, da, ctx, color=None):
        if color is None:
            color = self.color_data
        ctx.set_source_rgb(*self.rgbw_to_rgb(color))
        # Set the size of the rectangle
        width = height = da.get_allocated_width() * .9
        x = da.get_allocated_width() * .05
        # Set the radius of the corners
        radius = width / 2 * 0.2
        ctx.arc(x + radius, radius, radius, pi, 3 * pi / 2)
        ctx.arc(x + width - radius, radius, radius, 3 * pi / 2, 0)
        ctx.arc(x + width - radius, height - radius, radius, 0, pi / 2)
        ctx.arc(x + radius, height - radius, radius, pi / 2, pi)
        ctx.close_path()
        ctx.fill()

    @staticmethod
    def rgb_to_hex(color):
        hex_color = ''
        for value in color:
            int_value = round(value * 255)
            hex_color += hex(int_value)[2:].zfill(2)
        return hex_color.upper()

    @staticmethod
    def rgbw_to_rgb(color):
        # The idea here is to use the white channel as a saturation control
        # The white channel 'washes' the color
        return (
            [color[3] for i in range(3)]  # Special case of only white channel
            if color[0] == 0 and color[1] == 0 and color[2] == 0
            else [color[i] + (1 - color[i]) * color[3] / 3 for i in range(3)]
        )

    @staticmethod
    def hex_to_rgbw(hex_color):
        color = [0,0,0,0]
        logging.info(f"hexc:{hex_color}")
        if (hex_color is not None) and (len(hex_color)>=6):
            for i in range(int(len(hex_color)/2)):
                color[i] = int(hex_color[i*2:2+i*2], 16)/255
        return color
            

