from dingus import Dingus, returner

from jsonwidget.jsonnode import JsonNode, JsonNodeError
from jsonwidget.schema import SchemaNode
from jsonwidget.termwidgets import JsonWidgetParent

class TestJsonWidgetParent:
    def setup(self):
        self.schemastring = """
            {
                "type": "seq", 
                "sequence": [
                    {
                        "type": "str"
                    }
                ]
            }
            """

    def test_insert(self):
        def get_val_text(obj, i):
            return obj.get_child_node(i).get_widget().get_value_text()
        indata = ["thing1", "thing2", "thing3"]
        schemanode = SchemaNode(string=self.schemastring)
        jsonnode = JsonNode(data=indata, schemanode=schemanode)
        termparent = JsonWidgetParent(jsonnode)
        termparent._listbox = Dingus(get_focus_offset_inset=returner((0,0)))
        termparent.insert_child_node(1)
        outdata = termparent.get_value().get_data()
        outkeys = termparent.get_child_keys()
        assert get_val_text(termparent, 0) == 'thing1'
        assert get_val_text(termparent, 1) == ''
        assert get_val_text(termparent, 2) == 'thing2'
        assert get_val_text(termparent, 3) == 'thing3'
        for i, v in enumerate(outdata):
            wval = termparent.get_child_node(i).get_widget().get_value_text()
            assert v == wval

