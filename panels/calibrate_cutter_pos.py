import re
import logging
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Pango
from ks_includes.KlippyGcodes import KlippyGcodes
from ks_includes.screen_panel import ScreenPanel


class Panel(ScreenPanel):
    distances = ['.01', '.05', '0.1', '0.5', '1', '5', '10']
    distance = distances[-2]

    def __init__(self, screen, title):
        super().__init__(screen, title)

        if self.ks_printer_cfg is not None:
            dis = self.ks_printer_cfg.get("move_distances", '0.01, 0.05, 0.1, 0.5, 1, 5, 10')
            if re.match(r'^[0-9,\.\s]+$', dis):
                dis = [str(i.strip()) for i in dis.split(',')]
                if 1 < len(dis) <= 7:
                    self.distances = dis
                    self.distance = self.distances[-2]

        self.pos = {}
        self.pos['x'] = 0
        self.pos['y'] = 0
        self.pos['z'] = 0
        self.settings = {}
        self.menu = ['move_menu']
        self.buttons = {
            'x+': self._gtk.Button("arrow-right", "X+", "color1"),
            'x-': self._gtk.Button("arrow-left", "X-", "color1"),
            'y+': self._gtk.Button("arrow-up", "Y+", "color2"),
            'y-': self._gtk.Button("arrow-down", "Y-", "color2"),
            'z+': self._gtk.Button("z-farther", "Z+", "color3"),
            'z-': self._gtk.Button("z-closer", "Z-", "color3"),
            'start': self._gtk.Button("start", _("Start"), "color4"),
            'save': self._gtk.Button("complete", _("Confirm"), "color4"),
        }
        self.buttons['x+'].connect("clicked", self.move, "X", "+")
        self.buttons['x-'].connect("clicked", self.move, "X", "-")
        self.buttons['y+'].connect("clicked", self.move, "Y", "+")
        self.buttons['y-'].connect("clicked", self.move, "Y", "-")
        self.buttons['z+'].connect("clicked", self.move, "Z", "+")
        self.buttons['z-'].connect("clicked", self.move, "Z", "-")
        self.buttons['start'].connect("clicked", self.start)
        self.buttons['save'].connect("clicked", self.save)
        self.buttons['save'].set_sensitive(False)
        # adjust = self._gtk.Button("settings", None, "color2", 1, Gtk.PositionType.LEFT, 1)
        # adjust.connect("clicked", self.load_menu, 'options', _('Settings'))
        # adjust.set_hexpand(False)
        grid = self._gtk.HomogeneousGrid()
        if self._screen.vertical_mode:
            if self._screen.lang_ltr:
                grid.attach(self.buttons['x+'], 2, 1, 1, 1)
                grid.attach(self.buttons['x-'], 0, 1, 1, 1)
                grid.attach(self.buttons['z+'], 2, 2, 1, 1)
                grid.attach(self.buttons['z-'], 0, 2, 1, 1)
            else:
                grid.attach(self.buttons['x+'], 0, 1, 1, 1)
                grid.attach(self.buttons['x-'], 2, 1, 1, 1)
                grid.attach(self.buttons['z+'], 0, 2, 1, 1)
                grid.attach(self.buttons['z-'], 2, 2, 1, 1)
            # grid.attach(adjust, 1, 2, 1, 1)
            grid.attach(self.buttons['y+'], 1, 0, 1, 1)
            grid.attach(self.buttons['y-'], 1, 1, 1, 1)

        else:
            if self._screen.lang_ltr:
                grid.attach(self.buttons['x+'], 2, 1, 1, 1)
                grid.attach(self.buttons['x-'], 0, 1, 1, 1)
            else:
                grid.attach(self.buttons['x+'], 0, 1, 1, 1)
                grid.attach(self.buttons['x-'], 2, 1, 1, 1)
            grid.attach(self.buttons['y+'], 1, 0, 1, 1)
            grid.attach(self.buttons['y-'], 1, 1, 1, 1)
            grid.attach(self.buttons['z+'], 3, 0, 1, 1)
            grid.attach(self.buttons['z-'], 3, 1, 1, 1)

        grid.attach(self.buttons['start'], 0, 0, 1, 1)
        grid.attach(self.buttons['save'], 2, 0, 1, 1)

        distgrid = Gtk.Grid()
        for j, i in enumerate(self.distances):
            self.labels[i] = self._gtk.Button(label=i)
            self.labels[i].set_direction(Gtk.TextDirection.LTR)
            self.labels[i].connect("clicked", self.change_distance, i)
            ctx = self.labels[i].get_style_context()
            if (self._screen.lang_ltr and j == 0) or (not self._screen.lang_ltr and j == len(self.distances) - 1):
                ctx.add_class("distbutton_top")
            elif (not self._screen.lang_ltr and j == 0) or (self._screen.lang_ltr and j == len(self.distances) - 1):
                ctx.add_class("distbutton_bottom")
            else:
                ctx.add_class("distbutton")
            if i == self.distance:
                ctx.add_class("distbutton_active")
            distgrid.attach(self.labels[i], j, 0, 1, 1)

        for p in ('pos_x', 'pos_y', 'pos_z'):
            self.labels[p] = Gtk.Label()
        self.labels['move_dist'] = Gtk.Label(_("Move Distance (mm)"))

        bottomgrid = self._gtk.HomogeneousGrid()
        bottomgrid.set_direction(Gtk.TextDirection.LTR)
        bottomgrid.attach(self.labels['pos_x'], 0, 0, 1, 1)
        bottomgrid.attach(self.labels['pos_y'], 1, 0, 1, 1)
        bottomgrid.attach(self.labels['pos_z'], 2, 0, 1, 1)
        bottomgrid.attach(self.labels['move_dist'], 0, 1, 3, 1)
        # if not self._screen.vertical_mode:
        #     bottomgrid.attach(adjust, 3, 0, 1, 2)

        self.labels['move_menu'] = self._gtk.HomogeneousGrid()
        self.labels['move_menu'].attach(grid, 0, 0, 1, 3)
        self.labels['move_menu'].attach(bottomgrid, 0, 3, 1, 1)
        self.labels['move_menu'].attach(distgrid, 0, 4, 1, 1)

        self.content.add(self.labels['move_menu'])

        printer_cfg = self._printer.get_config_section("printer")
        # The max_velocity parameter is not optional in klipper config.
        max_velocity = int(float(printer_cfg["max_velocity"]))
        if max_velocity <= 1:
            logging.error(f"Error getting max_velocity\n{printer_cfg}")
            max_velocity = 50
        if "max_z_velocity" in printer_cfg:
            max_z_velocity = max(int(float(printer_cfg["max_z_velocity"])), 10)
        else:
            max_z_velocity = max_velocity

        configurable_options = [
            {"invert_x": {"section": "main", "name": _("Invert X"), "type": "binary", "value": "False"}},
            {"invert_y": {"section": "main", "name": _("Invert Y"), "type": "binary", "value": "False"}},
            {"invert_z": {"section": "main", "name": _("Invert Z"), "type": "binary", "value": "False"}},
            {"move_speed_xy": {
                "section": "main", "name": _("XY Speed (mm/s)"), "type": "scale", "value": "50",
                "range": [1, max_velocity], "step": 1}},
            {"move_speed_z": {
                "section": "main", "name": _("Z Speed (mm/s)"), "type": "scale", "value": "10",
                "range": [1, max_z_velocity], "step": 1}}
        ]

        self.labels['options_menu'] = self._gtk.ScrolledWindow()
        self.labels['options'] = Gtk.Grid()
        self.labels['options_menu'].add(self.labels['options'])
        for option in configurable_options:
            name = list(option)[0]
            self.add_option('options', self.settings, name, option[name])

    def process_update(self, action, data):
        if action != "notify_status_update":
            return
        homed_axes = self._printer.get_stat("toolhead", "homed_axes")
        if homed_axes == "xyz":
            if "gcode_move" in data and "gcode_position" in data["gcode_move"]:
                self.labels['pos_x'].set_text(f"X: {data['gcode_move']['gcode_position'][0]:.2f}")
                self.labels['pos_y'].set_text(f"Y: {data['gcode_move']['gcode_position'][1]:.2f}")
                self.labels['pos_z'].set_text(f"Z: {data['gcode_move']['gcode_position'][2]:.2f}")
                self.pos['x'] = data['gcode_move']['gcode_position'][0]
                self.pos['y'] = data['gcode_move']['gcode_position'][1]
                self.pos['z'] = data['gcode_move']['gcode_position'][2]
        else:
            if "x" in homed_axes:
                if "gcode_move" in data and "gcode_position" in data["gcode_move"]:
                    self.labels['pos_x'].set_text(f"X: {data['gcode_move']['gcode_position'][0]:.2f}")
                    self.pos['x'] = data['gcode_move']['gcode_position'][0]
            else:
                self.labels['pos_x'].set_text("X: ?")
            if "y" in homed_axes:
                if "gcode_move" in data and "gcode_position" in data["gcode_move"]:
                    self.labels['pos_y'].set_text(f"Y: {data['gcode_move']['gcode_position'][1]:.2f}")
                    self.pos['y'] = data['gcode_move']['gcode_position'][1]                    
            else:
                self.labels['pos_y'].set_text("Y: ?")
            if "z" in homed_axes:
                if "gcode_move" in data and "gcode_position" in data["gcode_move"]:
                    self.labels['pos_z'].set_text(f"Z: {data['gcode_move']['gcode_position'][2]:.2f}")
                    self.pos['z'] = data['gcode_move']['gcode_position'][2]
            else:
                self.labels['pos_z'].set_text("Z: ?")

    def change_distance(self, widget, distance):
        logging.info(f"### Distance {distance}")
        self.labels[f"{self.distance}"].get_style_context().remove_class("distbutton_active")
        self.labels[f"{distance}"].get_style_context().add_class("distbutton_active")
        self.distance = distance

    def move(self, widget, axis, direction):
        if self._config.get_config()['main'].getboolean(f"invert_{axis.lower()}", False):
            direction = "-" if direction == "+" else "+"

        dist = f"{direction}{self.distance}"
        config_key = "move_speed_z" if axis == "Z" else "move_speed_xy"
        speed = None if self.ks_printer_cfg is None else self.ks_printer_cfg.getint(config_key, None)
        if speed is None:
            speed = self._config.get_config()['main'].getint(config_key, 20)
        speed = 60 * max(1, speed)
        script = f"{KlippyGcodes.MOVE_RELATIVE}\nG0 {axis}{dist} F{speed}"
        self._screen._send_action(widget, "printer.gcode.script", {"script": script})
        if self._printer.get_stat("gcode_move", "absolute_coordinates"):
            self._screen._ws.klippy.gcode_script("G90")

    def add_option(self, boxname, opt_array, opt_name, option):
        name = Gtk.Label()
        name.set_markup(f"<big><b>{option['name']}</b></big>")
        name.set_hexpand(True)
        name.set_vexpand(True)
        name.set_halign(Gtk.Align.START)
        name.set_valign(Gtk.Align.CENTER)
        name.set_line_wrap(True)
        name.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)

        dev = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        dev.get_style_context().add_class("frame-item")
        dev.set_hexpand(True)
        dev.set_vexpand(False)
        dev.set_valign(Gtk.Align.CENTER)
        dev.add(name)

        if option['type'] == "binary":
            box = Gtk.Box()
            box.set_vexpand(False)
            switch = Gtk.Switch()
            switch.set_hexpand(False)
            switch.set_vexpand(False)
            switch.set_active(self._config.get_config().getboolean(option['section'], opt_name))
            switch.connect("notify::active", self.switch_config_option, option['section'], opt_name)
            switch.set_property("width-request", round(self._gtk.font_size * 7))
            switch.set_property("height-request", round(self._gtk.font_size * 3.5))
            box.add(switch) 
            dev.add(box)
        elif option['type'] == "scale":
            dev.set_orientation(Gtk.Orientation.VERTICAL)
            scale = Gtk.Scale.new_with_range(orientation=Gtk.Orientation.HORIZONTAL,
                                             min=option['range'][0], max=option['range'][1], step=option['step'])
            scale.set_hexpand(True)
            scale.set_value(int(self._config.get_config().get(option['section'], opt_name, fallback=option['value'])))
            scale.set_digits(0)
            scale.connect("button-release-event", self.scale_moved, option['section'], opt_name)
            dev.add(scale)

        opt_array[opt_name] = {
            "name": option['name'],
            "row": dev
        }

        opts = sorted(list(opt_array), key=lambda x: opt_array[x]['name'])
        pos = opts.index(opt_name)

        self.labels[boxname].insert_row(pos)
        self.labels[boxname].attach(opt_array[opt_name]['row'], 0, pos, 1, 1)
        self.labels[boxname].show_all()

    def back(self):
        if len(self.menu) > 1:
            self.unload_menu()
            return True
        return False

    def start(self, widget):
        self._screen._ws.klippy.gcode_script("BED_MESH_CLEAR")
        if self._printer.get_stat("toolhead", "homed_axes") != "xyz":
            self._screen._ws.klippy.gcode_script("G28")
        current_extruder = self._printer.get_stat("toolhead", "extruder")
        if current_extruder != "extruder":
            self._screen._ws.klippy.gcode_script("T0")
        try:
            x_position = self._screen.klippy_config.getfloat("Variables", "cutter_xpos")
            y_position = self._screen.klippy_config.getfloat("Variables", "cutter_ypos")
            z_position = self._screen.klippy_config.getfloat("Variables", "cutter_zpos")
        except:
            self._screen.show_popup_message(_("Couldn't get the calibration cutter position."))
            logging.error("Couldn't get the calibration cutter position.")
            return
    
        logging.info(f"Moving to X:{x_position} Y:{y_position}")
        script = [
            f"{KlippyGcodes.MOVE_ABSOLUTE}",
            f"G1 Z{z_position} F600\n",
            f"G1 X{x_position} Y{y_position} F6000\n",
        ]
        self._screen._send_action(widget, "printer.gcode.script", {"script": "\n".join(script)})  
        self.buttons['save'].set_sensitive(True)    

    def save(self, widget):
        buttons = [
            {"name": _("Cut Filament Test"), "response": Gtk.ResponseType.APPLY},
            {"name": _("Save & Restart"), "response": Gtk.ResponseType.OK},
            {"name": _("Cancel"), "response": Gtk.ResponseType.CANCEL}
        ]
        
        # 创建一个Label控件而不是直接使用字符串
        label = Gtk.Label()
        label.set_markup(_("Please select how you would like to proceed."))
        label.set_line_wrap(True)
        label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        label.set_halign(Gtk.Align.CENTER)
        label.set_valign(Gtk.Align.CENTER)
        
        dialog = self._gtk.Dialog(
            self._screen,
            buttons,
            label,  # 传入Label控件
            self._handle_save_action
        )
        dialog.set_title(_("Options"))
            
    def _handle_save_action(self, widget, response):
        if response == Gtk.ResponseType.APPLY:
            # 执行切刀测试
            self._screen._send_action(
                None,
                "printer.gcode.script",
                {"script": "_CUT_FILAMENT"}
            )
        elif response == Gtk.ResponseType.OK:
            # 保存并重启
            self.save_config()
        
        # 关闭对话框
        if widget:
            widget.destroy()

    def save_config(self):        
        try:
            # 打印值和类型信息进行调试
            logging.info(f"X position: {self.pos['x']}")
            logging.info(f"Y position: {self.pos['y']}")
            logging.info(f"Z position: {self.pos['z']}")
            
            save_cmd = (
                "G91\n"                    # 设置相对坐标
                "G1 X-20 F3000\n"         # X轴左移20mm
                "G90\n"                    # 恢复绝对坐标
                f'SAVE_VARIABLE VARIABLE=cutter_ypos VALUE={self.pos["y"]:.2f}\n'
                f'SAVE_VARIABLE VARIABLE=cutter_zpos VALUE={self.pos["z"]:.2f}\n'
                'SAVE_CONFIG'
            )
            
            self._screen._ws.klippy.gcode_script(save_cmd)
        except Exception as e:
            logging.error(f"Error saving variables: {e}")
            self._screen.show_popup_message(_("Error writing configuration"))
                  