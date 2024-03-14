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
        Parser = syntax_analyzer.JackTokenizer("")
        assert Parser._trim_whitespace(original) == new
