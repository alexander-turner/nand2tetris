import pytest
import syntax_analyzer


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
            (" + 2", "+"),
            (" 2", "2"),
            ("  1  ", "1"),
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

        token_str = tokenizer.current_token_str
        assert token_str == target

        # Assert the remaining text is as expected
        next_idx: int = len(token_str)
        assert tokenizer.remaining_text == original.strip()[next_idx:]

    def test_token_type(
        self, original: str, tok_type: syntax_analyzer.TokenType
    ) -> None:
        pass
