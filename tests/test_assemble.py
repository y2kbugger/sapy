from sapy.assembler import MNEMONIC as M, translate_instruction, assemble

def test_implied():
    bytecode = translate_instruction('HLT')
    assert bytecode == [0xFF]

def test_immediate():
    bytecode = translate_instruction('LDA #$C2')
    assert bytecode == [0x20, 0xC2]

def test_absolute():
    bytecode = translate_instruction('LDA $C2')
    assert bytecode == [0x00, 0xC2]

def test_indirect():
    bytecode = translate_instruction('LDA ($C2)')
    assert bytecode == [0x10, 0xC2]

def test_absolute_branching():
    bytecode = translate_instruction('JMP $C2')
    assert bytecode == [0x34, 0xC2]

def test_indirect_branching():
    bytecode = translate_instruction('JMP ($C2)')
    assert bytecode == [0x44, 0xC2]

def test_indirect():
    bytecode = translate_instruction('LDA ($C2)')
    assert bytecode == [0x10, 0xC2]

def test_can_read_instructions_from_source_assembly():
    code = "LDA ($C2)"
    bytecode = assemble(code)
    assert bytecode == [0x10, 0xC2]

def test_can_split_incoming_source_assembly():
    code = ("LDA ($C2)"
        "\nJMP ($C2)")
    bytecode = assemble(code)
    assert bytecode == [0x10, 0xC2, 0x44, 0xC2]

def test_can_handle_source_comments():
    code = """
        LDA ($C2)   ; don't know why i do this
        JMP ($C2)
    """
    bytecode = assemble(code)
    assert bytecode == [0x10, 0xC2, 0x44, 0xC2]

def test_can_handle_full_line_source_comments():
    code = """
        ;LDA ($C2)   ; don't know why i do this
        JMP ($C2)
    """
    bytecode = assemble(code)
    assert bytecode == [0x44, 0xC2]

def test_can_deal_with_indented_assembly_code():
    code = """
        LDA ($C2)
        JMP ($C2)
    """
    bytecode = assemble(code)
    assert bytecode == [0x10, 0xC2, 0x44, 0xC2]

def test_use_lables():
    code = """
        LDA ($C2)
        back:
        JMP back
    """
    bytecode = assemble(code)
    assert bytecode == [0x10, 0xC2, 0x34, 0x02]

def test_lables_with_indirect():
    code = """
        LDA ($C2)
        back:
        JMP (back)
    """
    bytecode = assemble(code)
    assert bytecode == [0x10, 0xC2, 0x44, 0x02]

def test_lable_defined_after_use():
    code = """
        LDA ($C2)
        JMP (back)
        LDA ($C2)
        back:
    """
    bytecode = assemble(code)
    assert bytecode == [0x10, 0xC2, 0x44, 0x06, 0x10, 0xC2,]

# def test_missing_opcode_arg_raises()
