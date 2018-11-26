from typing import List

from .sapy import opcode_map, mnemonics, implied, absolute, absolute_branching, indirect, indirect_branching, immediate


MNEMONIC = {m.mnemonic:m for m in mnemonics}

def assemble(instructions) -> List[int]:
    bytecode = []
    for i in instructions:
        bytecode.extend(translate_instruction(i))
    return bytecode

def translate_instruction(instruction: str) -> List[int]:
    if not ' ' in instruction:
        # implied addressing
        opcode = MNEMONIC[instruction]
        return [(implied.high_nibble << 4) + opcode.low_nibble]

    mne_chars, arg = instruction.split(' ', 1)
    mne = MNEMONIC[mne_chars]

    # Should be one or the other
    # This could only go wrong with misconfigured mnemonics
    ads = mne.addressing_modes
    assert not ((indirect in ads) and (indirect_branching in ads))
    assert not ((absolute in ads) and (indirect_branching in ads))
    assert not ((absolute_branching in ads) and (indirect in ads))
    assert not ((absolute_branching in ads) and (absolute in ads))

    data_addressing_modes = [immediate, absolute, indirect]
    branching_addressing_modes = [absolute_branching, indirect_branching]

    if any(ad in data_addressing_modes for ad in ads):
        if arg[0] == '$':
            arg_addressing_mode = absolute
            arg_val = int(arg[1:], 16)
        elif arg[0] == '#' and arg[1] == '$': 
            arg_val = int(arg[2:], 16)
            arg_addressing_mode = immediate
        elif arg[0] == '(' and arg[1] == '$' and arg[-1] == ')': 
            arg_val = int(arg[2:-1], 16)
            arg_addressing_mode = indirect
    if any(ad in branching_addressing_modes for ad in ads):
        if arg[0] == '$':
            arg_addressing_mode = absolute_branching
            arg_val = int(arg[1:], 16)
        elif arg[0] == '(' and arg[1] == '$' and arg[-1] == ')': 
            arg_val = int(arg[2:-1], 16)
            arg_addressing_mode = indirect_branching
    assert arg_val <= 0xFF
    return [(arg_addressing_mode.high_nibble << 4) + mne.low_nibble, arg_val]
