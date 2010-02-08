#!/usr/bin/python
#
# Urwid example lazy directory browser / tree view
#    Copyright (C) 2004-2009  Ian Ward
#
#    This library is free software; you can redistribute it and/or
#    modify it under the terms of the GNU Lesser General Public
#    License as published by the Free Software Foundation; either
#    version 2.1 of the License, or (at your option) any later version.
#
#    This library is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public
#    License along with this library; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# Urwid web site: http://excess.org/urwid/

"""
Urwid example lazy directory browser / tree view

Features:
- custom selectable widgets for files and directories
- custom message widgets to identify access errors and empty directories
- custom list walker for displaying widgets in a tree fashion
- outputs a quoted list of files and directories "selected" on exit
"""


import urwid

import os


class TreeWidget(urwid.WidgetWrap):
    """A widget representing something in the file tree."""
    def __init__(self, parent, name, index, display):
        self.parent = parent
        self.name = name
        self.index = index
        self.depth = self.calc_depth()

        widget = self.get_indented_widget(display)
        self.widget = widget
        w = urwid.AttrWrap(widget, None)
        self.__super.__init__(w)
        self.selected = False
        self.update_w()

    def calc_depth(self):
        """virtual method. define in sub class"""
        pass
        
    def get_indented_widget(self, display):
        return urwid.Text(["  "*self.depth, display])
    
    def selectable(self):
        return True
    
    def keypress(self, size, key):
        """Toggle selected on space, ignore other keys."""

        if key == " ":
            self.selected = not self.selected
            self.update_w()
        else:
            return key

    def update_w(self):
        """Update the attributes of self.widget based on self.selected.
        """
        if self.selected:
            self.get_w().attr = 'selected'
            self.get_w().focus_attr = 'selected focus'
        else:
            self.get_w().attr = 'body'
            self.get_w().focus_attr = 'focus'
        
    def first_child(self):
        """Default to have no children."""
        return None
    
    def last_child(self):
        """Default to have no children."""
        return None
    
    def next_inorder(self):
        """Return the next TreeWidget depth first from this one."""
        
        child = self.first_child()
        if child: 
            return child
        else:
            parent = self.get_parent()
            return parent.next_inorder_from(self.index)

    def get_parent(self):
        return self.parent
        
    def prev_inorder(self):
        """Return the previous TreeWidget depth first from this one."""
        
        parent = self.get_parent()
        return parent.prev_inorder_from(self.index)


class ParentWidget(TreeWidget):
    """Widget for an interior tree node."""

    def __init__(self, parent, name, index ):
        self.__super.__init__(parent, name, index, "")
        
        self.expanded = True
        
        self.update_widget()
    
    def update_widget(self):
        """Update display widget text."""
        
        if self.expanded:
            mark = "+"
        else:
            mark = "-"
        self.widget.set_text( ["  "*(self.depth),
            ('dirmark', mark), " ", self.name] )

    def keypress(self, size, key ):
        """Handle expand & collapse requests."""
        
        if key in ("+", "right"):
            self.expanded = True
            self.update_widget()
        elif key == "-":
            self.expanded = False
            self.update_widget()
        else:
            return self.__super.keypress(size, key)
    
    def mouse_event(self, (maxcol,), event, button, col, row, focus):
        if event != 'mouse press' or button!=1:
            return False

        if row == 0 and col == 2*self.depth:
            self.expanded = not self.expanded
            self.update_widget()
            return True
        
        return False
    
    def first_child(self):
        """Return first child if expanded."""
        if not self.expanded: 
            return None
        as_parent = self.self_as_parent()
        return as_parent.get_first()
        
    def last_child(self):
        """Return last child if expanded."""
        
        if not self.expanded:
            return None
        as_parent = self.self_as_parent()
        widget = as_parent.get_last()
        sub = widget.last_child()
        if sub is not None:
            return sub
        return widget

    def self_as_parent(self):
        """Return self as a parent object."""
        # virtual function.  implement in base class
        pass


class ParentNode(object):
    """Store sorted tree contents and cache TreeWidget objects."""
    def __init__(self, key):
        self.key = key
        self.widgets = {}

        self.items = self.get_items()
        # if no items, put a dummy None item in the list
        if not self.items:
            self.items = [None]

    def get_widget(self, key):
        """Return the widget for a given key.  Create if necessary."""
        
        if self.widgets.has_key(key):
            return self.widgets[key]
        
        constructor = self.get_constructor(key)
        index = self.items.index(key)
        widget = constructor(self.path, key, index)
        
        self.widgets[key] = widget
        return widget

    def get_constructor(self, key):
        """Return a constructor for the widget associated with the key"""
        pass

    def next_inorder_from(self, index):
        """Return the TreeWidget following index depth first."""
    
        index += 1
        # try to get the next item at same level
        if index < len(self.items):
            return self.get_widget(self.items[index])
            
        # ...otherwise need to go up a level
        parent = self.get_parent()
        if parent is None:
            # we're at the root, so give up
            return None
        else:
            # find my location in parent, and return next inorder
            mywidget = parent.get_widget(self.key)
            return parent.next_inorder_from(mywidget.index)

    def prev_inorder_from(self, index):
        """Return the TreeWidget preceeding index depth first."""
        
        index -= 1
        if index >= 0:
            widget = self.get_widget(self.items[index])
            widget_child = widget.last_child()
            if widget_child: 
                return widget_child
            else:
                return widget

        # need to go up a level
        parent = self.get_parent()
        if parent is None:
            # we're at the root, so give up
            return None
        else:
            # find myself in parent, and return
            return parent.get_widget(self.key)

    def get_first(self):
        """Return the first TreeWidget in the directory."""
        
        return self.get_widget(self.items[0])
    
    def get_last(self):
        """Return the last TreeWIdget in the directory."""
        
        return self.get_widget(self.items[-1])
        


class TreeWalker(urwid.ListWalker):
    """ListWalker-compatible class for browsing directories.
    
    positions used are directory,filename tuples."""
    
    def __init__(self, start_from):
        widget = start_from.get_first()
        self.focus = start_from, widget.name

    def get_focus(self):
        parent, key = self.focus
        widget = parent.get_widget(key)
        return widget, self.focus
        
    def set_focus(self, focus):
        parent, key = focus
        self.focus = parent, key
        self._modified()
    
    def get_next(self, start_from):
        parent, key = start_from
        try:
            widget = parent.get_widget(key)
        except:
            raise RuntimeError(parent)
        target = widget.next_inorder()
        if target is None:
            return None, None
        return target, (target.dir, target.name)

    def get_prev(self, start_from):
        parent, key = start_from
        widget = parent.get_widget(key)
        target = widget.prev_inorder()
        if target is None:
            return None, None
        return target, (target.dir, target.name)


