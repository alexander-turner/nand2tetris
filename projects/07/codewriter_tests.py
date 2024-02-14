import unittest
from VMTranslator import CodeWriter

class CodeWriterLabelGotoTest(unittest.TestCase):
    def setUp(self):
        self.output_filename = "TempTest.asm"
        self.writer = CodeWriter(self.output_filename)

    def tearDown(self):
        # Clean up by removing the temporary file
        import os
        os.remove(self.output_filename)

    def test_write_label(self):
        self.writer.write_label("LOOP_START")
        with open(self.output_filename, "r") as f:
            content = f.read()
        self.assertEqual(content, "(LOOP_START)\n")

    def test_write_goto(self):
        self.writer.write_goto("LOOP_START")
        with open(self.output_filename, "r") as f:
            content = f.read()
        self.assertEqual(content, "@LOOP_START\n0;JMP\n", f"The generated assembly code for goto does not match the expected output. Got: {content}")

    def test_write_if_goto(self):
        # Use the updated public interface for the if-goto command
        self.writer.write_if_goto("LOOP_END")
        
        # Now, read the file and check if the assembly code matches the expectation
        with open(self.output_filename, "r") as f:
            content = f.read()        
        # The expected assembly code for if-goto LOOP_END, including stack manipulation
        expected_content = (
            "@SP\n"         # Access SP
            "M=M-1\n"      # Decrement SP and address top of stack
            "A=M\n"         # Change address to old top of stack
            "D=M\n"         # Pop old top value into D
            f"@LOOP_END\n"   # Load the label address
            "D;JNE\n"       # Jump if D is not zero (conditional jump)
        )
        self.assertEqual(content, expected_content, "The generated assembly code for if-goto does not match the expected output.")

if __name__ == "__main__":
    unittest.main()

