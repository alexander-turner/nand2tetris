import enum
from absl import flags
import logging
from typing import List, Literal, Tuple, Sequence
import os
import sys
import re

logging.basicConfig(level=logging.DEBUG)

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
_SEPARATORS: Tuple[str] = (",", "[", "]", "(", ")", ";", "{", "}", " ", ".")


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
            lines = lines.split("\n")

        # Preprocess lines to remove comments and whitespace
        text: str = " ".join(lines)
        self.remaining_text = self._trim_whitespace(self._remove_comments(text))

        self.tokens: List[str] = []

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
        logging.debug(f"{self.remaining_text=} in advance() call.\n\n")

        for token_str in list(_SYMBOLS) + list(Keyword):
            if self.remaining_text.startswith(token_str):
                self.tokens.append(token_str)
                self.remaining_text = self.remaining_text[len(token_str) :]
                if self.remaining_text.startswith(" "):
                    self.remaining_text = self.remaining_text[1:]
                return

        if self.remaining_text[0] == '"':  # String constant
            next_idx: int = self.remaining_text.index('"', 1) + 1
            implied_str = self.remaining_text[:next_idx]  # Quote-inclusive
            if not _is_str_constant(implied_str):
                raise ValueError(f"Invalid string constant: {implied_str}")
            self.tokens.append(implied_str)
        elif self.remaining_text[0].isdigit():  # Integer constant
            implied_int_str = self._str_until_separator()
            next_idx: int = len(implied_int_str)
            if not implied_int_str.isdigit() or int(implied_int_str) not in _INTEGERS:
                raise ValueError(f"Invalid integer constant: {implied_int_str}")
            self.tokens.append(implied_int_str)
        else:  # Identifier
            implied_id: str = self._str_until_separator()
            next_idx: int = len(implied_id)
            logging.debug(f"{implied_id=} and {next_idx=}\n")
            if not _is_identifier(implied_id):
                raise ValueError(f"Invalid identifier: {implied_id}")
            self.tokens.append(implied_id)
        self.remaining_text = self.remaining_text[next_idx:]
        if self.remaining_text.startswith(" "):
            self.remaining_text = self.remaining_text[1:]

    def _str_until_separator(self) -> str:
        next_idx = len(self.remaining_text)
        for sep in _SEPARATORS:
            if sep in self.remaining_text:
                next_idx = min(next_idx, self.remaining_text.index(sep))
        return self.remaining_text[:next_idx]

    def token_type(self, token_str: str) -> TokenType:
        """Returns the type of the current token."""
        if token_str in _SYMBOLS:
            return TokenType.SYMBOL
        elif token_str in Keyword:
            return TokenType.KEYWORD
        elif _is_str_constant(token_str):
            return TokenType.STRING_CONST
        elif _is_identifier(token_str):
            return TokenType.IDENTIFIER
        elif token_str.isdigit() and int(token_str) in _INTEGERS:
            return TokenType.INT_CONST
        else:
            raise ValueError(f"Unrecognized token: {token_str}")

    def keyword(self, token_str: str) -> str:
        """Returns the keyword which is the current token."""
        if self.token_type(token_str) != TokenType.KEYWORD:
            raise ValueError("Current token is not a keyword.")
        return Keyword[token_str.upper()]

    def symbol(self, token_str: str) -> str:
        """Returns the character which is the current token."""
        if self.token_type(token_str) != TokenType.SYMBOL:
            raise ValueError("Current token is not a symbol.")
        return token_str

    def identifier(self, token_str: str) -> str:
        """Returns the identifier which is the current token."""
        if self.token_type(token_str) != TokenType.IDENTIFIER:
            raise ValueError("Current token is not an identifier.")
        return token_str

    def int_val(self, token_str: str) -> int:
        """Returns the integer value of the current token."""
        if self.token_type(token_str) != TokenType.INT_CONST:
            raise ValueError("Current token is not an integer constant.")
        return int(token_str)

    def string_val(self, token_str: str) -> str:
        """Returns the string value of the current token, without the surrounding quotes."""
        if self.token_type(token_str) != TokenType.STRING_CONST:
            raise ValueError("Current token is not a string constant.")
        return token_str[1:-1]

    def write_tokens(self, filename: str) -> None:
        with open(filename, "w") as f:
            f.write("<tokens>\n")
            for tok in self.tokens:
                tok_type = self.token_type(tok)
                match tok_type:
                    case TokenType.KEYWORD:
                        to_write = self.keyword(tok)
                    case TokenType.SYMBOL:
                        to_write = self.symbol(tok)
                    case TokenType.IDENTIFIER:
                        to_write = self.identifier(tok)
                    case TokenType.INT_CONST:
                        to_write = self.int_val(tok)
                    case TokenType.STRING_CONST:
                        to_write = self.string_val(tok)
                    case _:
                        raise ValueError(f"Unrecognized token: {self.tokens[idx]}")
                to_write = token_xml(token=to_write, tok_type=tok_type) + "\n"
                f.write(to_write)

            f.write("\n</tokens>")


def _escape_xml(xml_string: str) -> str:
    # TODO get escape sequences for " and &
    conversion_mapping = {"<": "&lt", ">": "&gt", '"': '"', "&": "&"}
    escaped_str = re.sub(r"<", "&lt", xml_string)
    escaped_str = re.sub(r">", "&gt", escaped_str)
    escaped_str = re.sub(r'"', '"', escaped_str)  # TODO
    return re.sub(r"&", "&", escaped_str)  # TODO


def token_xml(token: str, tok_type: TokenType) -> str:
    return f"<{tok_type}> {token} </{tok_type}>"


class CompilationEngine:
    def __init__(self, input_tokens: Sequence[str], output_filename: str) -> None:
        self.tokens = input_tokens
        self.output_filename = output_filename

    def compile_class(self) -> None:
        """Compiles a complete class."""
        # 'class' className '{' class_var_dec* subroutine_dec* '}'

        raise NotImplementedError

    def compile_class_var_dec(self) -> None:
        """Compiles a static variable declaration, or a field declaration."""


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

        # Clears out whitespace and comments
        tokenizer = JackTokenizer(lines)
        while tokenizer.has_more_tokens():
            tokenizer.advance()  # advance() calls append to tokens

        basename = file.partition(".jack")[0]
        xml_name = basename + "-user-T.xml"
        tokenizer.write_tokens(xml_name)
