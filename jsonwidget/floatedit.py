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
        '''
        Simulate what would happen should the given character be inserted
        '''

        # if there's highlighted text, it'll get replaced by this character
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
    
    # this should probably just be "valid_char()", but was renamed for reasons
    # stated below.
    def valid_charkey(self, ch): 
        """
        Return true for valid float characters, regardless of position
        """
        allowed = "0123456789.-+eE"
        if self.allow_nan:
            # allow "NaN", "nan", "Infinity", and "infinity"
            allowed +="NnaIifty"
        return len(ch)==1 and ch in allowed

    # note, this should probably be renamed "valid_result()", and the base
    # class should be modified to call it by its new name.  That would make
    # it so that "valid_charkey()" could be named "valid_char()".  This
    # function is currently named the way it is so that this class will run 
    # on an unmodified release of urwid.
    def valid_char(self, ch):
        """
        Return true if the result would be a valid string representing a float,
        or at least a partial representation of a float
        """
        
        future_result=self.test_result(ch)

        if not self.valid_charkey(ch):
            return False

        # if the result is a fully valid float, return true:
        if re.match(r'[\+\-]?(0|[1-9]\d*)(\.\d+)?([eE][\+\-]?\d+)?$', future_result):
            return True

        if self.allow_nan:
            # allow partial versions of "NaN"/"nan" and "[Ii]nfinity"
            if re.match(r'[\+\-]?[Ii](n(f(i(n(i(t(y)?)?)?)?)?)?)?$', future_result):
                return True
            if re.match(r'[Nn](a([Nn])?)?$', future_result):
                return True

        # if the result would be mostly valid, still return true so that the 
        # user can finish typing:

        # Partial exponent
        if re.match(r'-?(0|[1-9]\d*)(\.\d+)?([eE][\+\-]?)?$', future_result):
            return True

        # Partial decimal
        if re.match(r'-?(0|[1-9]\d*)(\.)?([eE])?$', future_result):
            return True

        # Prohibit leading zero in front of any digit at the beginning of the 
        # input
        if re.match(r'-?0\d+', future_result):
            return False
        
        # Partial whole number
        if re.match(r'-?(\d*)(\.\d+)?([eE])?$', future_result):
            return True

        return False
    
    def __init__(self,caption="",default=None, allow_nan=True):
        """
        caption -- caption markup
        default -- default edit value

        >>> FloatEdit("", 42)
        <FloatEdit selectable flow widget '42' edit_pos=2>
        """
        if default is not None: val = str(default)
        else: val = ""
        self.has_focus=False
        self.allow_nan=allow_nan
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
        """
        if self.edit_text:
            return float(self.edit_text)
        else:
            return 0

    def on_blur(self):
        """
        Called when the widget loses focus
        """
        newtext=self.edit_text

        # This function relies on valid_char() to do the heavy lifting.  The
        # code below performs cleanup on partial entries.

        # Nuke partial exponent
        newtext=re.sub(r'[eE][\+\-]?$', '', newtext)

        # If the 'e' is missing, put it back
        newtext=re.sub(r'(\d+)([\+\-])', r'\1e\2', newtext)

        # assume n* is "nan"
        newtext=re.sub(r'^[Nn].*$', 'nan', newtext)
        # assume i* is "inf"
        newtext=re.sub(r'^([\+\-]?)[Ii].*$', r'\1inf', newtext)
        # nuke "finity" or "an"
        newtext=re.sub(r'^[afty].*', '', newtext)

        if newtext=="":
            newtext="0"
        
        # inlining function snarfed from http://bugs.python.org/msg75745
        def isNaN(x):
            return (x is x) and (x != x)

        if not self.allow_nan and (isNaN(float(newtext)) or
                                   float(newtext)==float('-inf') or
                                   float(newtext)==float('inf')):
            newtext="0"

        newtext=str(float(newtext))
        newtext=re.sub(r'\.0$', '', newtext)
 
        self.set_edit_text(newtext)

    # This retrofits an on_blur() method into the class, and isn't specific
    # to FloatEdit
    def render(self,(maxcol,), focus=False):
        if self.has_focus and not focus:
            self.has_focus=False
            self.on_blur()
        self.has_focus=focus

        return self.__super.render((maxcol,), focus=focus)


def run_test():
    text_header = ("FloatEdit test harness")
    text_edit_cap1 = ('editcp',"Float 1: ")
    text_edit_cap2 = ('editcp',"Float 2: ")
    text_edit_cap3 = ('editcp',"Float 3: ")
    text_edit_cap4 = ('editcp',"Float 4: ")
    text_edit_cap5 = ('editcp',"Float 5: ")
    text_edit_cap6 = ('editcp',"Float 6 (disallow NaN): ")

    listbox_content = [
        AttrWrap(FloatEdit(text_edit_cap1, 1.23),
            'editbx', 'editfc' ),
        AttrWrap(FloatEdit(text_edit_cap2, 0.001),
            'editbx', 'editfc' ),
        AttrWrap(FloatEdit(text_edit_cap3, 0.1e-20),
            'editbx', 'editfc' ),
        AttrWrap(FloatEdit(text_edit_cap4, float('inf')),
            'editbx', 'editfc' ),
        AttrWrap(FloatEdit(text_edit_cap5, float('nan')),
            'editbx', 'editfc' ),
        AttrWrap(FloatEdit(text_edit_cap6, float('nan'), allow_nan=False),
            'editbx', 'editfc' )
    ]
    header = AttrWrap(Text(text_header), 'header')
    listbox = ListBox(SimpleListWalker(listbox_content))
    frame = Frame(AttrWrap(listbox, 'body'), header=header)
    
    palette = [
        ('body','black','light gray', 'standout'),
        ('reverse','light gray','black'),
        ('header','white','dark red', 'bold'),
        ('important','dark blue','light gray',('standout','underline')),
        ('editfc','white', 'dark blue', 'bold'),
        ('editbx','light gray', 'dark blue'),
        ('editcp','black','light gray', 'standout'),
        ('bright','dark gray','light gray', ('bold','standout')),
        ('buttn','black','dark cyan'),
        ('buttnf','white','dark blue','bold'),
        ]

    def unhandled(key):
        if key == 'f8':
            raise ExitMainLoop()

    MainLoop(frame, palette, None, unhandled_input=unhandled).run()
        
    main()
    
if '__main__'==__name__:
    run_test()

