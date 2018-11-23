from .assembler import MNEMONIC as M, assemble

def test_parameterless():
    instructions = ['HLT']
    bytecode = assemble(instructions)
    assert bytecode == [M['HLT']]


def test_absolute():
    instructions = ['LDA $C2']
    bytecode = assemble(instructions)
    assert bytecode == [M['LDA'], 0xC2]

# def test_missing_arg_raises()
