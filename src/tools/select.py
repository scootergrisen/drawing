# select.py

from gi.repository import Gtk, Gdk, Gio, GdkPixbuf
import cairo

from .tools import ToolTemplate

class ToolSelect(ToolTemplate):
	__gtype_name__ = 'ToolSelect'

	def __init__(self, window, **kwargs):
		super().__init__('select', _("Selection"), 'edit-select-symbolic', window)

		self.add_tool_action('unselect', self.action_unselect) # pareil que give_back_control ?
		self.add_tool_action('cut', self.action_cut)
		self.add_tool_action('copy', self.action_copy)
		self.add_tool_action('selection_delete', self.action_selection_delete)
		# self.add_tool_action('selection_crop', self.action_selection_crop)
		self.add_tool_action('selection_resize', self.action_selection_resize)
		# self.add_tool_action('selection_rotate', self.action_selection_rotate)
		self.add_tool_action('selection_export', self.action_selection_export)
		self.add_tool_action('import', self.action_import)
		self.add_tool_action('paste', self.action_paste)
		self.add_tool_action('select_all', self.action_select_all)

		#############################

		self.x_press = 0.0
		self.y_press = 0.0
		self.past_x = [-1, -1]
		self.past_y = [-1, -1]

		builder = Gtk.Builder.new_from_resource('/com/github/maoschanz/Drawing/tools/ui/select.ui')
		menu_r = builder.get_object('right-click-menu')
		self.rightc_popover = Gtk.Popover.new_from_model(self.window.drawing_area, menu_r)
		menu_l = builder.get_object('left-click-menu')
		self.selection_popover = Gtk.Popover.new_from_model(self.window.drawing_area, menu_l)

		#############################

		# Building the widget containing options
		self.options_box = builder.get_object('options-menu')

		radio_btn1 = builder.get_object('type_btn_1')
		radio_btn2 = builder.get_object('type_btn_2')

		radio_btn1.connect('clicked', self.on_option_changed, 'rectangle')
		radio_btn2.connect('clicked', self.on_option_changed, 'freehand')
		# radio_btn3.connect('clicked', self.on_option_changed, 'color')

		self.transp_switch = builder.get_object('transparency-switch')

		self.selected_type_id = 'rectangle'
		self.selected_type_label = _("Rectangle")

	def on_option_changed(self, b):
		self.selected_type_label = b.get_label()

	def get_options_widget(self):
		return self.options_box

	def get_options_label(self):
		return self.selected_type_label

	def give_back_control(self):
		print('selection give back control')
		self.restore_pixbuf()
		self.window._pixbuf_manager.delete_temp()
		self.window._pixbuf_manager.show_selection_content()
		self.end_selection()
		return False

	def show_popover(self, state):
		self.selection_popover.popdown()
		self.rightc_popover.popdown()
		if self.window._pixbuf_manager.selection_is_active and state:
			self.selection_popover.popup()
		elif state:
			self.window._pixbuf_manager.selection_x = self.rightc_popover.get_pointing_to()[1].x
			self.window._pixbuf_manager.selection_y = self.rightc_popover.get_pointing_to()[1].y
			self.rightc_popover.popup()

	def on_motion_on_area(self, area, event, surface):
		pass

	def on_press_on_area(self, area, event, surface, tool_width, left_color, right_color):
		print("press")
		area.grab_focus()
		self.x_press = event.x
		self.y_press = event.y
		self.left_color = left_color
		self.right_color = right_color

	def on_release_on_area(self, area, event, surface):
		print("release") # TODO à main levée c'est juste un crayon avec close_path() après
		if event.button == 3:
			rectangle = Gdk.Rectangle()
			rectangle.x = int(event.x)
			rectangle.y = int(event.y)
			rectangle.height = 1
			rectangle.width = 1
			self.rightc_popover.set_pointing_to(rectangle)
			self.rightc_popover.set_relative_to(area)
			self.show_popover(True)
			return
		else:
			# If nothing is selected (only -1), coordinates should be memorized, but
			# if something is already selected, the selection should be cancelled (the
			# action is performed outside of the current selection), or stay the same
			# (the user is moving the selection by dragging it).
			if not self.window._pixbuf_manager.selection_is_active:
				self.past_x[0] = event.x
				self.past_x[1] = self.x_press
				self.past_y[0] = event.y
				self.past_y[1] = self.y_press
				self.selection_popover.set_relative_to(area)
				self.create_selection_from_coord()
				if self.window._pixbuf_manager.selection_is_active:
					self.draw_selection_area(True)
			elif self.window._pixbuf_manager.point_is_in_selection(self.x_press, self.y_press):
				self.drag_to(event.x, event.y)
			else:
				self.give_back_control()
				return

	def get_center_of_selection(self):
		x = self.window._pixbuf_manager.selection_x + \
		self.window._pixbuf_manager.selection_pixbuf.get_width()/2
		y = self.window._pixbuf_manager.selection_y + \
		self.window._pixbuf_manager.selection_pixbuf.get_height()/2
		return [x, y]

	def create_selection_from_coord(self):
		x0 = self.past_x[0]
		x1 = self.past_x[1]
		y0 = self.past_y[0]
		y1 = self.past_y[1]
		if self.past_x[0] > self.past_x[1]:
			x0 = self.past_x[1]
			x1 = self.past_x[0]
		if self.past_y[0] > self.past_y[1]:
			y0 = self.past_y[1]
			y1 = self.past_y[0]
		self.window._pixbuf_manager.create_selection_from_main(x0, y0, x1, y1)

	def draw_selection_area(self, show):
		self.row.set_active(True)
		self.window._pixbuf_manager.show_selection_rectangle()
		self.set_popover_position()
		self.show_popover(show)

	def set_popover_position(self):
		rectangle = Gdk.Rectangle()
		[rectangle.x, rectangle.y] = self.get_center_of_selection()
		rectangle.height = 1
		rectangle.width = 1
		self.selection_popover.set_pointing_to(rectangle)

	def end_selection(self):
		self.apply_to_pixbuf()
		self.show_popover(False)
		self.x_press = 0.0
		self.y_press = 0.0
		self.past_x = [-1, -1]
		self.past_y = [-1, -1]

	def drag_to(self, final_x, final_y):
		self.restore_pixbuf()
		delta_x = final_x - self.x_press
		delta_y = final_y - self.y_press
		self.past_x[0] += delta_x
		self.past_x[1] += delta_x
		self.past_y[0] += delta_y
		self.past_y[1] += delta_y
		self.window._pixbuf_manager.selection_x += delta_x
		self.window._pixbuf_manager.selection_y += delta_y
		self.window._pixbuf_manager.show_selection_rectangle()
		self.set_popover_position()
		self.non_destructive_show_modif()

	def action_import(self, *args):
		file_chooser = Gtk.FileChooserNative.new(_("Import a picture"), self.window,
			Gtk.FileChooserAction.OPEN,
			_("Import"),
			_("Cancel"))
		allPictures = Gtk.FileFilter()
		allPictures.set_name(_("All pictures"))
		allPictures.add_mime_type('image/png')
		allPictures.add_mime_type('image/jpeg')
		allPictures.add_mime_type('image/bmp')
		file_chooser.add_filter(allPictures)
		response = file_chooser.run()
		if response == Gtk.ResponseType.ACCEPT:
			fn = file_chooser.get_filename()
			self.window._pixbuf_manager.selection_pixbuf = GdkPixbuf.Pixbuf.new_from_file(fn)
			self.window._pixbuf_manager.create_selection_from_selection()
			self.draw_selection_area(False)
			self.non_destructive_show_modif()
		file_chooser.destroy()

	def action_cut(self, *args):
		self.window._pixbuf_manager.cut_operation()
		self.show_popover(False)
		self.apply_to_pixbuf()

	def action_copy(self, *args):
		self.window._pixbuf_manager.copy_operation()

	def action_paste(self, *args):
		self.window._pixbuf_manager.paste_operation()
		self.draw_selection_area(False)
		self.non_destructive_show_modif()

	def action_select_all(self, *args):
		self.window._pixbuf_manager.select_all()
		self.draw_selection_area(True)

	def action_unselect(self, *args):
		self.give_back_control()
		self.non_destructive_show_modif()

	def action_cancel_select(self, *args): # TODO utile à connecter quelque part ?
		self.window._pixbuf_manager.reset_selection()
		self.show_popover(False)
		self.non_destructive_show_modif()

	def action_selection_delete(self, *args):
		self.window._pixbuf_manager.delete_operation()
		self.end_selection()
		self.window._pixbuf_manager.reset_selection()

	def action_selection_resize(self, *args):
		self.window.scale_pixbuf(True)

	def action_selection_crop(self, *args): # TODO
		print("selection_crop")

	def action_selection_rotate(self, *args): # TODO
		print("selection_rotate")

	def action_selection_export(self, *args):
		self.window._pixbuf_manager.export_selection_as()
