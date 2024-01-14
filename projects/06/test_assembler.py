import pytest 
import pytest_mock
import assembler 

@pytest.mark.parametrize("comp_str, target", 
                        [('M+1', '1110111'), ('A+1', '0110111'), ('D+1', '0011111'), ('A', '0110000'), ('D+A', '0000010'), ('D', ('0001100'))])
def test_comp(comp_str: str, target: str) -> None:
    encoder = assembler.Code() 
    assert encoder.comp(comp_str) == target 


@pytest.mark.parametrize("jump_str, target", 
                        [('JGT', '001'), ('JEQ', '010'), ('JGE', '011'), ('JLT', '100'), ('JNE', '101'), ('JLE', '110'), ('JMP', '111')])
def test_jump(jump_str: str, target: str) -> None:
    encoder = assembler.Code() 
    assert encoder.jump(jump_str) == target 

@pytest.mark.parametrize("dest_str, target", 
                        [('', '000'), ('M', '001'), ('D', '010'), ('A', '100')])
def test_dest(dest_str: str, target: str) -> None:
    encoder = assembler.Code() 
    assert encoder.dest(dest_str) == target 

@pytest.mark.parametrize("dest_line, target", 
                        [('M=1', 'M'), ('D=A', 'D'), ('A=D', 'A'), ('D;JMP', '')])
def test_parser_dest(mocker, dest_line: str, target: str) -> None:
    mocker.patch("builtins.open", mocker.mock_open(read_data=dest_line))
    mocker.patch("os.path.exists", return_value=True)

    parser = assembler.Parser('')
    assert parser.dest() == target 

@pytest.mark.parametrize("comp_line, target", 
                        [('M=1', '1'), ('D=A', 'A'), ('A=D', 'D'), ('D;JMP', 'D'), ('D=D+A', 'D+A'), ('D=D-M', 'D-M'), ('D=D&A', 'D&A'), ('D=D|A', 'D|A'), ('D=D+M', 'D+M'), ('D=D-M', 'D-M'), ('D=D&M', 'D&M'), ('D=D|M', 'D|M')])
def test_parser_comp(mocker, comp_line: str, target: str) -> None:
    mocker.patch("builtins.open", mocker.mock_open(read_data=comp_line))
    mocker.patch("os.path.exists", return_value=True)

    parser = assembler.Parser('')
    assert parser.comp() == target 

@pytest.mark.parametrize("jump_str, target", 
                        [('M=1', ''), ('D;JGT', 'JGT'), ('0;JMP', 'JMP'), ('D;JMP', 'JMP')])
def test_parser_comp(mocker, jump_str: str, target: str) -> None:
    mocker.patch("builtins.open", mocker.mock_open(read_data=jump_str))
    mocker.patch("os.path.exists", return_value=True)

    parser = assembler.Parser('')
    assert parser.jump() == target 

