import enum
from absl import flags
from typing import List, Literal, Tuple
import os
import sys
import re

FLAGS = flags.FLAGS
_SOURCE = flags.DEFINE_string(
    name="source", help="Name of file or folder to analyze.", default=None
)

TokenType = enum.StrEnum(
    "TokenType", "KEYWORD SYMBOL IDENTIFIER INT_CONST STRING_CONST"
)

Keyword = enum.StrEnum(
    "Keyword",
    "CLASS METHOD FUNCTION CONSTRUCTOR INT BOOLEAN CHAR VOID VAR STATIC FIELD LET DO IF ELSE WHILE RETURN TRUE FALSE NULL THIS",
)

_SYMBOLS = (
    "{",
    "}",
    "(",
    ")",
    "[",
    "]",
    ".",
    ",",
    ";",
    "+",
    "-",
    "*",
    "/",
    "&",
    "|",
    "<",
    ">",
    "=",
    "~",
)
_INTEGERS = range(32768)
_IDENTIFIER_SEP: Tuple[str] = (",", "(", "]", ")", ";", "{", " ", ".")


def _is_str_constant(s: str) -> bool:
    """Determines whether the string representation of a proposed token is a string constant."""
    if not s:
        raise ValueError("Empty strings cannot be string constants.")

    sandwiched_by_quotes: bool = s[0] == '"' and s[-1] == '"'
    valid_intermediate_chars: bool = all(
        c.isprintable() and c not in ('"', "\n") for c in s[1:-1]
    )
    return sandwiched_by_quotes and valid_intermediate_chars


def _is_identifier(s: str) -> bool:
    """Determines whether the string representation of a proposed token is an identifier."""
    if not s:
        raise ValueError("Empty strings cannot be identifiers.")

    not_digit_start = not s[0].isdigit()
    valid_chars = all([c.isalnum() or c == "_" for c in s])
    return not_digit_start and valid_chars


class JackTokenizer:
    def __init__(self, lines: list[str] | str):
        """Open the input file/stream and get ready to parse it."""
        if isinstance(lines, str):
            self.lines = lines.split("\n")

        # Preprocess lines to remove comments and whitespace
        text: str = " ".join(self.lines)
        self.remaining_text = self._trim_whitespace(self._remove_comments(text))

    @staticmethod
    def _remove_comments(original_line: str) -> str:
        """Remove comments and replace them with a single space."""

        def replace_line_comment(line: str) -> str:
            return re.sub(r"//.*", " ", line)

        def replace_block_comment(line: str) -> str:
            return re.sub(r"/\*\*?.*?\*/", " ", line, flags=re.DOTALL)

        return replace_block_comment(replace_line_comment(original_line))

    @staticmethod
    def _trim_whitespace(line: str) -> str:
        """Remove extra whitespace, leaving tokens separated by a single space."""
        return re.sub(r"\s+", " ", line).strip()

    def has_more_tokens(self) -> bool:
        """Are there more tokens in the input?"""
        return self.remaining_text != ""

    def _index_or_end(self, pattern: str) -> int:
        """Return the index of the first instance of pattern in the remaining text, or the length of the remaining text."""
        try:
            return self.remaining_text.index(pattern)
        except ValueError:
            return len(self.remaining_text)

    def advance(self):
        """Read the next token from the input and make it the current token."""
        for token_str in list(_SYMBOLS) + list(Keyword):
            if self.remaining_text.startswith(token_str):
                self.current_token_str = token_str
                self.remaining_text = self.remaining_text[len(token_str) :]
                return

        if self.remaining_text[0] == '"':  # String constant
            next_idx: int = self.remaining_text.index('"', 1)
            implied_str = self.remaining_text[1:next_idx]
            if not _is_str_constant(implied_str):
                raise ValueError(f"Invalid string constant: {implied_str}")
            self.current_token_str = '"' + implied_str + '"'
        elif self.remaining_text[0].isdigit():  # Integer constant
            next_idx: int = self._index_or_end(" ")
            implied_int_str: str = self.remaining_text[:next_idx]
            if not implied_int_str.isdigit() or int(implied_int_str) not in _INTEGERS:
                raise ValueError(f"Invalid integer constant: {implied_int_str}")
            self.current_token_str = implied_int_str
        else:  # Identifier
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
        if self.current_token_str in _SYMBOLS:
            return TerminalTokenType.SYMBOL
        elif self.current_token_str in Keyword:
            return TerminalTokenType.KEYWORD
        elif _is_str_constant(self.current_token_str):
            return TerminalTokenType.STRING_CONST
        elif _is_identifier(self.current_token_str):
            return TerminalTokenType.IDENTIFIER
        elif (
            self.current_token_str.isdigit()
            and int(self.current_token_str) in _INTEGERS
        ):
            return TerminalTokenType.INT_CONST
        else:
            raise ValueError(f"Unrecognized token: {self.current_token_str}")

    def keyword(self) -> str:
        """Returns the keyword which is the current token."""
        if self.token_type() != TerminalTokenType.KEYWORD:
            raise ValueError("Current token is not a keyword.")
        return Keyword[self.current_token_str.upper()]

    def symbol(self) -> str:
        """Returns the character which is the current token."""
        if self.token_type() != TerminalTokenType.SYMBOL:
            raise ValueError("Current token is not a symbol.")
        return self.current_token_str

    def identifier(self) -> str:
        """Returns the identifier which is the current token."""
        if self.token_type() != TerminalTokenType.IDENTIFIER:
            raise ValueError("Current token is not an identifier.")
        return self.current_token_str

    def int_val(self) -> int:
        """Returns the integer value of the current token."""
        if self.token_type() != TerminalTokenType.INT_CONST:
            raise ValueError("Current token is not an integer constant.")
        return int(self.current_token_str)

    def string_val(self) -> str:
        """Returns the string value of the current token, without the surrounding quotes."""
        if self.token_type() != TerminalTokenType.STRING_CONST:
            raise ValueError("Current token is not a string constant.")
        return self.current_token_str[1:-1]


def token_xml(token: str, type: TokenType) -> str:
    return f"<{type}> {token} </{type}>"


class SyntaxParser:

    def __init__(self, lines: str | List[str]):
        """Given lines of code, preprocess them and set initial position."""
        if isinstance(lines, str):
            lines = lines.split("\n")
        # Remove comments and whitespace
        no_comments: List[str] = self._remove_comments(lines)
        lines: List[str] = self._trim_whitespace(no_comments)

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
        Parser = JackTokenizer(lines)

        basename = file.partition(".jack")[0]
        # with open(basename + ".xml", "w"):
        #     f.write(parsed_lines)
