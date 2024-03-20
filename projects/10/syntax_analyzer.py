import enum
from absl import flags
import functools
import logging
from typing import List, Literal, Tuple, Iterable, Collection, Callable
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

_KEYWORD_CONSTANTS = ("true", "false", "null", "this")
_OPS = ("+", "-", "*", "/", "&", "|", "<", ">", "=")
_UNARY_OPS = ("-", "~")
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

    @staticmethod
    def token_type(token_str: str) -> TokenType:
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

    @staticmethod
    def keyword(token_str: str) -> str:
        """Returns the keyword which is the current token."""
        if JackTokenizer.token_type(token_str) != TokenType.KEYWORD:
            raise ValueError("Current token is not a keyword.")
        return Keyword[token_str.upper()]

    @staticmethod
    def symbol(token_str: str) -> str:
        """Returns the character which is the current token."""
        if JackTokenizer.token_type(token_str) != TokenType.SYMBOL:
            raise ValueError("Current token is not a symbol.")
        return token_str

    @staticmethod
    def identifier(token_str: str) -> str:
        """Returns the identifier which is the current token."""
        if JackTokenizer.token_type(token_str) != TokenType.IDENTIFIER:
            raise ValueError("Current token is not an identifier.")
        return token_str

    @staticmethod
    def int_val(token_str: str) -> int:
        """Returns the integer value of the current token."""
        if JackTokenizer.token_type(token_str) != TokenType.INT_CONST:
            raise ValueError("Current token is not an integer constant.")
        return int(token_str)

    @staticmethod
    def string_val(token_str: str) -> str:
        """Returns the string value of the current token, without the surrounding quotes."""
        if JackTokenizer.token_type(token_str) != TokenType.STRING_CONST:
            raise ValueError("Current token is not a string constant.")
        return token_str[1:-1]

    @staticmethod
    def token_val(token: str) -> str | int:
        tok_type = JackTokenizer.token_type(token)
        match tok_type:
            case TokenType.KEYWORD:
                to_return = JackTokenizer.keyword(token)
            case TokenType.SYMBOL:
                to_return = JackTokenizer.symbol(token)
            case TokenType.IDENTIFIER:
                to_return = JackTokenizer.identifier(token)
            case TokenType.INT_CONST:
                to_return = JackTokenizer.int_val(token)
            case TokenType.STRING_CONST:
                to_return = JackTokenizer.string_val(token)
            case _:
                raise ValueError(f"Unrecognized token: {token}")
        return to_return

    def write_tokens(self, filename: str) -> None:
        with open(filename, "w") as f:
            f.write("<tokens>\n")
        for tok in self.tokens:
            self.write_token(filename, tok)

        with open(filename, "a") as f:
            f.write("\n</tokens>")

    @staticmethod
    def write_token(filename: str, token: Iterable[str]) -> None:
        with open(filename, "a") as f:
            tok_type = JackTokenizer.token_type(token)
            tok_val = JackTokenizer.token_val(token)

            to_write = _escape_xml(tok_val)
            to_write = token_xml(token=to_write, tok_type=tok_type)
            f.write(to_write + "\n")


def _escape_xml(xml_string: str) -> str:
    escaped_str = str(xml_string)
    for pattern, target in (
        (r"&", "&amp;"),
        (r"<", "&lt;"),
        (r">", "&gt;"),
        (r'"', "&quot;"),
    ):
        escaped_str = re.sub(pattern, target, escaped_str)
    return escaped_str


def token_xml(token: str, tok_type: TokenType) -> str:
    if tok_type == TokenType.STRING_CONST:
        tok_type_str = "stringConstant"
    elif tok_type == TokenType.INT_CONST:
        tok_type_str = "integerConstant"
    else:
        tok_type_str = str(tok_type)
    return f"<{tok_type_str}> {token} </{tok_type_str}>"


class CompilationEngine:
    def __init__(self, input_tokens: Iterable[str], output_filename: str) -> None:
        self.tokens = input_tokens
        self.output_filename = output_filename

    def _write(self, s: str) -> None:
        with open(self.output_filename, "a") as f:
            f.write(s)

    @property
    def current_token(self) -> str:
        return self.tokens[0]

    def increment_token(self) -> None:
        self.tokens = self.tokens[1:]

    def _error_or_write_targets(self, targets: str | Collection[str]) -> None:
        if isinstance(targets, str):
            targets = [targets]  # Turn into collection
        if self.current_token not in targets:
            raise ValueError(f"Expected member of {targets}, got {self.current_token}")
        JackTokenizer.write_token(self.output_filename, self.current_token)
        self.increment_token()

    def _error_or_write_type(self, tok_type: TokenType) -> None:
        current_type = JackTokenizer.token_type(self.current_token)
        if current_type != tok_type:
            raise ValueError(f"Expected {tok_type}, got {current_type}")
        JackTokenizer.write_token(self.output_filename, self.current_token)
        self.increment_token()

    def compile_class(self) -> None:
        """Compiles a complete class."""
        # 'class' className '{' class_var_dec* subroutine_dec* '}'
        self._write("<class>")

        self._error_or_write_target("class")
        self._error_or_write_type(TokenType.IDENTIFIER)
        self._error_or_write_target("{")

        while True:
            if self.current_token in ("static", "field"):
                self.compile_class_var_dec()
            elif self.current_token in ("constructor", "function", "method"):
                self.compile_subroutine()
            else:
                break

        self._error_or_write_target("}")
        self._write("</class>")

    def compile_class_var_dec(self) -> None:
        """Compiles a static variable declaration, or a field declaration.

        Grammar: ('static' | 'field') type varName (',' varName)* ';'
        """
        self._write("<classVarDec>")

        self._error_or_write_target(("static", "field"))
        self.compile_type()
        self._error_or_write_type(TokenType.IDENTIFIER)
        while self.current_token == ",":
            self._error_or_write_target(",")
            self._error_or_write_type(TokenType.IDENTIFIER)

        self._error_or_write_target(";")
        self._write("</classVarDec>")

    def compile_type(self) -> None:
        """Compiles a type. Grammar: 'int' | 'char' | 'boolean' | className."""
        if self.current_token in ("int", "char", "boolean"):
            self._error_or_write_target(("int", "char", "boolean"))
        else:
            self._error_or_write_type(TokenType.IDENTIFIER)

    def compile_subroutine(self) -> None:
        """Compiles a complete method, function, or constructor."""
        # ('constructor' | 'function' | 'method') ('void' | type) subroutineName '(' parameterList ')' subroutineBody
        self._write("<subroutineDec>")
        self._error_or_write_target(("constructor", "function", "method"))

        if self.current_token == "void":
            self._error_or_write_target("void")
        else:
            self.compile_type()

        self._error_or_write_type(TokenType.IDENTIFIER)  # Subroutine Name
        self._error_or_write_target("(")
        self.compile_parameter_list()
        self._error_or_write_target(")")
        self.compile_subroutine_body()
        self._write("</subroutineDec>")

    def compile_parameter_list(self) -> None:
        """Compiles a (possibly empty) parameter list."""
        # ( (type varName) (',' type varName)* )?
        self._write("<parameterList>")
        if self.current_token == ")":  # No parameters
            return

        self.compile_type()
        self._error_or_write_type(TokenType.IDENTIFIER)
        while self.current_token == ",":  # The parameter list
            self._error_or_write_target(",")
            self.compile_type()
            self._error_or_write_type(TokenType.IDENTIFIER)
        self._write("</parameterList>")

    def compile_subroutine_body(self) -> None:
        """Compiles a subroutine's body."""
        # '{' varDec* statements '}'
        self._write("<subroutineBody>")

        self._error_or_write_target("{")
        while self.current_token == "var":
            self.compile_var_dec()
        self.compile_statements()
        self._error_or_write_target("}")

        self._write("</subroutineBody>")

    def compile_var_dec(self) -> None:
        """Compiles a var declaration."""
        # 'var' type varName (',' varName)* ';'
        self._error_or_write_target("var")
        self.compile_type()
        self._error_or_write_type(TokenType.IDENTIFIER)
        while self.current_token == ",":
            self._error_or_write_target(",")
            self._error_or_write_type(TokenType.IDENTIFIER)
        self._error_or_write_target(";")

    def compile_statements(self) -> None:
        self._write("<statements>")
        while self.current_token in ("let", "if", "while", "do", "return"):
            match self.current_token:
                case "let":
                    self.compile_let()
                case "if":
                    self.compile_if()
                case "while":
                    self.compile_while()
                case "do":
                    self.compile_do()
                case "return":
                    self.compile_return()
        self._write("</statements>")

    def compile_let(self) -> None:
        """Compiles a let statement."""
        # 'let' varName ('[' expression ']')? '=' expression ';'
        self._write("<letStatement>")

        self._error_or_write_target("let")
        self._error_or_write_type(TokenType.IDENTIFIER)
        if self.current_token == "[":
            self._error_or_write_target("[")
            self.compile_expression()
            self._error_or_write_target("]")
        self._error_or_write_target("=")
        self.compile_expression()
        self._error_or_write_target(";")

        self._write("</letStatement>")

    def compile_if(self) -> None:
        """Compiles an if statement."""
        # 'if' '(' expression ')' '{' statements '}' ('else' '{' statements '}')?
        self._write("<ifStatement>")

        self._error_or_write_target("if")
        self._error_or_write_target("(")
        self.compile_expression()
        self._error_or_write_target(")")
        self._error_or_write_target("{")
        self.compile_statements()
        self._error_or_write_target("}")
        if self.current_token == "else":
            self._error_or_write_target("else")
            self._error_or_write_target("{")
            self.compile_statements()
            self._error_or_write_target("}")

        self._write("</ifStatement>")

    def compile_while(self) -> None:
        """Compiles a while statement."""
        # 'while' '(' expression ')' '{' statements '}'
        self._write("<whileStatement>")

        self._error_or_write_target("while")
        self._error_or_write_target("(")
        self.compile_expression()
        self._error_or_write_target(")")
        self._error_or_write_target("{")
        self.compile_statements()
        self._error_or_write_target("}")

        self._write("</whileStatement>")

    def compile_do(self) -> None:
        """Compiles a do statement."""
        # 'do' subroutineCall ';'
        self._write("<doStatement>")

        self._error_or_write_target("do")
        self.compile_subroutine_call()
        self._error_or_write_target(";")

        self._write("</doStatement>")

    def compile_return(self) -> None:
        """Compiles a return statement."""
        # 'return' expression? ';'
        self._write("<returnStatement>")
        self._error_or_write_target("return")
        if self.current_token != ";":
            self.compile_expression()
        self._error_or_write_target(";")
        self._write("</returnStatement>")

    def compile_expression(self) -> None:
        """Compiles an expression."""
        # term (op term)*
        self._write("<expression>")
        self.compile_term()
        while self.current_token in _OPS:
            self._error_or_write_target(_OPS)
            self.compile_term()
        self._write("</expression>")

    def compile_term(self) -> None:
        """Compiles a term."""
        # integerConstant | stringConstant | keywordConstant | varName | varName '[' expression ']' | subroutineCall | '(' expression ')' | unaryOp term
        self._write("<term>")
        current_type: TokenType = JackTokenizer.token_type(self.current_token)

        # NOTE assumes at least 2 tokens remaining
        is_array: bool = current_type == TokenType.IDENTIFIER and self.tokens[1] == "["
        is_subroutine: bool = current_type == TokenType.IDENTIFIER and self.tokens[
            1
        ] in ("(", ".")
        three_types: Tuple[TokenType, ...] = (
            TokenType.INT_CONST,
            TokenType.STRING_CONST,
            TokenType.IDENTIFIER,
        )
        if not is_array:
            if self.current_token in _KEYWORD_CONSTANTS:
                self._error_or_write_target(_KEYWORD_CONSTANTS)
            elif current_type in three_types:
                self._error_or_write_type(three_types)
            else:
                raise ValueError(f"Invalid term: {self.current_token}")
        elif is_array:
            self._error_or_write_type(TokenType.IDENTIFIER)
            self._error_or_write_target("[")
            self.compile_expression()
            self._error_or_write_target("]")
        elif self.current_token == "(":
            self._error_or_write_target("(")
            self.compile_expression()
            self._error_or_write_target(")")
        elif self.current_token in _UNARY_OPS:
            self._error_or_write_target(_UNARY_OPS)
            self.compile_term()
        elif is_subroutine:
            self.compile_subroutine_call()
        else:
            raise ValueError(f"Invalid term: {self.current_token}")

        self._write("</term>")

    def compile_subroutine_call(self) -> None:
        self._error_or_write_type(TokenType.IDENTIFIER)
        if self.current_token == ".":
            self._error_or_write_target(".")
            self._error_or_write_type(TokenType.IDENTIFIER)

        # The ( expressionList ) part
        self._error_or_write_target("(")
        self.compile_expression_list()
        self._error_or_write_target(")")

    def compile_expression_list(self) -> None:
        """Compiles a (possibly empty) comma-separated list of expressions."""
        self._write("<expressionList>")
        if self.current_token == ")":
            return
        self.compile_expression()
        while self.current_token == ",":
            self._error_or_write_target(",")
            self.compile_expression()
        self._write("</expressionList>")


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
