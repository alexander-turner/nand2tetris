from absl import flags
from typing import Dict
import enum
import sys


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
        assert source.endswith(".vm"), "Invalid file type"
        assert (
            source[0].capitalize() == source[0]
        ), f"First letter of {source} must be capitalized."

        self.source = source
        with open(self.source, "r") as f:
            self.lines = f.readlines()
        self.current_idx = 0

    @property
    def current_line(self) -> str:
        return self.lines[self.current_idx].strip()

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
        elif any(
            x in self.current_line
            for x in ["eq", "gt", "lt", "and", "or", "not"]
        ):
            return CommandType.C_ARITHMETIC
        elif "goto" in self.current_line:
            return CommandType.C_GOTO
        elif any(x in self.current_line for x in ["add", "sub", "neg"]):
            return CommandType.C_ARITHMETIC
        elif "return" in self.current_line:
            return CommandType.C_RETURN
        elif "call" in self.current_line:
            return CommandType.C_CALL
        else:  # TODO implement function
            raise ValueError("Invalid command type")

    def arg1(self) -> str:
        """Returns the first argument of the current command."""
        command = self.command_type()
        assert command != CommandType.C_RETURN
        if command == CommandType.C_ARITHMETIC:
            return self.current_line.split()[0]
        else:  # Get the second word
            return self.current_line.split()[1]

    def arg2(self) -> int:
        """Return the second argument of the current command."""
        command = self.command_type()
        assert command in (
            CommandType.C_PUSH,
            CommandType.C_POP,
            CommandType.C_FUNCTION,
            CommandType.C_CALL,
        )
        return int(self.current_line.split()[2])


_SEGMENTS: Dict[str, str] = {
    "local": "LCL",
    "argument": "ARG",
    "temp": "TEMP",
    "this": "THIS",
    "that": "THAT",
}


class CodeWriter:
    """Translates VM commands into Hack assembly code."""

    def __init__(self, output_file: str) -> None:
        self.filename = output_file
        # Delete file if it exists
        with open(self.filename, "w") as f:
            f.write("")  # Clear the file

        self.arithmetic_counter = 0

    def _write_to_file(self, content: str) -> None:
        """Writes the given content to the output file."""
        with open(self.filename, "a") as f:
            f.write(content)

    @staticmethod
    def _compute_target_address(segment: str, index: int) -> str:
        """Returns the assembly code that computes the target address
        in the segment given by segment and index. Sets it as the
        current address."""
        assert segment in _SEGMENTS.keys(), f"{segment} not valid"
        # Compute target address to move value to
        output = f"@{index}\nD=A\n"
        if segment == "temp":
            output += "@5\n"  # Starts at address 5
            output += "A=A+D\n"
        else:  # We're jumping to the address stored in the segment
            # Add to base address
            output += f"@{_SEGMENTS[segment]}\n"
            output += "A=M+D\n"
        return output

    def writePushPop(
        self, command: CommandType, segment: str, index: int
    ) -> None:
        """Writes to the output file the assembly code that implements
        the given push/pop command."""
        assert command in (CommandType.C_POP, CommandType.C_PUSH)
        if command == CommandType.C_POP:
            if segment == "constant":
                return  # Ignore pop constant
            # For pop, decrement SP, read the value, and store in
            # segment-index
            output = self._compute_target_address(segment, index)
            output += (
                "D=A\n"
                # Store target address in register 13
                "@R13\n"
                "M=D\n"
                # Decrement SP
                "@SP\n"
                "M=M-1\n"
                "A=M\n"  # Get RAM[SP]
                "D=M\n"
                # Retrieve target address
                "@R13\n"
                "A=M\n"
                # Store value
                "M=D\n"
            )
        else:
            """For push, read the value from segment-index and store in
            RAM[SP], then increment SP."""
            if segment == "constant":
                output = (
                    f"@{index}\n"
                    "D=A\n"  # Set to constant value
                )
            else:
                output = (
                    self._compute_target_address(segment, index) + "D=M\n"
                )  # Read the value from segment-index
            output += (
                "@SP\n"  # Get RAM[SP]
                "M=M+1\n"
                "A=M-1\n"  # Get RAM[SP-1]
                "M=D\n"  # Store value
            )
        self._write_to_file(output)

    def writeArithmetic(self, command: str) -> None:
        """Writes to the output file the assembly code that implements
        the given arithmetic-logical command."""
        if command not in ("not", "neg"):  # Single arg, doesn't decrement SP
            output = "@SP\nM=M-1\n"  # Decrement SP
            output += "A=M\nD=M\n"  # Get RAM[SP] and store in D

        if command in ("add", "sub"):
            output += "A=A-1\n"  # Get RAM[SP-1]
            output += (
                "M=M+D\n" if command == "add" else "M=M-D\n"
            )  # RAM[SP-1] - RAM[SP]
        elif command == "neg":
            output = (
                "@SP\n"
                "A=M-1\n"  # Get RAM[SP-1]
                "D=M\n"
                # Do the negation
                "@0\n"
                "D=A-D\n"
                # Store in RAM[SP]
                "@SP\n"
                "A=M-1\n"
                "M=D\n"  # Write to RAM[SP-1]
            )
        elif command in ("eq", "lt", "gt"):
            output += (
                "A=A-1\n"  # Get SP-1 (y addr)
                "D=D-M\n"  # Get difference RAM[SP] (y) - RAM[SP-1] (x)
                f"@TRUE{self.arithmetic_counter}\n"
            )
            if command == "eq":
                output += "D;JEQ\n"  # jump to TRUE if D==0
            elif command == "lt":  # x < y so we check if y-x = D > 0
                output += "D;JGT\n"
            else:
                output += "D;JLT\n"
            output += (
                "@SP\n"  # If we jumped, the conditional is false
                "A=M-1\n"  # Overwrite RAM[SP-1]
                "M=0\n"
                f"@END{self.arithmetic_counter}\n"  # Jump past the TRUE clause
                "0;JMP\n"
                f"(TRUE{self.arithmetic_counter})\n"
                "@SP\n"
                "A=M-1\n"  # Overwrite RAM[SP-1]
                "M=-1\n"
            )
        elif command == "and":
            output += (
                "A=A-1\n"  # Get RAM[SP-1]
                "M=M&D\n"  # RAM[SP-1] & RAM[SP]
            )
        elif command == "or":
            output += (
                "A=A-1\n"  # Get RAM[SP-1]
                "M=M|D\n"  # RAM[SP-1] | RAM[SP]
            )
        elif command == "not":  # command is bitwise-not
            output = (
                "@SP\n"
                "A=M-1\n"  # Get RAM[SP-1]
                "D=M\n"  # Store bitwise-not in RAM[SP-1]
                "@0\n"
                "D=A-D\n"
                "D=D-1\n"
                "@SP\n"
                "A=M-1\n"
                "M=D\n"
            )
        else:
            raise ValueError("Invalid command type")

        if command not in ("add", "sub", "neg"):
            output += f"(END{self.arithmetic_counter})\n"
        self.arithmetic_counter += 1
        self._write_to_file(output)


_SOURCE = flags.DEFINE_string(
    "source",
    "",
    "File name to translate",
    short_name="s",
)


def __main__(args) -> None:
    # Parse the flags
    flags.FLAGS(args)

    parser = Parser(source=_SOURCE.value)

    if not parser.has_more_lines():
        print("Loaded an empty file.")
        return None  # Empty file

    if parser.skip_line(parser.current_line):
        parser.advance()  # Skip the first line if it's a comment
    basename: str = _SOURCE.value.partition(".")[0]
    writer = CodeWriter(basename + ".asm")
    while parser.has_more_lines():
        command: CommandType = parser.command_type()
        arg1 = parser.arg1()  # NOTE not handling return command type
        if command in (CommandType.C_POP, CommandType.C_PUSH):
            arg2 = parser.arg2()
            writer.writePushPop(command=command, segment=arg1, index=arg2)
        else:
            writer.writeArithmetic(command=arg1)

        parser.advance()  # Skip whitespace
    writer._write_to_file(f"(END)\n@END\n0;JMP\n")  # Endless loop


if __name__ == "__main__":
    __main__(sys.argv)
