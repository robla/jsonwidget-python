from jsonwidget.jsonnode import JsonNode, JsonNodeError
from jsonwidget.schema import SchemaNode

class TestJsonNodeArray:
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
        indata = ["thing1", "thing2", "thing3"]
        schemanode = SchemaNode(string=self.schemastring)
        jsonnode = JsonNode(data=indata, schemanode=schemanode)
        jsonnode.insert_child(1)
        outdata = jsonnode.get_data()
        assert outdata[1] == ''
        assert outdata[2] == 'thing2'
        assert len(outdata) == 4

