#!/usr/bin/python
#
#  Generic TreeWidget/TreeWalker class 
#    Original version:
#      Urwid example lazy directory browser / tree view
#      Copyright (C) 2004-2009  Ian Ward
#    Copied and adapted by Rob Lanphier
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
Urwid tree view

Features:
- custom selectable widgets for trees
- custom list walker for displaying widgets in a tree fashion
"""


import urwid

import os


class TreeWidgetError(RuntimeError):
    pass


class TreeWidget(urwid.WidgetWrap):
    """A widget representing something in the file tree."""
    def __init__(self, parent, key, value):
        self._parent = parent
        self._key = key
        self._value = value
        self.depth = self.calc_depth()

        widget = self.get_indented_widget()

        w = urwid.AttrWrap(widget, None)
        self.__super.__init__(w)
        self.selected = False
        self.update_w()

    def calc_depth(self):
        """virtual method. define in sub class"""
        if self.get_parent() is None:
            return 0
        else:
            return self.get_parent().get_depth() + 1
        
    def get_indented_widget(self):
        leftmargin = urwid.Text("")
        widgetlist = [self.get_widget()]
        if self.depth > 0:
            widgetlist.insert(0, ('fixed', self.get_indent_cols(), leftmargin))
        return urwid.Columns(widgetlist)

    def get_indent_cols(self):
        return 3 * self.depth

    def get_widget(self):
        self._innerwidget = urwid.Text(self.get_display_text())
        return self._innerwidget

    def get_display_text(self):
        return str(self.get_value())

    def get_key(self):
        return self._key

    def get_value(self):
        return self._value
        
    def get_index(self):
        parent = self.get_parent()
        key = self.get_key()
        return parent.get_child_index(key)

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
            return parent.next_inorder_from(self.get_index())

    def get_parent(self):
        return self._parent
        
    def prev_inorder(self):
        """Return the previous TreeWidget depth first from this one."""

        parent = self.get_parent()
        if self.is_root():
            return None
        else:
            return parent.prev_inorder_from(self.get_index())
    
    def is_root(self):
        """Is this widget at the root of the tree?"""
        return self.get_key() is None


class ParentWidget(TreeWidget):
    """Widget for an interior tree node."""

    def __init__(self, parent, key, value):
        self.__super.__init__(parent, key, value)
        
        self.expanded = True
        
        self.update_widget()
    
    def update_widget(self):
        """Update display widget text."""
        
        if self.expanded:
            mark = "-"
        else:
            mark = "+"
        self._innerwidget.set_text([('dirmark', mark), " ", self.get_display_text()] )

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
    
    def mouse_event(self, size, event, button, col, row, focus):
        if event != 'mouse press' or button!=1:
            return False

        if row == 0 and col == self.get_indent_cols():
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
        return parent.get_child_node(self.get_key())


class ParentNode(object):
    """Store sorted tree contents and cache TreeWidget objects."""
    def __init__(self, value, parent=None, key=None):
        self._key = key
        self._parent = parent
        self._value = value
        # this will only be set if this node is the root
        self._widget = None
        self.widgets = {}
        self.subtrees = {}

        self.items = self.get_items()
        # if no items, put a dummy None item in the list
        if not self.items:
            self.items = [None]

    def get_widget(self):
        parent = self.get_parent()
        if self._widget is not None:
            return self._widget
        elif self.get_parent() is None:
            constructor = \
                self.get_root_widget()
            self._widget = constructor(self, None, self._value) 
            return self._widget
        else:
            return parent.get_child_widget(self.get_key())

    def get_child_widget(self, key):
        """Return the widget for a given key.  Create if necessary."""
        
        if key is None:
            return self.get_widget()

        if self.widgets.has_key(key):
            return self.widgets[key]

        constructor = self.get_widget_constructor_for_child(key)
        widget = constructor(self, key, self.get_child_value(key))
        
        self.widgets[key] = widget
        return widget

    def get_child_value(self, key):
        # virtual function. implement in sub class
        raise TreeWidgetError("unimplemented function get_child_value in %s" %
                              str(self.__class__))

    def get_child_index(self, key):
        if key is None:
            # we're at the root
            return None
        else:
            try:
                return self.items.index(key)
            except ValueError:
                errorstring = ("Can't find key %s in ParentNode %s\n" +
                               "ParentNode items: %s")
                raise TreeWidgetError(errorstring % (key, self.get_key(), 
                                      str(self.get_items())))

    def get_widget_constructor_for_child(self, key):
        """
        Return a TreeWidget constructor for the widget associated with the key.
        """
        # virtual function. implement in sub class
        pass
    
    def get_subtree(self, key):
        """Return the subtree for a given key.  Create if necessary."""
        
        if self.subtrees.has_key(key):
            return self.subtrees[key]

        if key is None:
            return self

        constructor = self.get_subtree_constructor(key)
        subtree = constructor(self.get_child_value(key), parent=self, key=key)
        
        self.subtrees[key] = subtree
        return subtree

    def get_subtree_constructor(self, key):
        """
        Return a ParentNode constructor for the subtree associated with the 
        key.
        """
        return self.__class__

    def next_inorder_from(self, index):
        """Return the TreeWidget following index depth first."""
    
        if index is None:
            # we're at the root
            return self.get_first()
        index += 1
        # try to get the next item at same level
        if index < len(self.items):
            return self.get_child_widget(self.items[index])
            
        # ...otherwise need to go up a level
        parent = self.get_parent()
        if parent is None:
            # we're at the root, so give up
            return None
        else:
            # find my location in parent, and return next inorder
            mywidget = parent.get_child_widget(self.get_key())
            return parent.next_inorder_from(mywidget.get_index())

    def prev_inorder_from(self, index):
        """Return the TreeWidget preceeding index depth first."""
        
        index -= 1
        if index >= 0:
            widget = self.get_child_widget(self.items[index])
            widget_child = widget.last_child()
            if widget_child: 
                return widget_child
            else:
                return widget

        # need to go up a level
        parent = self.get_parent()
        if parent is None:
            # we're at the root, so return root widget
            return self.get_widget()
        else:
            # find myself in parent, and return
            return parent.get_child_widget(self.get_key())

    def get_first(self):
        """Return the first TreeWidget in the directory."""
        return self.get_child_widget(self.items[0])
    
    def get_last(self):
        """Return the last TreeWidget in the directory."""
        return self.get_child_widget(self.items[-1])
        
    def get_parent(self):
        return self._parent
        
    def get_key(self):
        return self._key
        
    def get_depth(self):
        parent = self.get_parent()
        if parent is None:
            return 0
        else:
            return parent.get_depth() + 1

class TreeWalker(urwid.ListWalker):
    """ListWalker-compatible class for browsing directories.
    
    positions used are directory,filename tuples."""
    
    def __init__(self, start_from):
        """start_from: ParentNode at the root of the tree."""
        widget = start_from.get_widget()
        if start_from.get_parent() is None:
            self.focus = start_from, widget.get_key()
        else:
            self.focus = start_from.get_parent(), widget.get_key()

    def get_focus(self):
        parent, key = self.focus
        widget = parent.get_child_widget(key)
        return widget, self.focus
        
    def set_focus(self, focus):
        parent, key = focus
        self.focus = parent, key
        self._modified()
    
    def get_next(self, start_from):
        parent, key = start_from
        widget = parent.get_child_widget(key)
        target = widget.next_inorder()
        if target is None:
            return None, None
        return target, (target.get_parent(), target.get_key())

    def get_prev(self, start_from):
        parent, key = start_from
        widget = parent.get_child_widget(key)
        target = widget.prev_inorder()
        if target is None:
            return None, None
        return target, (target.get_parent(), target.get_key())


