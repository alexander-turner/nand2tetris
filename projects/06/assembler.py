import os
import sys
from typing import Optional, Dict


class Parser:
    def __init__(self, filepath: str):
        assert os.path.exists(filepath), "File does not exist"

        self.filepath: str = filepath
        self.file = open(filepath, "r")
        self.lines: list[str] = self.file.readlines()
        self.current_idx: int = 0

    @property
    def current_line(self) -> str:
        if self.current_idx is None:
            return ""

        line: str = self.lines[self.current_idx]
        return line.strip()

    def has_more_lines(self) -> bool:
        return 0 <= self.current_idx < len(self.lines)

    def advance(self) -> None:
        # Skips over whitespaces and comments
        self.current_idx += 1

        def skip_line(line: str) -> bool:
            return line.startswith("//") or line.isspace()

        while self.has_more_lines() and skip_line(self.current_line):
            self.current_idx += 1

    def instruction_type(self) -> str:
        if self.current_line.startswith("@"):
            return "A"
        elif self.current_line.startswith("("):
            return "L"
        else:
            return "C"

    def symbol(self) -> str:
        if self.instruction_type() == "L":
            return self.current_line[1:-1]  # Leave out the parens
        elif self.current_line.startswith("@"):
            return self.current_line[1:]
        else:
            raise Exception

    def dest(self) -> str:
        assert self.instruction_type() == "C"
        first_part: str = self.current_line.partition("=")[0]
        return first_part if first_part != str else ""

    def comp(self) -> str:
        assert self.instruction_type() == "C"
        second_part = self.current_line.partition("=")[
            2
        ]  # 0 is before, 1 is sep, 2 is after
        # If there is no ;, then will return second_part, which is ok
        return second_part.partition(";")[0]

    def jump(self) -> str:
        assert self.instruction_type() == "C"
        return self.current_line.partition(";")[2]

    def finish(self) -> None:
        self.file.close()


_COMP_CODES: Dict[str, str] = {
    "": "",
    "0": "101010",
    "1": "111111",
    "-1": "111010",
    "D": "001100",
    "A": "110000",
    "M": "110000",
    "!D": "001101",
    "!A": "110001",
    "!M": "110001",
    "-D": "001111",
    "-A": "110011",
    "-M": "110011",
    "D+1": "011111",
    "A+1": "110111",
    "M+1": "110111",
    "D-1": "001110",
    "A-1": "110010",
    "M-1": "110010",
    "D+A": "000010",
    "D+M": "000010",
    "D-A": "010011",
    "D-M": "010011",
    "A-D": "000111",
    "M-D": "000111",
    "D&A": "000000",
    "D&M": "000000",
    "D|A": "010101",
    "D|M": "010101",
}

_JUMP_CODES: Dict[str, str] = {
    "": "000",
    "JGT": "001",
    "JEQ": "010",
    "JGE": "011",
    "JLT": "100",
    "JNE": "101",
    "JLE": "110",
    "JMP": "111",
}


class Code:
    def dest(self, dest_str: str) -> str:
        """Return the 3-bit destination code. Specifies where to store comp."""
        flags = [0, 0, 0]
        if "A" in dest_str:
            flags[2] = 1
        if "D" in dest_str:
            flags[1] = 1
        if "M" in dest_str:
            flags[0] = 1

        return str(flags[2]) + str(flags[1]) + str(flags[0])

    def comp(self, comp_str: str) -> str:
        a_bit: int = 1 if "M" in comp_str else 0
        return str(a_bit) + _COMP_CODES[comp_str]

    def jump(self, jump_str: str) -> str:
        return _JUMP_CODES[jump_str]


def __main__(args) -> None:
    # Implement the assembler
    filepath: str = args[0]
    parser = Parser(filepath=filepath)
    encoder = Code()
    output: str = ""

    if not parser.has_more_lines():
        print("Loaded an empty file.")
        return None  # Empty file
    while parser.has_more_lines():
        if parser.instruction_type() in ("A", "L"):
            symbol: str = parser.symbol()
            if parser.instruction_type() == "A":
                output += "0" + symbol + "\n"
            else:
                pass
        else:
            # It's a C-instruction; get the block information
            dest, comp, jump = parser.dest(), parser.comp(), parser.jump()
            b_dest, b_comp, b_jump = (
                encoder.dest(dest),
                encoder.comp(comp),
                encoder.jump(jump),
            )
            output += "111" + b_dest + b_comp + b_jump + "\n"
        parser.advance()  # Skip whitespace
    parser.finish()

    print(output)
    basename: str = filepath.partition(".")[0]
    with open(basename + ".hack", mode="w") as f:
        f.write(output)


if __name__ == "__main__":
    __main__(sys.argv)
