import os
import re 
import sys
from absl import flags
from typing import Optional, Dict


class Parser:
    def __init__(self, filepath: str):
        assert os.path.exists(filepath), "File does not exist"

        self.filepath: str = filepath
        self.file = open(filepath, "r")
        self.lines: list[str] = self.file.readlines()
        self.current_idx: int = 0

        self.symbol_table: Dict[str, int] = {
            'SP': 0, 'LCL': 1, 'ARG': 2, 'THIS': 3, 'THAT': 4, 
            'SCREEN': 16384, 'KBD': 24576
        } 
        self.symbol_table.update({f'R{n}': n for n in range(16)})

        self.fill_symbol_table() 
        self.second_pass()

    def fill_symbol_table(self) -> None:
        """Fill in (XXX) L-instructions in the symbol table."""
        
        instruction_idx: int = 0 # Current ROM index 
        if self.skip_line(self.current_line):
            self.advance() # Skip the first line if it's a comment
        while self.has_more_lines():
            # Note occurrences of variables 
            if self.instruction_type() == 'L':
                self.symbol_table[self.symbol()] = instruction_idx 
            else:
                instruction_idx += 1 
            self.advance()
        # Reset so we can parse normally 
        self.current_idx = 0 


    def second_pass(self) -> None:
        free_register: int = 16 # R0-R15 are taken 

        if self.skip_line(self.current_line):
            self.advance() # Skip the first line if it's a comment

        while self.has_more_lines():
            if self.instruction_type() == 'A' and not self.symbol().isdigit():
                symbol = self.symbol()
                if symbol not in self.symbol_table:
                    self.symbol_table[symbol] = free_register
                    free_register += 1
                new_addr = self.symbol_table[symbol]
                self.lines[self.current_idx] = "@" + str(new_addr)
                
            self.advance()
        self.current_idx = 0 

    @staticmethod 
    def replace_symbols(input: str) -> str: 
        # Sort keys by length, in descending order, to replace longer keys first
        for key in sorted(dict_mapping.keys(), key=len, reverse=True):
            # Use a regular expression to replace only whole words
            regex_pattern = r'\b' + re.escape(key) + r'\b'
            input_str = re.sub(regex_pattern, str(dict_mapping[key]), input_str)
        return input_str

    @property
    def current_line(self) -> str:
        if self.current_idx is None:
            return ""

        line: str = self.lines[self.current_idx]
        return line.strip()

    def has_more_lines(self) -> bool:
        return 0 <= self.current_idx < len(self.lines)

    def skip_line(self, line: str) -> bool:
        return line.startswith("//") or line.isspace() or line == ""

    def advance(self) -> None:
        # Skips over whitespaces and comments
        self.current_idx += 1

        while self.has_more_lines() and self.skip_line(self.current_line):
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
        return self.current_line.partition("=")[0] if "=" in self.current_line else ""

    def comp(self) -> str:
        assert self.instruction_type() == "C"
        comp_str = self.current_line
        if '=' in self.current_line:
            comp_str = comp_str.partition("=")[2]
        # Return the part between = and ; 
        return comp_str.partition(";")[0]

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
    @staticmethod 
    def dest(dest_str: str) -> str:
        """Return the 3-bit destination code. Specifies where to store comp."""
        flags = [0, 0, 0]
        if "A" in dest_str:
            flags[2] = 1
        if "D" in dest_str:
            flags[1] = 1
        if "M" in dest_str:
            flags[0] = 1

        return str(flags[2]) + str(flags[1]) + str(flags[0])

    @staticmethod
    def comp(comp_str: str) -> str:
        a_bit: int = 1 if "M" in comp_str else 0
        return str(a_bit) + _COMP_CODES[comp_str]

    @staticmethod
    def jump(jump_str: str) -> str:
        return _JUMP_CODES[jump_str]

#### The assembler 
_FILEPATH = flags.DEFINE_string("filepath", None, "The path to the file to assemble")

def to_bin_string(num: int) -> str:
    binarized_int: str = str(bin(num))[2:] # skip the '0b' prefix 
    # Make this a 15-bit number 
    return "0" * (15 - len(binarized_int)) + binarized_int

def __main__(args) -> None:
    # Parse the flags
    flags.FLAGS(args)

    parser = Parser(filepath=_FILEPATH.value)
    output: str = ""

    if not parser.has_more_lines():
        print("Loaded an empty file.")
        return None  # Empty file

    if parser.skip_line(parser.current_line):
        parser.advance() # Skip the first line if it's a comment

    while parser.has_more_lines():
        if parser.instruction_type() == 'A':
            symbol: str = parser.symbol()
            output += "0" + to_bin_string(int(symbol)) + "\n"
        elif parser.instruction_type() == 'C':
            dest, comp, jump = parser.dest(), parser.comp(), parser.jump()
            b_dest, b_comp, b_jump = (
                Code.dest(dest),
                Code.comp(comp),
                Code.jump(jump),
            )
            output += "111" + b_comp + b_dest + b_jump + "\n"
        parser.advance()  # Skip whitespace
    parser.finish()

    basename: str = _FILEPATH.value.partition(".")[0]
    with open(basename + ".hack", mode="w") as f:
        f.write(output)


if __name__ == "__main__":
    __main__(sys.argv)
