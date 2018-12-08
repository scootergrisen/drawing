# crop_dialog.py
#
# Copyright 2018 Romain F. T.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from gi.repository import Gtk, Gdk, Gio, GdkPixbuf
from .gi_composites import GtkTemplate
import cairo

class DrawingCropDialog(Gtk.Dialog):
	__gtype_name__ = 'DrawingCropDialog'

	def __init__(self, window, o_width, o_height, forbid_growth):
		wants_csd = ( window._settings.get_string('decorations') != 'ssd' )
		super().__init__(modal=True, use_header_bar=wants_csd, title=_("Crop the picture"), transient_for=window)
		self._window = window
		self.original_width = o_width
		self.original_height = o_height
		self.forbid_growth = forbid_growth
		self.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
		self.add_button(_("Apply"), Gtk.ResponseType.APPLY)
		builder = Gtk.Builder.new_from_resource('/com/github/maoschanz/Drawing/ui/crop_dialog.ui')
		crop_content_area = builder.get_object('crop_content_area')
		self.get_content_area().add(crop_content_area)
		self.preview = builder.get_object('preview')
		self.height_btn = builder.get_object('height_btn')
		self.width_btn = builder.get_object('width_btn')
		self.preview.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | \
			Gdk.EventMask.BUTTON_RELEASE_MASK | Gdk.EventMask.POINTER_MOTION_MASK)
		self.preview.connect('draw', self.on_draw)
		self.preview.connect('button-press-event', self.on_press)
		self.preview.connect('button-release-event', self.on_release)
		if self._window.get_pixbuf_width() > self._window.get_pixbuf_height():
			w = 500
			h = 500*(self._window.get_pixbuf_height()/self._window.get_pixbuf_width())
		else:
			w = 500*(self._window.get_pixbuf_width()/self._window.get_pixbuf_height())
			h = 500
		self.pixbuf = self._window._pixbuf_manager.main_pixbuf.scale_simple(w, h, GdkPixbuf.InterpType.TILES)
		self.surface = Gdk.cairo_surface_create_from_pixbuf(self.pixbuf, 0, None)
		self.preview.set_size_request(self.surface.get_width(), self.surface.get_height())
		self.set_resizable(False)

		self.width_btn.connect('value-changed', self.on_width_changed)
		self.height_btn.connect('value-changed', self.on_height_changed)
		self._x = 0
		self._y = 0
		if self.forbid_growth:
			self.width_btn.set_range(1, self.original_width)
			self.height_btn.set_range(1, self.original_height)
			w = self._window.drawing_area.get_allocated_width()
			h = self._window.drawing_area.get_allocated_height()
		else:
			w = self._window.get_pixbuf_width()
			h = self._window.get_pixbuf_height()
		self.width_btn.set_value(w)
		self.height_btn.set_value(h)

	def on_apply(self, *args):
		x = self._x
		y = self._y
		width = self.get_width()
		height = self.get_height()
		self._window._pixbuf_manager.resize_main_surface(x, y, width, height)
		self._window._pixbuf_manager.on_tool_finished()
		self.destroy()

	def on_cancel(self, *args):
		self.destroy()

	def on_draw(self, area, cairo_context):
		cairo_context.set_source_surface(self.surface, 0, 0)
		cairo_context.paint()

	def on_width_changed(self, *args):
		if self.forbid_growth:
			self.check_coord()
		self.draw_overlay()

	def on_height_changed(self, *args):
		if self.forbid_growth:
			self.check_coord()
		self.draw_overlay()

	def get_width(self):
		return self.width_btn.get_value_as_int()

	def get_height(self):
		return self.height_btn.get_value_as_int()

	def convert_to_preview_coord(self, x, y):
		preview_x = (x / self.original_width) * self.pixbuf.get_width()
		preview_y = (y / self.original_height) * self.pixbuf.get_height()
		return [preview_x, preview_y]

	def convert_from_preview_coord(self, x, y):
		preview_x = (x / self.pixbuf.get_width()) * self.original_width
		preview_y = (y / self.pixbuf.get_height()) * self.original_height
		return [preview_x, preview_y]

	def draw_overlay(self): # XXX même si on grandit ??
		self.surface = Gdk.cairo_surface_create_from_pixbuf(self.pixbuf, 0, None)
		w_context = cairo.Context(self.surface)

		x1, y1 = self.convert_to_preview_coord(self._x, self._y)
		x2, y2 = self.convert_to_preview_coord(self._x + self.get_width(), self._y + self.get_height())

		w_context.move_to(x1, y1)
		w_context.line_to(x2, y1)
		w_context.line_to(x2, y2)
		w_context.line_to(x1, y2)
		w_context.close_path()
		w_context.clip_preserve()
		w_context.set_source_rgba(0.1, 0.1, 0.3, 0.3)
		w_context.paint()
		w_context.stroke()

		self.preview.queue_draw()

	def on_press(self, area, event):
		self.old_x = event.x
		self.old_y = event.y

	def on_release(self, area, event):
		x, y = self.convert_from_preview_coord(event.x - self.old_x, event.y - self.old_y)
		self._x += x
		self._y += y
		self.check_coord()
		self.draw_overlay()

	def check_coord(self):
		if self._x < 0:
			self._x = 0
		elif self._x > self.original_width - self.get_width():
			self._x = self.original_width - self.get_width()
		if self._y < 0:
			self._y = 0
		elif self._y > self.original_height - self.get_height():
			self._y = self.original_height - self.get_height()

