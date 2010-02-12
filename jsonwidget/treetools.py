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
    def __init__(self, node):
        self._node = node

        widget = self.get_indented_widget()

        w = urwid.AttrWrap(widget, None)
        self.__super.__init__(w)
        self.selected = False
        self._innerwidget = None
        self.update_w()

    def get_indented_widget(self):
        leftmargin = urwid.Text("")
        widgetlist = [self.get_inner_widget()]
        indent_cols = self.get_indent_cols()
        if indent_cols > 0:
            widgetlist.insert(0, ('fixed', indent_cols, leftmargin))
        return urwid.Columns(widgetlist)

    def get_indent_cols(self):
        return 3 * self.get_node().get_depth()

    def get_inner_widget(self):
        if self._innerwidget == None:
            self._innerwidget = self.load_widget()
        return self._innerwidget

    def load_inner_widget(self):
        return urwid.Text(self.get_display_text())
        
    def get_node(self):
        return self._node

    def get_display_text(self):
        return (self.get_node().get_key() + ": " + 
                str(self.get_node().get_value()))

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

    def next_inorder(self):
        """Return the next TreeWidget depth first from this one."""
        # first check if there's a child widget
        firstchild = this.first_child()
        if firstchild is not None:
            return firstchild

        # now we need to hunt for the next sibling
        thisnode = self.get_node()
        nextnode = thisnode.next_sibling()
        depth = thisnode.get_depth()
        while nextnode is None and depth > 0:
            # keep going up the tree until we find an ancestor next sibling
            thisnode = thisnode.get_parent()
            nextnode = thisnode.next_sibling()
            depth -= 1
            assert depth == thisnode.get_depth()
        if nextnode is None:
            # we're at the end of the tree
            return None
        else:
            return nextnode.get_widget()

    def prev_inorder(self):
        """Return the previous TreeWidget depth first from this one."""
        thisnode = self._node
        prevnode = thisnode.prev_sibling()
        if prevnode is not None:
            # we need to find the last child of the previous widget if its
            # expanded
            prevwidget = prevnode.get_widget()
            lastchild = prevwidget.last_child()
            if lastchild is None:
                return prevwidget
            else:
                return lastchild
        else:
            # need to hunt for the parent
            depth = thisnode.get_depth()
            if prevnode is None and depth == 0:
                return None
            elif prevnode is None:
                prevnode = thisnode.get_parent()
            return prevnode.get_widget()

    def first_child(self):
        """Default to have no children."""
        return None
    
    def last_child(self):
        """Default to have no children."""
        return None

class ParentWidget(TreeWidget):
    """Widget for an interior tree node."""

    def __init__(self, node):
        self.__super.__init__(node)
        
        self.expanded = True
        
        self.update_widget()
    
    def update_widget(self):
        """Update display widget text."""
        
        if self.expanded:
            mark = "-"
        else:
            mark = "+"
        self._innerwidget.set_text([('dirmark', mark), " ", self.get_display_text()] )

    def keypress(self, size, key):
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
        else:
            firstnode = self._node.get_first_child()
            return firstnode.get_widget()

    def last_child(self):
        """Return last child if expanded."""
        if not self.expanded:
            return None
        else:
            lastchild = self._node.get_last_child().get_widget()
            # recursively search down for the last descendant
            lastdescendant = lastchild.last_child()
            if lastdescendant is None:
                return lastchild
            else:
                return lastdescendant


class TreeNode(object):
    """
    Store tree contents and cache TreeWidget objects.  
    A TreeNode consists of the following elements:
    *  key: accessor token for parent nodes
    *  value: application specific data
    *  parent: a TreeNode which contains a pointer back to this object
    *  widget: The widget used to render the object
    """
    def __init__(self, value, parent=None, key=None, depth=None):
        self._key = key
        self._parent = parent
        self._value = value
        self._depth = depth
        self._widget = None

    def get_widget(self):
        """ Return the widget for this node."""
        if self._widget is not None:
            return self._widget

    def load_widget(self):
        return TreeWidget(self)
        
    def get_depth(self):
        if self._depth is None and self._parent is None:
            self._depth = 0
        elif self._depth is None:
            self._depth = self._parent.get_depth()
        else:
            return self._depth
            
    def get_index(self):
        if self.get_depth() == 0:
            return None
        else:
            key = self.get_key()
            parent = self.get_parent()
            return parent.get_child_index(key)

    def get_key(self):
        return self._key

    def get_parent(self):
        return self._parent

    def is_root():
        return self.get_depth() == 0
        
    def next_sibling():
        if depth > 0:
            return self.get_parent().next_child(self.get_key())
        else:
            return None

    def prev_sibling():
        if depth > 0:
            return self.get_parent().prev_child(self.get_key())
        else:
            return None


class ParentNode(TreeNode):
    """Maintain sort order for TreeNodes."""
    def __init__(self, value, parent=None, key=None, depth=None):
        TreeNode.__init__(self, value, parent, key)

        self._child_keys = None
        self._children = {}

    def load_widget(self):
        return ParentWidget(self)

    def get_child_keys(self):
        """Return a possibly ordered list of child keys"""
        if self._child_keys is None:
            self._child_keys = self.load_child_keys()
        return self._child_keys

    def load_child_keys(self):
        """Provide ParentNode with an ordered list of child keys (virtual
        function)"""
        raise TreeWidgetError("virtual function.  Implement in sub class")

    def get_child_widget(self, key):
        """Return the widget for a given key.  Create if necessary."""
        
        child = self.get_child_node(key)
        return child.get_widget()

    def get_child_node(self, key):
        """Return the child node for a given key.  Create if necessary."""
        if key in self._children:
            return self._children[key]
        else:
            return self.load_child_node(key)

    def load_child_node(self, key):
        """Load the child node for a given key (virtual function)"""
        raise TreeWidgetError("virtual function.  Implement in sub class")

    def get_child_index(self, key):
        try:
            return self._child_keys.index(key)
        except ValueError:
            errorstring = ("Can't find key %s in ParentNode %s\n" +
                           "ParentNode items: %s")
            raise TreeWidgetError(errorstring % (key, self.get_key(), 
                                  str(self.get_child_keys())))

    def next_child(self, key):
        """Return the next child node in index order from the given key."""

        index = self.get_child_index(key)
        index += 1
        
        child_keys = self.get_child_keys()
        if index < len(child_keys):
            # get the next item at same level
            return self.get_child_node(child_keys[index])
        else:
            return None

    def prev_child(self, key):
        """Return the previous child node in index order from the given key."""
        index = self.get_child_index(key)
        if index > 0:
            # get the previous item at same level
            return self.get_child_node(child_keys[index])
        else:
            return None

    def get_first_child(self):
        """Return the first TreeNode in the directory."""
        return self.get_child_node(self._child_keys[0])
    
    def get_last_child(self):
        """Return the last TreeNode in the directory."""
        return self.get_child_node(self._child_keys[-1])


class TreeWalker(urwid.ListWalker):
    """ListWalker-compatible class for browsing directories.
    
    positions are TreeNodes."""
    
    def __init__(self, start_from):
        """start_from: TreeNode with the initial focus."""
        self.focus = start_from

    def get_focus(self):
        widget = self.focus.get_widget()
        return widget, self.focus
        
    def set_focus(self, focus):
        self.focus = focus
        self._modified()

    def get_next(self, start_from):
        widget = start_from.get_widget(key)
        target = widget.next_inorder()
        if target is None:
            return None, None
        else:
            return target, target.get_node()

    def get_prev(self, start_from):
        widget = start_from.get_widget(key)
        target = widget.prev_inorder()
        if target is None:
            return None, None
        else:
            return target, target.get_node()


