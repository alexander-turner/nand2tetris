import pytest
from typing import Tuple
import frozendict
import glob
import pyfakefs
import logging
import re
import syntax_analyzer

_FILES_TO_OPEN: Tuple[str, ...] = (
    *glob.glob("Square/*.jack"),
    *glob.glob("ExpressionLessSquare/*.jack"),
    *glob.glob("ArrayTest/*.jack"),
)

# Get the .jack files
_JACK_TEXTS = frozendict.frozendict(
    {filename: open(filename, "r").read() for filename in _FILES_TO_OPEN}
)
# Get the T.xml files
_TARGET_TOKENIZED_TEXTS = frozendict.frozendict(
    {
        filename: open(filename.replace(".jack", "T.xml"), "r").read()
        for filename in _FILES_TO_OPEN
    }
)
# Get the .xml files
_TARGET_TEXTS = frozendict.frozendict(
    {
        filename: open(filename.replace(".jack", ".xml"), "r").read()
        for filename in _FILES_TO_OPEN
    }
)


class TestJackTokenizer:

    @pytest.mark.parametrize(
        "original, new",
        [
            ("1 + 2", "1 + 2"),
            ("  1 22-2", "1 22-2"),
            ("\n\n 1! 2      \n ", "1! 2"),
            ("", ""),
            ("\n", ""),
            ("  \n  1  ", "1"),
        ],
    )
    def test_trim_whitespace(self, original: str, new: str):
        tokenizer = syntax_analyzer.JackTokenizer("")
        assert tokenizer._trim_whitespace(original) == new

    @pytest.mark.parametrize(
        "original, new",
        [
            ("1 + 2", "1 + 2"),
            ("//Comment", " "),
            ("/* Comment */", " "),
            ("/* Comment \n Comment */", " "),
            ("/* Comment \n Comment */ 1 + 2", "  1 + 2"),
            ("/* Comment \n Comment */ 1 + 2 /* Comment \n Comment */", "  1 + 2  "),
            ("1 + 2 // Comment", "1 + 2  "),
            ("xab/**csfdsa fas\n */", "xab "),
        ],
    )
    def test_remove_comments(self, original: str, new: str):
        tokenizer = syntax_analyzer.JackTokenizer("")
        assert tokenizer._remove_comments(original) == new

    @pytest.mark.parametrize(
        "original, truth_val",
        [
            ("1 + 2", True),
            ("1 + 2 // Comment", True),
            ("1 + 2 /* Comment \n Comment */", True),
            ("1 + 2 /* Comment \n Comment */", True),
            ("xab/**csfdsa fas\n */", True),
            ("//Comment", False),
            ("/* Comment */", False),
            ("/* Comment \n Comment */", False),
            ("/* Comment \n Comment */ 1 + 2", True),
            ("/* Comment \n Comment */ 1 + 2 /* Comment \n Comment */", True),
        ],
    )
    def test_has_more_tokens(self, original: str, truth_val: bool) -> None:
        tokenizer = syntax_analyzer.JackTokenizer(original)
        assert tokenizer.has_more_tokens() == truth_val, tokenizer.remaining_text

    @pytest.mark.parametrize(
        "original, target",
        [
            ("1 + 2", "1"),
            ("+ 2", "+"),
            ("2", "2"),
            ("xab ALBERT", "xab"),
            ("5123 31 !!", "5123"),
            ("_FDAV( ", "_FDAV"),
            ("var{", "var"),
            ('"Hi!"', '"Hi!"'),
            *[(s, s) for s in syntax_analyzer._SYMBOLS],
        ],
    )
    def test_advance(self, original: str, target: str) -> None:
        tokenizer = syntax_analyzer.JackTokenizer(original)
        tokenizer.advance()

        token_str = tokenizer.tokens[-1]
        assert token_str == target

        # Assert the remaining text is as expected
        next_idx: int = len(token_str)
        if len(original) > next_idx and original[next_idx] == " ":
            next_idx += 1
        assert (
            tokenizer.remaining_text == original[next_idx:].rstrip()
        ), f"{tokenizer.remaining_text=} != {original[next_idx:]=}; {tokenizer.tokens=}"

    @pytest.mark.parametrize(
        "original, target",
        [
            ("1 + 2", "+"),
            (" + 2", "2"),
            ("xab ALBERT", "ALBERT"),
            ("5123 31 !!", "31"),
            ("_FDAV( ", "("),
            ("var{", "{"),
        ],
    )
    def test_second_advance(self, original: str, target: str) -> None:
        tokenizer = syntax_analyzer.JackTokenizer(original)
        tokenizer.advance()
        tokenizer.advance()

        token_str = tokenizer.tokens[-1]
        assert token_str == target

    @pytest.mark.parametrize(
        "original, tok_type",
        [
            ("1", syntax_analyzer.TokenType.INT_CONST),
            ("+", syntax_analyzer.TokenType.SYMBOL),
            ("2", syntax_analyzer.TokenType.INT_CONST),
            ("xab", syntax_analyzer.TokenType.IDENTIFIER),
            ("5123", syntax_analyzer.TokenType.INT_CONST),
            ("_FDAV", syntax_analyzer.TokenType.IDENTIFIER),
            ("var", syntax_analyzer.TokenType.KEYWORD),
            ('"Hi!"', syntax_analyzer.TokenType.STRING_CONST),
            *[(s, syntax_analyzer.TokenType.SYMBOL) for s in syntax_analyzer._SYMBOLS],
        ],
    )
    def test_token_type(
        self, original: str, tok_type: syntax_analyzer.TokenType
    ) -> None:
        tokenizer = syntax_analyzer.JackTokenizer(original)
        tokenizer.advance()
        assert tokenizer.token_type(tokenizer.tokens[-1]) == tok_type

    @pytest.mark.parametrize(
        "filename",
        _FILES_TO_OPEN,
    )
    def test_cmp_tokenized_output(self, filename: str, fs) -> None:
        lines = _JACK_TEXTS[filename]
        target_text: str = _TARGET_TOKENIZED_TEXTS[filename]
        filename = filename.partition("/")[-1]  # fakefs has no directories

        tokenizer = syntax_analyzer.JackTokenizer(lines)
        while tokenizer.has_more_tokens():
            tokenizer.advance()

        user_generated_filename = filename.replace(".jack", "-user-T.xml")
        tokenizer.write_tokens(user_generated_filename)

        with open(user_generated_filename, "r") as f:
            user_text = f.read()

        assert _cmp_ignore_whitespace(target_text, user_text), f"{filename=}"

    @pytest.mark.parametrize(
        "filename",
        _FILES_TO_OPEN,
    )
    def test_cmp_engine_output(self, filename: str, fs) -> None:
        lines = _JACK_TEXTS[filename]
        target_text: str = _TARGET_TEXTS[filename]
        filename = filename.partition("/")[-1]  # fakefs has no directories

        tokenizer = syntax_analyzer.JackTokenizer(lines)
        while tokenizer.has_more_tokens():
            tokenizer.advance()

        user_generated_filename = filename.replace(".jack", "-user.xml")
        engine = syntax_analyzer.CompilationEngine(
            tokenizer.tokens, user_generated_filename
        )
        engine.compile_class()

        with open(user_generated_filename, "r") as f:
            user_text = f.read()

        assert _cmp_ignore_whitespace(target_text, user_text), f"{filename=}"


def _cmp_ignore_whitespace(s1: str, s2: str) -> bool:
    s1_no_whitespace = re.sub(r"\s+", "", s1)
    s2_no_whitespace = re.sub(r"\s+", "", s2)
    for idx, (ch1, ch2) in enumerate(zip(s1_no_whitespace, s2_no_whitespace)):
        if ch1 != ch2:
            raise Exception(f"{idx=}: {ch1=} != {ch2=}")
            # logging.error(f"{idx=}: {ch1=} != {ch2=}")
    return s1_no_whitespace == s2_no_whitespace
