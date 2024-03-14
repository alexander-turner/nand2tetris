from absl import flags
from typing import List, Literal
import os
import sys
import re

FLAGS = flags.FLAGS
_SOURCE = flags.DEFINE_string(
    name="source", help="Name of file or folder to analyze.", default=None
)

TokenType = enum.StrEnum('TokenType', 'KEYWORD SYMBOL IDENTIFIER INT_CONST STRING_CONST')

Keyword = enum.StrEnum('Keyword', 'CLASS METHOD FUNCTION CONSTRUCTOR INT BOOLEAN CHAR VOID VAR STATIC FIELD LET DO IF ELSE WHILE RETURN TRUE FALSE NULL THIS')



def _is_str_constant(s: str) -> bool:
    """Determines whether the string representation of a proposed token is a string constant."""
    if not s:
        raise ValueError("Empty strings cannot be string constants.")

    sandwiched_by_quotes: bool = s[0] == '"' and s[-1] == '"'
    valid_intermediate_chars: bool = all(
        c.isprintable() and c not in ('"', "\n") for c in s[1:-1]
    )
    return sandwiched_by_quotes and valid_intermediate_chars


_IDENTIFIER_SEP: tuple(str) = (',', ']', ')', ';', '{', ' ', '.')

def _is_identifier(s: str) -> bool:
    """Determines whether the string representation of a proposed token is an identifier."""
    if not s:
        raise ValueError("Empty strings cannot be identifiers.")

    not_digit_start = not s[0].isdigit()
    valid_chars = all(c.isalnum() or c == "_" for c in s)
    return not_digit_start and valid_chars


class JackTokenizer:
    def __init__(self, filename: str):
        """Open the input file/stream and get ready to parse it."""
        self.filename = filename
        with open(filename, "r") as f:
            self.lines = f.readlines()

        # Preprocess lines to remove comments and whitespace
        cleaned_lines: list[str] = self._remove_comments(self.lines)
        cleaned_lines = self._remove_whitespace(cleaned_lines)
        self.remaining_text = " ".join(self.cleaned_lines)

        raise NotImplementedError

    @staticmethod
    def _remove_comments(lines: List[str]) -> List[str]:
        """Remove comments from lines of code, replacing with a single space."""

        def replace_line_comment(line: str) -> str:
            return re.sub(r"//.*", " ", line)

        def replace_block_comment(line: str) -> str:
            return re.sub(r"/\*\*?.*\*/", " ", line, flags=re.DOTALL)

        no_lines = list(map(replace_line_comment, lines))
        return list(map(replace_block_comment, no_lines))

    @staticmethod
    def _remove_whitespace(lines: List[str]) -> List[str]:
        """Remove whitespace from lines of code."""
        return [re.sub(r"\s+", " ", line).strip() for line in lines]

    def has_more_tokens(self) -> bool:
        """Are there more tokens in the input?"""
        return self.remaining_text != ""

    def advance(self):
        """Read the next token from the input and make it the current token."""
        for token_str in token_mapping.keys()
            if self.remaining_text.startswith(token_str):
                self.current_token_str = token_str
                self.remaining_text = self.remaining_text[len(token_str):]
                return
        
        if self.remaining_text[0] == '"': # String constant
            next_idx: int = self.remaining_text.index('"', 1)
            implied_str = self.remaining_text[1:next_idx]
            if not _is_str_constant(implied_str):
                raise ValueError(f"Invalid string constant: {implied_str}")
            self.current_token_str = '"' + implied_str + '"'
        elif self.remaining_text[0].isdigit(): # Integer constant
            next_idx: int = self.remaining_text.index(" ")
            implied_int_str: str = self.remaining_text[:next_idx]
            if not implied_int_str.isdigit() or int(implied_int) not in INTEGERS:
                raise ValueError(f"Invalid integer constant: {implied_int_str}")
            self.current_token_str = implied_int_str
        else: # Identifier
            # Find the next separator
            next_idx = len(self.remaining_text)
            for sep in _IDENTIFIER_SEP:
                if sep in self.remaining_text:
                    next_idx = min(next_idx, self.remaining_text.index(sep))
            implied_id: str = self.remaining_text[:next_idx]
            if not _is_identifier(implied_id):
                raise ValueError(f"Invalid identifier: {implied_id}")
            self.current_token_str = implied_id
        self.remaining_text = self.remaining_text[next_idx:]
        

    def token_type(self) -> TokenType:
        """Returns the type of the current token."""
        return TokenType[self.current_token_str.upper()]

    def keyword(self) -> str:
        """Returns the keyword which is the current token."""
        if self.token_type() != TerminalTokenType.KEYWORD:
            raise ValueError("Current token is not a keyword.")
        return 

    def symbol(self) -> str:
        """Returns the character which is the current token."""
        pass

    def identifier(self) -> str:
        """Returns the identifier which is the current token."""
        pass

    def int_val(self) -> int:
        """Returns the integer value of the current token."""
        pass

    def string_val(self) -> str:
        """Returns the string value of the current token."""
        pass


def token_xml(token: str, type: TokenType) -> str:
    return f"<{type}> {token} </{type}>"


class SyntaxParser:

    def __init__(self, lines: str | List[str]):
        """Given lines of code, preprocess them and set initial position."""
        if isinstance(lines, str):
            lines = lines.split("\n")
        # Remove comments and whitespace
        no_comments: List[str] = self._remove_comments(lines)
        lines: List[str] = self._remove_whitespace(no_comments)

        single_line = " ".join(lines)
        # These can still contain compound statements, which we'll need to handle
        self.proto_tokens = single_line.split()


if __name__ == "__main__":
    # Parse flags
    FLAGS(sys.argv)

    if _SOURCE.value.endswith(".jack"):
        files = [_SOURCE.value]
    else:
        folder = _SOURCE.value
        files = [
            os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".jack")
        ]

    # Parse each file
    for file in files:
        print(f"Analyzing {file}...")
        with open(file, "r") as f:
            lines = f.readlines()
        Parser = SyntaxParser(lines)

        basename = file.partition(".jack")[0]
        # with open(basename + ".xml", "w"):
        #     f.write(parsed_lines)
