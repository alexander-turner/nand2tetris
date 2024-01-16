from absl import flags 
from typing import Dict 
import enum 

@enum.unique
class CommandType(enum.Enum): 
    C_ARITHMETIC = enum.auto()
    C_PUSH = enum.auto()
    C_POP = enum.auto()
    C_LABEL = enum.auto()
    C_GOTO = enum.auto()
    C_IF = enum.auto()
    C_FUNCTION = enum.auto()
    C_RETURN = enum.auto()
    C_CALL = enum.auto()

class Parser: 
    def __init__(self, source: str) -> None: 
        self.source = source 
        self.file = open(source, 'r')
        self.lines = self.file.readlines()
        self.current_idx = 0
        
    @property 
    def current_line(self) -> str:
        return self.lines[self.current_idx]

    def has_more_lines(self) -> bool:
        return 0 <= self.current_idx < len(self.lines)

    @staticmethod
    def skip_line(line: str) -> bool:
        return line.startswith("//") or line.isspace() or line == ""

    def advance(self) -> None:
        # Skips over whitespaces and comments
        self.current_idx += 1

        while self.has_more_lines() and self.skip_line(self.current_line):
            self.current_idx += 1

    def command_type(self) -> CommandType:
        """Returns a constant representing the type of the current command.
If the current command is an arithmetic-logical command, returns
C_ARITHMETIC.""" 
        if "push" in self.current_line: 
            return CommandType.C_PUSH
        elif "pop" in self.current_line:
            return CommandType.C_POP
        elif "label" in self.current_line:
            return CommandType.C_LABEL
        elif any(x in self.current_line for x in ["eq", "gt", "lt", "and", "or", "not"]):
            return CommandType.C_IF
        elif "goto" in self.current_line:
            return CommandType.C_GOTO
        elif any(x in self.current_line for x in ["add", "sub", "neg"]):
            return CommandType.C_FUNCTION
        elif "return" in self.current_line:
            return CommandType.C_RETURN
        elif "call" in self.current_line:
            return CommandType.C_CALL
        else: 
            raise ValueError("Invalid command type")

    def arg1(self) -> str:
        # Return the first argument of the current command.
        command = self.command_type()
        assert command != CommandType.C_RETURN 
        if command == CommandType.C_ARITHMETIC:
            return self.current_line.split()[0]
        else: # Get the second word
            return self.current_line.split()[1]

    def arg2(self) -> int:
        """Return the second argument of the current command."""
        command = self.command_type()
        assert command in (CommandType.C_PUSH, CommandType.C_POP, CommandType.C_RETURN)
        return int(self.current_line.split()[2])

_SEGMENTS: Dict[str, str] = {
    'local': 'LCL',
    'argument': 'ARG', 
    'temp': 'TEMP',
    'this': 'THIS',
    'that': 'THAT'
}
class CodeWriter: 
    """ Translates VM commands into Hack assembly code. """

    def __init__(self, output: str) -> None: 
        self.output = output 
        self.file = open(output, 'w')


    def writePushPop(self, command: CommandType, segment: str, index: int) -> None: 
        """ Writes to the output file the assembly code that implements
        the given push/pop command."""
        assert command in (CommandType.C_POP, CommandType.C_PUSH)
        # For pop, decrement SP, read the value, and store in segment-index
        output: str = ""
        if command == CommandType.C_POP: 
            output = (
                # Decrement SP
                "@SP\n"
                "M=M-1\n"
                "D=M\n"
                # Store RAM[SP] in temporary register 13 
                "@R13\n" 
                "M=D\n"
                # Compute target address to move value to
                f"@{index}\n" 
                "D=A\n"
                # Add to base address
                f"@{_SEGMENTS[segment]}\n"
                "A=M+D\n"
                "D=A\n"
                "@R14\n"
                "M=D\n"
                # Retrieve value from RAM[SP] 
                "@R13\n"
                "D=M\n"
                "@R14\n"
                "A=M\n"
                # Store the value
                "M=D\n" 
            )
        else: 
            pass 
        return output 
        
    def writeArithmetic(self, command: str) -> None: 
        raise NotImplementedError

    def close(self) -> None: 
        self.file.close()

_SOURCE = flags.DEFINE_string('source', '', 'File name to translate', short_name='s', )

def __main__(args) -> None: 

