import unittest
from VMTranslator import Parser, CommandType

class ParserLabelGotoTest(unittest.TestCase):
    def setUp(self):
        # Setup a temporary .vm file with label and goto commands
        self.source_content = """
// Simple label and goto example
label LOOP_START
goto LOOP_START
if-goto LOOP_END
"""
        self.filename = "TempTest.vm"
        with open(self.filename, "w") as f:
            f.write(self.source_content.strip())

    def tearDown(self):
        # Clean up by removing the temporary file
        import os
        os.remove(self.filename)

    def test_label_command_recognition(self):
        parser = Parser(self.filename)
        parser.advance()  # Move to the label command
        self.assertEqual(parser.command_type(), CommandType.C_LABEL)

    def test_goto_command_recognition(self):
        parser = Parser(self.filename)
        parser.advance()  # Skip to the label command
        parser.advance()  # Move to the goto command
        self.assertEqual(parser.command_type(), CommandType.C_GOTO)

    def test_label_name_extraction(self):
        parser = Parser(self.filename)
        parser.advance()  # Move to the label command
        self.assertEqual(parser.arg1(), "LOOP_START")

    def test_if_goto_command_recognition_and_label_extraction(self):
        parser = Parser(self.filename)
        parser.reset()  # Resets the parser to the beginning of the file
        while parser.has_more_lines():
            parser.advance()
            if "if-goto" in parser.current_line:
                self.assertEqual(parser.command_type(), CommandType.C_IF)
                self.assertEqual(parser.arg1(), "LOOP_END")
                break
        else:
            self.fail("if-goto command not found in the test file.")

if __name__ == "__main__":
    unittest.main()
