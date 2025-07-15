import logging
import re
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Pango
from ks_includes.KlippyGcodes import KlippyGcodes
from ks_includes.screen_panel import ScreenPanel


class Panel(ScreenPanel):

    def __init__(self, screen, title):
        super().__init__(screen, title)
        self.current_extruder = self._printer.get_stat("toolhead", "extruder")
        # 添加错误处理和默认值
        try:
            self.current_tool = self._screen.klippy_config.getint("Variables", "feed_system_active_tool", fallback=1)
        except (AttributeError, KeyError):
            self.current_tool = 1  # 如果获取失败则默认使用T0
            logging.info("Unable to get feed_system_active_tool, defaulting to T0")
        self.multi_material_enabled = True if self.current_tool > 0 else False
        self.previous_tool = self.current_tool

        # 通过检查可用命令来确定支持的工具号
        self.available_tools = []
        available_commands = self._printer.available_commands
        for i in range(10):  # 检查T0到T9
            if f"T{i}" in available_commands:
                self.available_tools.append(i)
        
        if not self.available_tools and "extruder" in self._printer.get_tools():
            self.available_tools.append(0)
        
        macros = self._printer.get_config_section_list("gcode_macro ")
        self.load_filament = any("LOAD_FILAMENT" in macro.upper() for macro in macros)
        self.unload_filament = any("UNLOAD_FILAMENT" in macro.upper() for macro in macros)

        self.speeds = ['2', '5']
        self.distances = ['10', '25', '50', '100']
        if self.ks_printer_cfg is not None:
            dis = self.ks_printer_cfg.get("extrude_distances", '10, 25, 50, 100')
            if re.match(r'^[0-9,\s]+$', dis):
                dis = [str(i.strip()) for i in dis.split(',')]
                if 1 < len(dis) < 5:
                    self.distances = dis
            vel = self.ks_printer_cfg.get("extrude_speeds", '2, 5')
            if re.match(r'^[0-9,\s]+$', vel):
                vel = [str(i.strip()) for i in vel.split(',')]
                if 1 < len(vel) < 5:
                    self.speeds = vel

        self.distance = int(self.distances[1])
        self.speed = int(self.speeds[1])
        self.buttons = {
            'extrude': self._gtk.Button("extrude", _("Load"), "color4"),
            'load': self._gtk.Button("arrow-down", _("Load"), "color3"),
            'unload': self._gtk.Button("retract", _("Unload"), "color2"),
            'retract': self._gtk.Button("retract", _("Unload"), "color1"),
            'temperature': self._gtk.Button("heat-up", _("Preheat"), "color4"),
            'spoolman': self._gtk.Button("spool", _("Filament Settings"), "color3"),
            'multi_material': self._gtk.Button(
                "multi_material_enabled" if self.current_tool > 0 else "multi_material_disable",
                _("Multi-Material Box"),
                "color3"
            ),
        }
        self.buttons['extrude'].connect("clicked", self.extrude, "+")
        self.buttons['load'].connect("clicked", self.load_unload, "+")
        self.buttons['unload'].connect("clicked", self.extrude, "-")
        self.buttons['retract'].connect("clicked", self.extrude, "-")
        self.buttons['temperature'].connect("clicked", self.menu_item_clicked, {
            "name": "Temperature",
            "panel": "temperature"
        })
        self.buttons['spoolman'].connect("clicked", self.menu_item_clicked, {
            "name": "Filament Settings",
            "panel": "feed_filament_box",
            "params": {"current_tool": self.current_tool}
        })
        self.buttons['multi_material'].connect("clicked", self.toggle_multi_material)
        self.buttons['spoolman'].set_sensitive(self.multi_material_enabled > 0)
        
        # 初始化时设置多材料按钮的文本限制
        self._apply_multi_material_text_limit()

        extgrid = self._gtk.HomogeneousGrid()
        limit = 5
        i = 0
        for tool_num in self.available_tools:
            extruder = f"extruder{tool_num}"
            self.labels[extruder] = self._gtk.Button(f"filament-{tool_num}", f"T{tool_num}")
            self.labels[extruder].connect("clicked", self.change_extruder, tool_num + 1)
        
            if i < limit:
                extgrid.attach(self.labels[extruder], i, 0, 1, 1)
                i += 1
        
        if i < (limit - 2) and self._printer.spoolman:
            extgrid.attach(self.buttons['spoolman'], i + 2, 0, 1, 1)
        
        distgrid = Gtk.Grid()
        for j, i in enumerate(self.distances):
            self.labels[f"dist{i}"] = self._gtk.Button(label=i)
            self.labels[f"dist{i}"].connect("clicked", self.change_distance, int(i))
            ctx = self.labels[f"dist{i}"].get_style_context()
            if ((self._screen.lang_ltr is True and j == 0) or
                    (self._screen.lang_ltr is False and j == len(self.distances) - 1)):
                ctx.add_class("distbutton_top")
            elif ((self._screen.lang_ltr is False and j == 0) or
                  (self._screen.lang_ltr is True and j == len(self.distances) - 1)):
                ctx.add_class("distbutton_bottom")
            else:
                ctx.add_class("distbutton")
            if int(i) == self.distance:
                ctx.add_class("distbutton_active")
            distgrid.attach(self.labels[f"dist{i}"], j, 0, 1, 1)

        speedgrid = Gtk.Grid()
        for j, i in enumerate(self.speeds):
            self.labels[f"speed{i}"] = self._gtk.Button(label=i)
            self.labels[f"speed{i}"].connect("clicked", self.change_speed, int(i))
            ctx = self.labels[f"speed{i}"].get_style_context()
            if ((self._screen.lang_ltr is True and j == 0) or
                    (self._screen.lang_ltr is False and j == len(self.speeds) - 1)):
                ctx.add_class("distbutton_top")
            elif ((self._screen.lang_ltr is False and j == 0) or
                  (self._screen.lang_ltr is True and j == len(self.speeds) - 1)):
                ctx.add_class("distbutton_bottom")
            else:
                ctx.add_class("distbutton")
            if int(i) == self.speed:
                ctx.add_class("distbutton_active")
            speedgrid.attach(self.labels[f"speed{i}"], j, 0, 1, 1)

        distbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.labels['extrude_dist'] = Gtk.Label(_("Distance (mm)"))
        distbox.pack_start(self.labels['extrude_dist'], True, True, 0)
        distbox.add(distgrid)
        speedbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.labels['extrude_speed'] = Gtk.Label(_("Speed (mm/s)"))
        speedbox.pack_start(self.labels['extrude_speed'], True, True, 0)
        speedbox.add(speedgrid)

        filament_sensors = self._printer.get_filament_sensors()
        sensors = Gtk.Grid()
        sensors.set_size_request(self._gtk.content_width - 30, -1)
        if len(filament_sensors) > 0:
            sensors.set_column_spacing(5)
            sensors.set_row_spacing(5)
            sensors.set_halign(Gtk.Align.CENTER)
            sensors.set_valign(Gtk.Align.CENTER)
            for s, x in enumerate(filament_sensors):
                if s > limit:
                    break
                name = x[23:].strip()
                self.labels[x] = {
                    'label': Gtk.Label(self.prettify(name)),
                    'switch': Gtk.Switch(),
                    'box': Gtk.Box()
                }
                self.labels[x]['label'].set_halign(Gtk.Align.CENTER)
                self.labels[x]['label'].set_hexpand(True)
                self.labels[x]['label'].set_ellipsize(Pango.EllipsizeMode.END)
                self.labels[x]['switch'].set_property("width-request", round(self._gtk.font_size * 2))
                self.labels[x]['switch'].set_property("height-request", round(self._gtk.font_size))
                self.labels[x]['switch'].connect("notify::active", self.enable_disable_fs, name, x)
                self.labels[x]['box'].pack_start(self.labels[x]['label'], True, True, 10)
                self.labels[x]['box'].pack_start(self.labels[x]['switch'], False, False, 0)
                self.labels[x]['box'].get_style_context().add_class("filament_sensor")
                sensors.attach(self.labels[x]['box'], s, 0, 1, 1)

        grid = Gtk.Grid()
        grid.set_column_homogeneous(True)
        grid.attach(extgrid, 0, 0, 4, 1)

        if self._screen.vertical_mode:
            grid.attach(self.buttons['extrude'], 0, 1, 2, 1)
            grid.attach(self.buttons['retract'], 2, 1, 2, 1)
            grid.attach(self.buttons['load'], 0, 2, 2, 1)
            grid.attach(self.buttons['unload'], 2, 2, 2, 1)
            grid.attach(distbox, 0, 3, 4, 1)
            grid.attach(speedbox, 0, 4, 4, 1)
            grid.attach(sensors, 0, 5, 4, 1)
            grid.attach(self.buttons['multi_material'], 0, 6, 4, 1)  # 添加按钮到布局
        else:
            grid.attach(self.buttons['extrude'], 0, 2, 1, 1)
            # grid.attach(self.buttons['load'], 1, 2, 1, 1)
            grid.attach(self.buttons['unload'], 1, 2, 1, 1)
            grid.attach(self.buttons['multi_material'], 2, 2, 1, 1)  # 添加按钮到布局
            # grid.attach(self.buttons['spoolman'], 2, 2, 1, 1)
            grid.attach(self.buttons['temperature'], 3, 2, 1, 1)
            grid.attach(distbox, 0, 3, 2, 1)
            grid.attach(speedbox, 2, 3, 2, 1)
            grid.attach(sensors, 0, 4, 4, 1)

                # 更新所有按钮状态
        for t_num in self.available_tools:
            extruder = f"extruder{t_num}"
                # T0时禁用所有按钮
            self.labels[extruder].get_style_context().remove_class("button_active")
            if self.current_tool > 0:
                self.labels[extruder].set_sensitive(True)
                if t_num == self.current_tool - 1:
                    self.labels[extruder].get_style_context().add_class("button_active")
            else:
                self.labels[extruder].set_sensitive(False)
        self.content.add(grid)

    def _apply_multi_material_text_limit(self):
        """为横屏模式下的multi_material按钮设置文本限制"""
        if not self._screen.vertical_mode and 'multi_material' in self.buttons:
            from ks_includes.KlippyGtk import find_widget
            label = find_widget(self.buttons['multi_material'], Gtk.Label)
            if label:
                # 对所有语言统一限制为12字符，确保界面一致性
                label.set_max_width_chars(12)
                label.set_ellipsize(Pango.EllipsizeMode.END)
    
    def _update_multi_material_icon(self, enabled):
        """更新多材料按钮的图标，不破坏按钮结构"""
        from ks_includes.KlippyGtk import find_widget
        image = find_widget(self.buttons['multi_material'], Gtk.Image)
        if image:
            icon_name = "multi_material_enabled" if enabled else "multi_material_disable"
            # 直接更新图片的pixbuf，而不是替换整个图片对象
            new_pixbuf = self._gtk.Image(icon_name, self._gtk.img_scale * self._gtk.button_image_scale, 
                                         self._gtk.img_scale * self._gtk.button_image_scale).get_pixbuf()
            if new_pixbuf:
                image.set_from_pixbuf(new_pixbuf)

    def enable_buttons(self, enable):
        for button in self.buttons:
            if button in ("temperature", "spoolman"):
                continue
            self.buttons[button].set_sensitive(enable)

    def activate(self):
        if self._printer.state == "printing":
            self.enable_buttons(False)

    def deactivate(self):
        # 保存当前工具号和多耗材箱状态到文件
        try:
            if self._screen._ws.connected:
                # 使用 SAVE_VARIABLE 命令保存变量
                save_cmd = (
                    f'SAVE_VARIABLE VARIABLE=feed_system_active_tool VALUE={self.current_tool}\n'
                )
                self._screen._ws.klippy.gcode_script(save_cmd)

        except Exception as e:
            logging.error(f"Error saving variables: {e}")

    def process_update(self, action, data):
        if action != "notify_status_update":
            return
            
        for x in self._printer.get_tools():
            if x in data:
                self.update_temp(
                    x,
                    self._printer.get_dev_stat(x, "temperature"),
                    self._printer.get_dev_stat(x, "target"),
                    self._printer.get_dev_stat(x, "power"),
                    lines=2,
                )

        # 检查并更新当前料管
        try:
            if 'save_variables' in data:
                logging.info(f"Extrude panel received save_variables: {data['save_variables']}")
                if 'variables' in data['save_variables']:
                    logging.info(f"Variables content: {data['save_variables']['variables']}")
                    active_tool = data['save_variables']['variables'].get('feed_system_active_tool')
                    if active_tool is not None and active_tool != self.current_tool:
                        logging.info(f"Current tool: {self.current_tool}, New tool: {active_tool}")
                        
                        # 更新按钮状态
                        for t_num in self.available_tools:
                            extruder = f"extruder{t_num}"
                            self.labels[extruder].get_style_context().remove_class("button_active")
                            if active_tool > 0:
                                self.labels[extruder].set_sensitive(True)
                                if t_num == active_tool - 1:
                                    self.labels[extruder].get_style_context().add_class("button_active")
                                    logging.info(f"Setting {extruder} as active")
                            else:
                                self.labels[extruder].set_sensitive(False)
                        
                        # 更新当前工具号
                        self.current_tool = active_tool
                        
                        # 更新多材料盒状态
                        self.multi_material_enabled = active_tool > 0
                        # 使用新方法更新图标
                        self._update_multi_material_icon(self.multi_material_enabled)
                        self.buttons['spoolman'].set_sensitive(self.multi_material_enabled)
                        
        except Exception as e:
            logging.exception(f"Error updating active feed system: {e}")

        for x in self._printer.get_filament_sensors():
            if x in data:
                if 'enabled' in data[x]:
                    self._printer.set_dev_stat(x, "enabled", data[x]['enabled'])
                    self.labels[x]['switch'].set_active(data[x]['enabled'])
                if 'filament_detected' in data[x]:
                    self._printer.set_dev_stat(x, "filament_detected", data[x]['filament_detected'])
                    if self._printer.get_stat(x, "enabled"):
                        if data[x]['filament_detected']:
                            self.labels[x]['box'].get_style_context().remove_class("filament_sensor_empty")
                            self.labels[x]['box'].get_style_context().add_class("filament_sensor_detected")
                        else:
                            self.labels[x]['box'].get_style_context().remove_class("filament_sensor_detected")
                            self.labels[x]['box'].get_style_context().add_class("filament_sensor_empty")
                logging.info(f"{x}: {self._printer.get_stat(x)}")

    def change_distance(self, widget, distance):
        logging.info(f"### Distance {distance}")
        self.labels[f"dist{self.distance}"].get_style_context().remove_class("distbutton_active")
        self.labels[f"dist{distance}"].get_style_context().add_class("distbutton_active")
        self.distance = distance

    def change_extruder(self, widget, tool_num):
        logging.info(f"Changing feed_system_active_tool to {tool_num}")
        
        # 更新所有按钮状态
        for t_num in self.available_tools:
            extruder = f"extruder{t_num}"
                # T0时禁用所有按钮
            self.labels[extruder].get_style_context().remove_class("button_active")
            if tool_num > 0:
                self.labels[extruder].set_sensitive(True)
                if t_num == tool_num - 1:
                    self.labels[extruder].get_style_context().add_class("button_active")
            else:
                self.labels[extruder].set_sensitive(False)
        
        self.current_tool = tool_num
        if tool_num > 0:
            self._screen._send_action(widget, "printer.gcode.script",
                                {"script": f"T{tool_num - 1}"})
    def change_speed(self, widget, speed):
        logging.info(f"### Speed {speed}")
        self.labels[f"speed{self.speed}"].get_style_context().remove_class("distbutton_active")
        self.labels[f"speed{speed}"].get_style_context().add_class("distbutton_active")
        self.speed = speed

    def extrude(self, widget, direction):
        temp = self._printer.get_dev_stat(self.current_extruder, "temperature")
        if temp < 190:
            script = {"script": "M104 S240"}
            self._screen._confirm_send_action(None,
                                              _("The nozzle temperature is too low, Are you sure you want to heat it?"),
                                              "printer.gcode.script", script, save_button=False)
        else:
            self._screen._ws.klippy.gcode_script(KlippyGcodes.EXTRUDE_REL)
            if direction == "-":
                self._screen._ws.klippy.gcode_script("_FEEDSYS_RETRACT_FILAMENT")
            else:
                self._screen._send_action(widget, "printer.gcode.script",
                                  {"script": f"G1 E{direction}{self.distance} F{self.speed * 60}"})


    def load_unload(self, widget, direction):
        if direction == "-":
            if not self.unload_filament:
                self._screen.show_popup_message("Macro UNLOAD_FILAMENT not found")
            else:
                self._screen._send_action(widget, "printer.gcode.script",
                                          {"script": f"UNLOAD_FILAMENT SPEED={self.speed * 60}"})
        if direction == "+":
            if not self.load_filament:
                self._screen.show_popup_message("Macro LOAD_FILAMENT not found")
            else:
                self._screen._send_action(widget, "printer.gcode.script",
                                          {"script": f"LOAD_FILAMENT SPEED={self.speed * 60}"})

    def enable_disable_fs(self, switch, gparams, name, x):
        if switch.get_active():
            self._printer.set_dev_stat(x, "enabled", True)
            self._screen._ws.klippy.gcode_script(f"SET_FILAMENT_SENSOR SENSOR={name} ENABLE=1")
            if self._printer.get_stat(x, "filament_detected"):
                self.labels[x]['box'].get_style_context().add_class("filament_sensor_detected")
            else:
                self.labels[x]['box'].get_style_context().add_class("filament_sensor_empty")
        else:
            self._printer.set_dev_stat(x, "enabled", False)
            self._screen._ws.klippy.gcode_script(f"SET_FILAMENT_SENSOR SENSOR={name} ENABLE=0")
            self.labels[x]['box'].get_style_context().remove_class("filament_sensor_empty")
            self.labels[x]['box'].get_style_context().remove_class("filament_sensor_detected")

    def toggle_multi_material(self, widget):
        if not self.multi_material_enabled:
            label = Gtk.Label()
            label.set_markup(_("Do you want to enable multi-material box?"))
            label.set_line_wrap(True)
            label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
            label.set_halign(Gtk.Align.CENTER)
            label.set_valign(Gtk.Align.CENTER)
            
            buttons = [
                {"name": _("Yes"), "response": Gtk.ResponseType.YES},
                {"name": _("No"), "response": Gtk.ResponseType.NO}
            ]
            
        else:
            # 如果当前是启用状态，显示清理喉管提示
            label = Gtk.Label()
            label.set_markup(_("Do you want to use external filament?"))
            label.set_line_wrap(True)
            label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
            label.set_halign(Gtk.Align.CENTER)
            label.set_valign(Gtk.Align.CENTER)
            
            buttons = [
                {"name": _("Continue"), "response": Gtk.ResponseType.OK},
                {"name": _("Cancel"), "response": Gtk.ResponseType.CANCEL}
            ]
        
        dialog = self._gtk.Dialog(
            self._screen,
            buttons,
            label,
            self._handle_multi_material_toggle
        )
        dialog.set_title(_("Multi-Material") if not self.multi_material_enabled else _("External Filament"))

    def _handle_multi_material_toggle(self, widget, response):
        if widget:
            widget.destroy()
            
        if self.multi_material_enabled:
            # 处理禁用多色耗材箱的响应
            if response == Gtk.ResponseType.OK:
                self.multi_material_enabled = False
                self.previous_tool = self.current_tool
                self.current_tool = 0
                logging.info("Multi-material box disabled")
                self._screen._ws.klippy.gcode_script("ACTIVE_FIALMENT S=0")

                # 更新按钮图标
                # 使用新方法更新图标
                self._update_multi_material_icon(False)
                self.change_extruder(None, self.current_tool)
        else:
            # 处理启用多色耗材箱的响应
            if response == Gtk.ResponseType.YES:
                self.multi_material_enabled = True
                self.current_tool = 1 if self.current_tool == 0 else self.current_tool
                logging.info("Multi-material box enabled")
                # self._screen._ws.klippy.gcode_script(f"ACTIVE_FIALMENT S={self.current_tool}")

                # 更新按钮图标
                # 使用新方法更新图标
                self._update_multi_material_icon(True)
                self.change_extruder(None, self.current_tool)
