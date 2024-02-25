from absl import flags
from typing import Dict, Literal
import enum
import re
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
            x in self.current_line for x in ["eq", "gt", "lt", "and", "or", "not"]
        ):
            return CommandType.C_ARITHMETIC
        elif "if-goto" in self.current_line:
            return CommandType.C_IF
        elif "goto" in self.current_line:
            return CommandType.C_GOTO
        elif any(x in self.current_line for x in ["add", "sub", "neg"]):
            return CommandType.C_ARITHMETIC
        elif "return" in self.current_line:
            return CommandType.C_RETURN
        elif "call" in self.current_line:
            return CommandType.C_CALL
        elif "function" in self.current_line:
            return CommandType.C_FUNCTION
        elif "return" in self.current_line:
            return CommandType.C_RETURN
        else:
            raise ValueError("Invalid command type")

    @staticmethod
    def is_valid_label_name(label: str) -> bool:
        """The label is a string composed of any sequence of letters, digits, underscore (_), dot (.), and colon (:) that does not begin with a digit."""
        pattern = "^[a-zA-Z_.$:][a-zA-Z_.$:0-9]*$"
        return bool(re.match(pattern, label)) and not label == "END"

    @staticmethod
    def _basename(filename: str) -> str:
        """Returns the basename."""
        assert filename.count(".") >= 1
        return filename.partition(".")[0]

    @staticmethod
    def scoped_label(filename: str, label: str) -> str:
        return f"{Parser._basename(filename)}.{label}"

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

    def reset(self) -> None:
        self.current_idx = 0


_SEGMENTS: Dict[str, str] = {
    "local": "LCL",
    "argument": "ARG",
    "temp": "TEMP",
    "this": "THIS",
    "that": "THAT",
}


class CodeWriter:
    """Translates VM commands into Hack assembly code."""

    def __init__(self, output_filename: str) -> None:
        self.filename = output_filename
        self.reset()

    def reset(self) -> None:
        # Delete file if it exists
        with open(self.filename, "w") as f:
            f.write("")  # Clear the file
        self.arithmetic_counter = 0

    def _write_to_file(self, content: str) -> None:
        """Writes the given content to the output file."""
        with open(self.filename, "a") as f:
            f.write(content)

    def _compute_target_address(
        self, segment: str, index: int, register: Literal["D", "A", "M"] = "A"
    ) -> str:
        """Returns the assembly code that computes the target address
        in the segment given by segment and index. Stores it in `register`."""
        assert (
            segment in _SEGMENTS.keys() or segment == "pointer" or segment == "static"
        ), f"{segment} not valid"

        if segment == "pointer":
            if index == 0:
                return "@THIS\n"
            elif index == 1:
                return "@THAT\n"
            else:
                raise ValueError("Invalid pointer index")

        # Address a scoped label which we make for the static segment
        if segment == "static":
            return scoped_label(self.filename, label=str(index))

        # Compute target address to move value to
        output = f"@{index}\nD=A\n"
        if segment == "temp":
            output += "@5\n"  # Starts at address 5
            output += f"{register}=A+D\n"
        else:  # We're jumping to the address stored in the segment
            # Add to base address
            output += f"@{_SEGMENTS[segment]}\n"
            output += f"{register}=M+D\n"
        return output

    def _pop_cmds(self) -> str:
        """Pops the top value off the stack and stores it in D. Decrements SP."""
        return (
            "@SP\n"  # Access SP
            "M=M-1\n"  # Decrement SP
            "A=M\n"  # Change address to old top of stack
            "D=M\n"  # Pop old top value into D
        )

    def _push_cmds(self) -> str:
        """Pushes the current contents of D onto the stack."""
        return (
            "@SP\n"  # Get RAM[SP]
            "M=M+1\n"
            "A=M-1\n"  # Get RAM[SP-1]
            "M=D\n"  # Write to old top of stack
        )

    def write_push_pop(
        self,
        command: Literal[CommandType.C_POP, CommandType.C_PUSH],
        segment: str,
        index: int,
    ) -> None:
        """Writes to the output file the assembly code that implements
        the given push/pop command."""
        if command == CommandType.C_POP:
            if segment == "constant":
                return  # Ignore pop constant
            # Store target address in R13
            output = self._compute_target_address(segment, index, register="D")
            output += (
                # Store target address in register 13
                "@R13\n"
                "M=D\n"
            )
            output += self._pop_cmds()
            output += (
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
                    self._compute_target_address(segment, index, register="A") + "D=M\n"
                )  # Read the value from segment-index
            output += self._push_cmds()
        self._write_to_file(output)

    def write_arithmetic(self, command: str) -> None:
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

    def write_label(self, location_name: str) -> None:
        """Writes the assembly code that effects the label command."""
        self._write_to_file(f"({location_name})\n")

    def write_goto(self, location_name: str) -> None:
        """Writes the assembly code that effects the goto command."""
        self._write_to_file(f"@{location_name}\n0;JMP\n")

    def write_if_goto(self, location_name: str) -> None:
        """Writes the assembly code for an if-goto command that pops the top
        value off the stack and conditionally jumps to the specified label if
        the value is not zero."""
        output = self._pop_cmds()
        output += (
            f"@{location_name}\n"  # Load the label address
            "D;JNE\n"  # Jump if D is not zero (conditional jump)
        )
        self._write_to_file(output)

    def write_function(self, function_name: str, num_vars: int) -> None:
        raise NotImplementedError

    def write_call(self, function_name: str, num_args: int) -> None:
        """Call the given function, informing it that num_args were pushed to stack before the call."""
        # First generate a label and write to asm
        scoped_function_name: str = Parser.scoped_label(
            filename=self.filename, label=function_name
        )
        self.write_label(scoped_function_name)

        # Push LCL
        self._get_segment_address(segment="LCL", index=0, register="D")

        raise NotImplementedError

    def write_return(self) -> None:
        raise NotImplementedError

    def write_end_loop(self) -> None:
        self._write_to_file(f"(END)\n@END\n0;JMP\n")


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

    vm_filename = _SOURCE.value
    asm_filename = vm_filename.replace(".vm", ".asm")
    writer = CodeWriter(asm_filename)

    if parser.skip_line(parser.current_line):
        parser.advance()  # Skip the first line if it's a comment
    while parser.has_more_lines():
        command: CommandType = parser.command_type()

        arg1 = parser.arg1()
        arg2 = parser.arg2()
        if command in (CommandType.C_POP, CommandType.C_PUSH):
            writer.write_push_pop(command=command, segment=arg1, index=arg2)
        elif command in (CommandType.C_LABEL, Commandtype.C_GOTO, CommandType.C_IF):
            label = parser.arg1()
            scoped_label: str = parser.scoped_label(
                filename=writer.filename, label=label
            )
            if not parser.is_valid_label_name(scoped_label):
                raise ValueError(f"Invalid label name: {scoped_label}")
            if command == CommandType.C_LABEL:
                writer.write_label(scoped_label)
            elif command == CommandType.C_GOTO:
                writer.write_goto(scoped_label)
            elif command == CommandType.C_IF:
                writer.write_if_goto(scoped_label)
        elif command == CommandType.C_ARITHMETIC:
            writer.write_arithmetic(command=arg1)
        elif command == CommandType.C_FUNCTION:
            writer.write_function(function_name=arg1, num_vars=arg2)
        elif command == CommandType.C_CALL:
            writer.write_call(function_name=arg1, num_args=arg2)
        elif command == CommandType.C_RETURN:
            writer.write_return()
        else:
            raise ValueError("Invalid command type")

        parser.advance()  # Skip whitespace

    writer.write_end_loop()


if __name__ == "__main__":
    __main__(sys.argv)
