import logging
import gi
import os

gi.require_version("Gtk", "3.0")
from math import pi
from gi.repository import Gtk, Pango
from ks_includes.screen_panel import ScreenPanel

class Panel(ScreenPanel):
    filament_list = {
        'Generic PLA': ["190","220"],
        'Generic PETG': ["220","260"],
        'Generic PDS': ["190","220"],
        'Generic PET': ["260","300"],
        'MINGDA PLA': ["190","220"],
        'MINGDA PETG': ["220","260"],
        'MINGDA PDS': ["190","220"],
        'MINGDA PET': ["260","300"],
    }
    known_filament_info_list = {
        'Generic': {
            'PLA': ["190","220"],
            'PDS': ["190","220"],
            'PET': ["260","300"],
            'PET-CF': ["265","305"],
        },
        'MINGDA': {
            'PLA': ["180","220"],
            'PDS': ["180","220"],
            'PET': ["260","300"],
            'PETG': ["220","260"],
        },
    }
    def __init__(self, screen, title):
        super().__init__(screen, title)

        logging.info("Init filament info")
        self.filament_info_menu = {}
        self.filament_combo_menu = {}
        self.filament_msg = {
            'name': None,
            'vendor': None,
            'type': None,
            'min_temp': None,
            'max_temp': None,
        }
        self.filament_vendor_option = {
            'section': "main",
            'name': _("Vendor"),
            'type': "dropdown",
            'value': self.filament_msg['vendor'],
            # 'value': None,
            'callback': self.set_filament_vendor,
            'options': [],
        }
        self.filament_type_option = {
            'section': "main",
            'name': _("Type"),
            'type': "dropdown",
            'value': self.filament_msg['type'],
            # 'value': None,
            'callback': self.set_filament_type,
            'options': [],
        }

        self.color_order = 'RGBW'
        self.color_data = [1, 0, 0, 0]
        self.da_size = self._gtk.img_scale * 2
        self.preview = Gtk.DrawingArea(width_request=self.da_size, height_request=self.da_size)
        # self.preview.set_size_request(-1, self.da_size * 2)
        self.preview.connect("draw", self.on_draw)

        if self.known_filament_info_list is not None:
            for key in self.known_filament_info_list.keys():
                self.filament_vendor_option['options'].append({'name': key, 'value': key})
        self.labels['filament_info_l'] = Gtk.Grid()
        self.labels['filament_info_r'] = Gtk.Grid()

        self.grid = self._gtk.HomogeneousGrid()
        self._gtk.reset_temp_color()
        self.filament_msg_box = {}

        self.grid.attach(self.create_left_panel(), 0, 0, 2, 1)
        self.grid.attach(self.create_right_panel(), 2, 0, 2, 1)
        self.show_filament_info()
        self.content.add(self.grid)

    def activate(self):
        logging.info(f"acti:{self._screen.feed_filament_index}")
        if self._screen.feed_filament_index is not None:
            # logging.info(f"1 ==> {self._screen.feed_filament_allinfo[self._screen.feed_filament_index]}")
            self.filament_msg = self._screen.feed_filament_allinfo[int(self._screen.feed_filament_index)]
            self.filament_vendor_option['value'] = self.filament_msg['vendor']
            self.filament_type_option['value'] = self.filament_msg['type']
            self.color_data = self.hex_to_rgbw(self.filament_msg['color'])
            self.preview.queue_draw()
            self.update_option("filament_info_l", self.filament_combo_menu, "vendor", self.filament_vendor_option)
            self.set_filament_vendor(self.filament_msg['vendor'])
            # logging.info(f"2 ==> {self._screen.feed_filament_allinfo[self._screen.feed_filament_index]}")
            # self.update_filment_name_temp()
        # while len(self.menu) > 1:
        #     self.unload_menu()

    def back(self):
        logging.info("back")
        gcode_script_str = "_SET_FILAMENT_INFO"
        if self._screen.feed_filament_index is not None:
            gcode_script_str += f" S={self._screen.feed_filament_index}"
            if self.filament_msg['vendor'] is not None:
                gcode_script_str += f" V={self.filament_msg['vendor']}"
            if self.filament_msg['type'] is not None:
                gcode_script_str += f" T={self.filament_msg['type']}"
            if self.filament_msg['min_temp'] is not None:
                gcode_script_str += f" MIN={self.filament_msg['min_temp']}"
            if self.filament_msg['max_temp'] is not None:
                gcode_script_str += f" MAX={self.filament_msg['max_temp']}"
            if self.filament_msg['color'] is not None:
                gcode_script_str += f" C={self.filament_msg['color']}"
            logging.info(gcode_script_str)
            self._screen._ws.klippy.gcode_script(gcode_script_str)
        # self._screen._ws.klippy.gcode_script("_SAVE_FILAMENT_INFO")
        # if self.filament_msg
        # if len(self.menu) > 1:
        #     self.unload_menu()
        #     return True
        # return False

    def dropdown_changed_event(self, combo, section, option, callback=None):
        tree_iter = combo.get_active_iter()
        if tree_iter is not None:
            model = combo.get_model()
            value = model[tree_iter][1]
            if callback is not None:
                callback(value)
        return

    def set_color_event(self, widget, event):
        logging.info("color_event")
        self._screen.show_panel("feed_filament_color", _("Set Color"))
        return

    def update_filment_name_temp(self):
        self.filament_info_menu['name']['label1'].set_markup(f"{self.filament_msg['name'] if self.filament_msg['name'] is not None else ' '}")
        self.filament_info_menu['temp']['label1'].set_markup(f"{self.filament_msg['min_temp'] if self.filament_msg['min_temp'] is not None else '-'} (°C)")
        self.filament_info_menu['temp']['label3'].set_markup(f"{self.filament_msg['max_temp'] if self.filament_msg['max_temp'] is not None else '-'} (°C)")
        self.labels['filament_info_l'].show_all()
        self.labels['filament_info_r'].show_all()

    def set_filament_vendor(self, vendor_str):
        # name = None
        # logging.info(f"vendor_event:{vendor_str}")

        # if vendor_str is not None:
        # if (self.filament_msg['vendor'] == vendor_str) or (vendor_str not in self.known_filament_info_list):
        #     return False

        self.filament_msg['vendor'] = vendor_str
        # if self.filament_msg['vendor'] is not None:
            # name = self.filament_msg['vendor'] + " " + self.filament_msg['type']

        if (self.filament_msg['vendor'] is not None and
            self.filament_msg['vendor'] in self.known_filament_info_list
        ):
            # update 'Type' ComboBox options
            self.filament_type_option['options'][:] = []
            for key in self.known_filament_info_list[self.filament_msg['vendor']].keys():
                self.filament_type_option['options'].append({'name': key, 'value': key})
            self.update_option("filament_info_r", self.filament_combo_menu, "type", self.filament_type_option)

            #  get 'Name' and 'Temp
            if (self.filament_msg['type'] is not None and
                self.filament_msg['type'] in self.known_filament_info_list[self.filament_msg['vendor']]
            ):
                filament = self.known_filament_info_list[self.filament_msg['vendor']][self.filament_msg['type']]
                self.filament_msg['min_temp'] = filament[0]
                self.filament_msg['max_temp'] = filament[1]
                self.filament_msg['name'] = self.filament_msg['vendor'] + " " + self.filament_msg['type']
            else:
                self.filament_msg['type'] = None
                self.filament_msg['min_temp'] = None
                self.filament_msg['max_temp'] = None
                self.filament_msg['name'] = None
        else:
            self.filament_type_option['options'][:] = []
            self.update_option("filament_info_r", self.filament_combo_menu, "type", self.filament_type_option)
            self.filament_msg['type'] = None
            self.filament_msg['min_temp'] = None
            self.filament_msg['max_temp'] = None
            self.filament_msg['name'] = None

        # if self.filament_msg['type'] is None:
        #     # return True
        #     filament = None
        # else:
        #     filament = self.known_filament_info_list[self.filament_msg['vendor']][self.filament_msg['type']]
        # # if name is not None and (name != self.filament_msg['name']):
        #     # self.filament_msg['name'] = name
        #     # filament = self.filament_list[self.filament_msg['name']]
        #     # filament = self.known_filament_info_list[]
        # if filament is not None:
        #     self.filament_msg['min_temp'] = filament[0]
        #     self.filament_msg['max_temp'] = filament[1]
        # else:
        #     self.filament_msg['min_temp'] = None
        #     self.filament_msg['max_temp'] = None
        # self.show_filament_info()
        # self.filament_info_menu['name']['label1'].set_markup(f"{self.filament_msg['name'] if self.filament_msg['name'] is not None else ' '}")
        # self.filament_info_menu['temp']['label1'].set_markup(f"{self.filament_msg['min_temp'] if self.filament_msg['min_temp'] is not None else '-'} (°C)")
        # self.filament_info_menu['temp']['label3'].set_markup(f"{self.filament_msg['max_temp'] if self.filament_msg['max_temp'] is not None else '-'} (°C)")
        # self.labels['filament_info_l'].show_all()
        # self.labels['filament_info_r'].show_all()
        self.update_filment_name_temp()
        # logging.info(f"vendor_event:{vendor_str}, filament:{self.filament_msg['name']}, {self.filament_msg['min_temp']}, {self.filament_msg['max_temp']}")
        return True

    def set_filament_type(self, type_str):
        # logging.info(f"type_event:{type_str}")
        # name = None
        # if type_str is not None:
        #     self.filament_msg['type'] = type_str
        # if self.filament_msg['vendor'] is not None and self.filament_msg['type'] is not None:
        #     name = self.filament_msg['vendor'] + " " + self.filament_msg['type']
        # if name is not None and (name != self.filament_msg['name']):
        #     self.filament_msg['name'] = name
        #     filament = self.filament_list[self.filament_msg['name']]

        self.filament_msg['type'] = type_str
        if (self.filament_msg['vendor'] is not None and
            self.filament_msg['vendor'] in self.known_filament_info_list and
            self.filament_msg['type'] is not None and
            self.filament_msg['type'] in self.known_filament_info_list[self.filament_msg['vendor']]
        ):
            filament = self.known_filament_info_list[self.filament_msg['vendor']][self.filament_msg['type']]
            self.filament_msg['min_temp'] = filament[0]
            self.filament_msg['max_temp'] = filament[1]
            self.filament_msg['name'] = self.filament_msg['vendor'] + " " + self.filament_msg['type']
        else:
            self.filament_msg['min_temp'] = None
            self.filament_msg['max_temp'] = None
            self.filament_msg['name'] = None
        self.update_filment_name_temp()
        # logging.info(f"type_event:{type_str}, filament:{self.filament_msg['name']}, {self.filament_msg['min_temp']}, {self.filament_msg['max_temp']}")
        return

    def set_filament_info(self):
        return

    def show_filament_info(self):
        self.show_filament_name()
        self.show_filament_temp()
        self.show_filament_color()
        return

    def show_filament_color(self):
        self.filament_info_menu['color'] = {
            'name': Gtk.Label(),
            'button': self._gtk.Button(),
            'dev1': Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5),
            'dev2': Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5),
        }
        self.filament_msg_box['color'] = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        name = self.filament_info_menu['color']['name']
        name.set_markup(f"<big><b>{_('Color')}: </b></big>")
        name.set_hexpand(True)
        name.set_vexpand(True)
        name.set_halign(Gtk.Align.START)
        name.set_valign(Gtk.Align.CENTER)
        name.set_line_wrap(True)
        name.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self.filament_msg_box['color'].add(name)


        dev = self.filament_info_menu['color']['dev1']
        dev.get_style_context().add_class("frame-item")
        dev.set_hexpand(True)
        dev.set_vexpand(False)
        dev.set_valign(Gtk.Align.CENTER)
        dev.add(self.filament_msg_box['color'])

        color_btn = self.filament_info_menu['color']['button']
        color_btn.connect("button-release-event", self.set_color_event)
        color_btn.set_halign(Gtk.Align.END)
        color_btn.set_image(self.preview)
        dev2 = self.filament_info_menu['color']['dev2']
        dev2.get_style_context().add_class("frame-item")
        dev2.set_hexpand(True)
        dev2.set_vexpand(False)
        dev2.set_valign(Gtk.Align.CENTER)
        dev2.add(color_btn)

        self.labels['filament_info_l'].insert_row(4)
        self.labels['filament_info_l'].attach(dev, 0, 4, 1, 1)
        self.labels['filament_info_l'].show_all()
        self.labels['filament_info_r'].insert_row(4)
        self.labels['filament_info_r'].attach(dev2, 0, 4, 1, 1)
        self.labels['filament_info_r'].show_all()
        return

    def show_filament_temp(self):
        # filament_name = self.filament_msg['name']
        min_temp = self.filament_msg['min_temp'] if self.filament_msg['min_temp'] is not None else '-'
        max_temp = self.filament_msg['max_temp'] if self.filament_msg['max_temp'] is not None else '-'
        self.filament_info_menu['temp'] = {
            'name': Gtk.Label(),
            'dev_l': Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5),
            'dev_r': Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5),
            'box1': Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL),
            'box2': Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL),
            'box3': Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL),
            'label1': Gtk.Label(),
            'label2': Gtk.Label(),
            'label3': Gtk.Label(),
        }

        self.filament_msg_box['temp'] = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        name = self.filament_info_menu['temp']['name']
        name.set_markup(f"<big><b>{_('Temperature')}: </b></big>")
        name.set_hexpand(True)
        name.set_vexpand(True)
        name.set_halign(Gtk.Align.START)
        name.set_valign(Gtk.Align.CENTER)
        name.set_line_wrap(True)
        name.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self.filament_msg_box['temp'].add(name)

        dev = self.filament_info_menu['temp']['dev_l']
        dev.get_style_context().add_class("frame-item")
        dev.set_hexpand(True)
        dev.set_vexpand(False)
        dev.set_valign(Gtk.Align.CENTER)
        dev.add(self.filament_msg_box['temp'])

        # btn = Gtk.Button()
        # btn.get_style_context().add_class("numpad_key")
        # btn.set_label(f"{min_temp}")
        # dev.add(btn)

        # box = Gtk.Box()
        # box.set_vexpand(False)
        # label = Gtk.Label(f"{min_temp}")
        # box.get_style_context().add_class("numpad_key")
        # box.add(label)
        # dev.add(box)

        dev2 = self.filament_info_menu['temp']['dev_r']
        dev2.get_style_context().add_class("frame-item")
        dev2.set_hexpand(True)
        dev2.set_vexpand(False)
        dev2.set_valign(Gtk.Align.CENTER)
        grid = self._gtk.HomogeneousGrid()

        label1 = self.filament_info_menu['temp']['label1']
        label1.set_markup(f"{min_temp} (°C)")
        label1.set_hexpand(True)
        label1.set_vexpand(True)
        label1.set_halign(Gtk.Align.CENTER)
        label1.set_valign(Gtk.Align.CENTER)

        label2 = self.filament_info_menu['temp']['label2']
        label2.set_markup("-")
        label2.set_hexpand(True)
        label2.set_vexpand(True)
        label2.set_halign(Gtk.Align.CENTER)
        label2.set_valign(Gtk.Align.CENTER)

        label3 = self.filament_info_menu['temp']['label3']
        label3.set_markup(f"{max_temp} (°C)")
        label3.set_hexpand(True)
        label3.set_vexpand(True)
        label3.set_halign(Gtk.Align.CENTER)
        label3.set_valign(Gtk.Align.CENTER)

        box1 = self.filament_info_menu['temp']['box1']
        box2 = self.filament_info_menu['temp']['box2']
        box3 = self.filament_info_menu['temp']['box3']
        box1.get_style_context().add_class("numpad_key")
        # box2.get_style_context().add_class("numpad_key")
        box3.get_style_context().add_class("numpad_key")
        box1.add(label1)
        box2.add(label2)
        box3.add(label3)
        grid.attach(box1, 0, 0, 1, 1)
        grid.attach(box2, 1, 0, 1, 1)
        grid.attach(box3, 2, 0, 1, 1)
        dev2.add(grid)
        
        self.labels['filament_info_l'].insert_row(3)
        self.labels['filament_info_l'].attach(dev, 0, 3, 1, 1)
        self.labels['filament_info_l'].show_all()
        self.labels['filament_info_r'].insert_row(3)
        self.labels['filament_info_r'].attach(dev2, 0, 3, 1, 1)
        self.labels['filament_info_r'].show_all()
        return

    def show_filament_name(self):
        self.filament_info_menu['name'] = {
            'name': Gtk.Label(),
            'dev1': Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5),
            'dev2': Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5),
            'box1': Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL),
            'label1': Gtk.Label(),
        }
        self.filament_msg_box['name'] = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        filament_name = self.filament_msg['name']
        name = self.filament_info_menu['name']['name']
        name.set_markup(f"<big><b>{_('Name')}: </b></big>")
        name.set_hexpand(True)
        name.set_vexpand(True)
        name.set_halign(Gtk.Align.START)
        name.set_valign(Gtk.Align.CENTER)
        name.set_line_wrap(True)
        name.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self.filament_msg_box['name'].add(name)

        dev = self.filament_info_menu['name']['dev1']
        dev.get_style_context().add_class("frame-item")
        dev.set_hexpand(True)
        dev.set_vexpand(False)
        dev.set_valign(Gtk.Align.CENTER)
        dev.add(self.filament_msg_box['name'])
        
        label1 = self.filament_info_menu['name']['label1']
        label1.set_markup(f"{filament_name if filament_name is not None else ' '}")
        label1.set_hexpand(True)
        label1.set_vexpand(True)
        label1.set_halign(Gtk.Align.CENTER)
        label1.set_valign(Gtk.Align.CENTER)
        # label1.get_style_context().add_class("numpad_key")

        box1 =self.filament_info_menu['name']['box1']
        box1.get_style_context().add_class("numpad_key")
        box1.add(label1)

        dev2 = self.filament_info_menu['name']['dev2']
        dev2.get_style_context().add_class("frame-item")
        dev2.set_hexpand(True)
        dev2.set_vexpand(False)
        dev2.set_valign(Gtk.Align.CENTER)
        dev2.add(box1)

        self.labels['filament_info_l'].insert_row(2)
        self.labels['filament_info_l'].attach(dev, 0, 2, 1, 1)
        self.labels['filament_info_r'].attach(dev2, 0, 2, 1, 1)
        self.labels['filament_info_l'].show_all()
        self.labels['filament_info_r'].show_all()
        return

    def create_left_panel(self):
        # self.left_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        
        scroll = self._gtk.ScrolledWindow(steppers=False)
        scroll.set_policy(Gtk.PolicyType.ALWAYS, Gtk.PolicyType.AUTOMATIC)
        # scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.ALWAYS)
        scroll.get_style_context().add_class('heater-list')
        scroll.add(self.labels['filament_info_l'])

        self.left_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.left_panel.add(scroll)

        self.add_option("filament_info_l", self.filament_combo_menu, "vendor", self.filament_vendor_option)
        
        return self.left_panel

    def create_right_panel(self):
        # self.right_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        scroll = self._gtk.ScrolledWindow(steppers=False)
        scroll.set_policy(Gtk.PolicyType.ALWAYS, Gtk.PolicyType.AUTOMATIC)
        # scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.ALWAYS)
        scroll.get_style_context().add_class('heater-list')
        scroll.add(self.labels['filament_info_r'])

        self.right_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.right_panel.add(scroll)

        if self.filament_msg['vendor'] in self.known_filament_info_list:
            self.filament_type_option['options'][:] = []
            for key in self.known_filament_info_list[self.filament_msg['vendor']].keys():
                self.filament_type_option['options'].append({'name': str(key), 'value': str(key)})
        self.add_option("filament_info_r", self.filament_combo_menu, "type", self.filament_type_option)
        return self.right_panel

    def update_option(self, boxname, opt_array, opt_name, option):
        # logging.info(f"update_option:{opt_name} ==> {opt_array[opt_name]}")
        if opt_name not in opt_array or opt_array[opt_name]['module'] is None:
            # logging.info(f"update error:{opt_array[opt_name]}")
            return False

        dropdown = opt_array[opt_name]['module']
        dropdown.remove_all()
        for i, opt in enumerate(option['options']):
            # logging.info(f"update_option: {i}")
            dropdown.append(opt['value'], opt['name'])
            # if opt['value'] == self._config.get_config()[option['section']].get(opt_name, option['value']):
            if (self.filament_msg[opt_name] is not None) and (opt['value'] == self.filament_msg[opt_name]):
                # logging.info(f"set_active0: {i}==>{opt['value']}")
                dropdown.set_active(i)
                # logging.info(f"set_active1: {i}==>{opt['value']}")
        # opt_array[opt_name]
        self.labels[boxname].show_all()
        # logging.info("update_option end")
        return True

    def add_option(self, boxname, opt_array, opt_name, option):
        if option['type'] is None:
            return
        name = Gtk.Label()
        name.set_markup(f"<big><b>{option['name']}</b></big>")
        name.set_hexpand(True)
        name.set_vexpand(True)
        name.set_halign(Gtk.Align.START)
        name.set_valign(Gtk.Align.CENTER)
        name.set_line_wrap(True)
        name.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)

        labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        labels.add(name)

        dev = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        dev.get_style_context().add_class("frame-item")
        dev.set_hexpand(True)
        dev.set_vexpand(False)
        dev.set_valign(Gtk.Align.CENTER)

        dev.add(labels)
        module = None
        if option['type'] == "binary":
            switch = Gtk.Switch()
            switch.set_active(self._config.get_config().getboolean(option['section'], opt_name))
            switch.connect("notify::active", self.switch_config_option, option['section'], opt_name,
                           option['callback'] if "callback" in option else None)
            dev.add(switch)
        elif option['type'] == "dropdown":
            dropdown = Gtk.ComboBoxText()
            for i, opt in enumerate(option['options']):
                dropdown.append(opt['value'], opt['name'])
                if (self.filament_msg[opt_name] is not None) and (opt['value'] == self.filament_msg[opt_name]):
                    dropdown.set_active(i)
            dropdown.connect("changed", self.dropdown_changed_event, option['section'], opt_name,
                             option['callback'] if "callback" in option else None)
            dropdown.set_entry_text_column(0)
            module = dropdown
            dev.add(dropdown)
        elif option['type'] == "scale":
            dev.set_orientation(Gtk.Orientation.VERTICAL)
            scale = Gtk.Scale.new_with_range(orientation=Gtk.Orientation.HORIZONTAL,
                                             min=option['range'][0], max=option['range'][1], step=option['step'])
            scale.set_hexpand(True)
            scale.set_value(int(self._config.get_config().get(option['section'], opt_name, fallback=option['value'])))
            scale.set_digits(0)
            scale.connect("button-release-event", self.scale_moved, option['section'], opt_name)
            dev.add(scale)
        elif option['type'] == "printer":
            box = Gtk.Box()
            box.set_vexpand(False)
            label = Gtk.Label(f"{option['moonraker_host']}:{option['moonraker_port']}")
            box.add(label)
            dev.add(box)
        elif option['type'] == "menu":
            open_menu = self._gtk.Button("settings", style="color3")
            open_menu.connect("clicked", self.load_menu, option['menu'], option['name'])
            open_menu.set_hexpand(False)
            open_menu.set_halign(Gtk.Align.END)
            dev.add(open_menu)
        elif option['type'] == "lang":
            select = self._gtk.Button("load", style="color3")
            select.connect("clicked", self._screen.change_language, option['code'])
            select.set_hexpand(False)
            select.set_halign(Gtk.Align.END)
            dev.add(select)

        # if opt_name in opt_array:
        #     opt_array[opt_name].clear()
        #     opt_array[opt_name]['name'] = option['name']
        #     opt_array[opt_name]['row'] = dev
        # else:
        opt_array[opt_name] = {
            'name': option['name'],
            'row': dev,
            'module': module,
            'pos': 0
        }
        # logging.info(f"opt_array:{opt_array}")
        # logging.info(f"option:{option}")

        opts = sorted(list(opt_array), key=lambda x: opt_array[x]['name'])
        # logging.info(f"opts:{opts}, ")
        pos = opts.index(opt_name)
        # opt_array[opt_name]['pos'] = pos

        self.labels[boxname].insert_row(pos)
        self.labels[boxname].attach(opt_array[opt_name]['row'], 0, pos, 1, 1)
        self.labels[boxname].show_all()

    def on_draw(self, da, ctx, color=None):
        if color is None:
            color = self.color_data
            # logging.info("on_draw, None")
            # return
        logging.info(f"on_draw, {color}")
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
