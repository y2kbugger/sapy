from .assembler import MNEMONIC as M, assemble

def test_implied():
    instructions = ['HLT']
    bytecode = assemble(instructions)
    assert bytecode == [0xFF]

def test_immediate():
    instructions = ['LDA #$C2']
    bytecode = assemble(instructions)
    assert bytecode == [0x20, 0xC2]

def test_absolute():
    instructions = ['LDA $C2']
    bytecode = assemble(instructions)
    assert bytecode == [0x00, 0xC2]

def test_indirect():
    instructions = ['LDA ($C2)']
    bytecode = assemble(instructions)
    assert bytecode == [0x10, 0xC2]

def test_absolute_branching():
    instructions = ['JMP $C2']
    bytecode = assemble(instructions)
    assert bytecode == [0x34, 0xC2]

def test_indirect_branching():
    instructions = ['JMP ($C2)']
    bytecode = assemble(instructions)
    assert bytecode == [0x44, 0xC2]

# def test_missing_arg_raises()
