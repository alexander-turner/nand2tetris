import pytest
import syntax_analyzer


@pytest.mark.parametrize(
    "original, new",
    [
        ("1 + 2", "1+2"),
        ("  1 22-2", "122-2"),
        ("\n\n 1! 2      \n ", "1!2"),
        ("", ""),
        ("\n", ""),
        ("  \n  1  ", "1"),
    ],
)
def test_remove_whitespace(original: str, new: str):
    Parser = syntax_analyzer.JackTokenizer()
    assert syntax_analyzer._remove_whitespace(original) == new
