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

    @pytest.mark.parametrize(
        "original, new",
        [
            ("1 + 2", "1 + 2"),
            ("//Comment", ""),
            ("/* Comment */", ""),
            ("/* Comment \n Comment */", ""),
            ("/* Comment \n Comment */ 1 + 2", " 1 + 2"),
            ("/* Comment \n Comment */ 1 + 2 /* Comment \n Comment */", " 1 + 2 "),
            ("1 + 2 // Comment", "1 + 2 "),
            ("xab/**csfdsa fas\n */", "xab"),
        ],
    )
    def test_remove_comments(self, original: str, new: str):
        Parser = syntax_analyzer.JackTokenizer("")
        assert Parser._remove_comments(original) == new
