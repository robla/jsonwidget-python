from jsonwidget.schema import SchemaNode

class TestSchemaArray:
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

    def test_create(self):
        schemanode = SchemaNode(string=self.schemastring)
        assert schemanode.is_type('array')

