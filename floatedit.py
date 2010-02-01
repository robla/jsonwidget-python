#!/usr/bin/python
# FloatEdit widget for urwid
#    Copyright (c) 2010  Rob Lanphier
# Derived from IntEdit in the urwid basic widget classes
#    Copyright (C) 2004-2007  Ian Ward
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

from urwid import *
import re

class FloatEdit(Edit):
    """Edit widget for float values"""

    def test_result(self, ch):
        # simulate what would have happened had this character been inserted

        # delete highlighted
        if self.highlight:
            start, stop = self.highlight
            btext, etext = self.edit_text[:start], self.edit_text[stop:]
            test_text =  btext + etext
            test_pos = start
        else:
            test_text = self.edit_text
            test_pos = self.edit_pos

        if type(ch) == type(u""):
            ch = ch.encode("utf-8")

        test_text = test_text[:test_pos] + ch + test_text[test_pos:]
        return test_text
    
    def valid_charkey(self, ch): 
        return len(ch)==1 and ch in "0123456789.-+eE"

    def valid_char(self, ch):
        """
        Return true for decimal digits, decimal point, exponent, and +/-
        """
        
        future_result=self.test_result(ch)

        if not self.valid_charkey(ch):
            return False

        # if the result is a fully valid float, return true:
        if re.match(r'[\+\-]?(0|[1-9]\d*)(\.\d+)?([eE][\+\-]?\d+)?$', future_result):
            return True

        # if the result would be a partial float, still return true so that 
        # they can finish
        
        # Partial exponent
        if re.match(r'-?(0|[1-9]\d*)(\.\d+)?([eE][\+\-]?)?$', future_result):
            return True
            
        # Partial decimal
        if re.match(r'-?(0|[1-9]\d*)(\.)?([eE])?$', future_result):
            return True

        # Prohibit leading zero in front of any digit
        if re.match(r'-?0\d+', future_result):
            return False
        
        # Partial whole number
        if re.match(r'-?(\d*)(\.\d+)?([eE])?$', future_result):
            return True

        return False
    
    def __init__(self,caption="",default=None):
        """
        caption -- caption markup
        default -- default edit value

        >>> FloatEdit("", 42)
        <FloatEdit selectable flow widget '42' edit_pos=2>
        """
        if default is not None: val = str(default)
        else: val = ""
        self.has_focus=False
        self.__super.__init__(caption,val)

    def keypress(self, size, key):
        """
        Handle editing keystrokes.  Remove leading zeros.
        
        >>> e, size = IntEdit("", 5002), (10,)
        >>> e.keypress(size, 'home')
        >>> e.keypress(size, 'delete')
        >>> e.edit_text
        '002'
        >>> e.keypress(size, 'end')
        >>> e.edit_text
        '2'
        """
        (maxcol,) = size
        unhandled = Edit.keypress(self,(maxcol,),key)

        return unhandled

    def value(self):
        """
        Return the numeric value of self.edit_text.
        
        >>> e, size = FloatEdit(), (10,)
        >>> e.keypress(size, '5')
        >>> e.keypress(size, '1')
        >>> e.value() == 51
        True
        """
        if self.edit_text:
            return float(self.edit_text)
        else:
            return 0

    def on_blur(self):
        newtext=self.edit_text
        
        # if the result is a fully valid float, don't munge
        #if re.match(r'-?(0|[1-9]\d*)(\.\d+)?([eE][+-]?\d+)?$', newtext):
        #    return

        # Nuke partial exponent
        newtext=re.sub(r'[eE][\+\-]?$', '', newtext)
        if newtext=="":
            newtext="0"

        newtext=str(float(newtext))
        newtext=re.sub(r'\.0$', '', newtext)
        
        self.set_edit_text(newtext)

    def render(self,(maxcol,), focus=False):
        if self.has_focus and not focus:
            self.has_focus=False
            self.on_blur()
        self.has_focus=focus

        return self.__super.render((maxcol,), focus=focus)

