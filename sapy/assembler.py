from typing import List, Dict

from sapy.components import opcode_map, mnemonics, implied, absolute, absolute_branching, indirect, indirect_branching, immediate


MNEMONIC = {m.mnemonic:m for m in mnemonics}

def assemble(assembly_text):
    instructions, labels = preprocess(assembly_text)
    bytecode = translate_instructions(instructions)
    return bytecode

def translate_instructions(instructions):
    bytecode = []
    for i in instructions:
        bytecode.extend(translate_instruction(i))
    return bytecode

def translate_instruction(instruction, labels=None):
    if labels is None:
        labels = dict()

    # split on one or more whitespace chars
    split_instruction = instruction.split(None, 1)

    if len(split_instruction) == 1:
        # no arguments
        arg_addressing_mode = implied
        mne = MNEMONIC[instruction]
        arg_list = []
    else:
        # must handle argument
        mne_chars, arg = split_instruction
        mne = MNEMONIC[mne_chars]
        print(mne)

        # Should be one or the other
        # This could only go wrong with misconfigured mnemonics
        ads = mne.addressing_modes
        assert not ((indirect in ads) and (indirect_branching in ads))
        assert not ((absolute in ads) and (indirect_branching in ads))
        assert not ((absolute_branching in ads) and (indirect in ads))
        assert not ((absolute_branching in ads) and (absolute in ads))

        data_addressing_modes = [immediate, absolute, indirect]
        branching_addressing_modes = [absolute_branching, indirect_branching]

        is_data_add_mode = any(ad in data_addressing_modes for ad in ads)
        is_branching_add_mode = any(ad in branching_addressing_modes for ad in ads)

        if is_data_add_mode and arg[0] == '$':
                arg_addressing_mode = absolute
                arg_list = [int(arg[1:], 16)]
        elif is_data_add_mode and arg[0] == '#' and arg[1] == '$':
                arg_list = [int(arg[2:], 16)]
                arg_addressing_mode = immediate
        elif is_data_add_mode and arg[0] == '(' and arg[1] == '$' and arg[-1] == ')':
                arg_list = [int(arg[2:-1], 16)]
                arg_addressing_mode = indirect
        elif is_branching_add_mode and arg[0] == '$':
            arg_addressing_mode = absolute_branching
            arg_list = [int(arg[1:], 16)]
        elif is_branching_add_mode and arg[0] == '(' and arg[1] == '$' and arg[-1] == ')':
            arg_list = [int(arg[2:-1], 16)]
            arg_addressing_mode = indirect_branching
        else:
            raise RuntimeError(f"Could not understand argument \"{arg}\"")
    assert all(arg_val <= 0xFF for arg_val in arg_list)
    return [(arg_addressing_mode.high_nibble << 4) + mne.low_nibble] + arg_list

def preprocess(assembly_text):
    instructions = []
    labels = dict()

    for line in assembly_text.split('\n'):
        if line.strip() == '':
            continue
        # remove comments
        line = line.split(';', 1)[0]

        instructions.append(line.strip())

    return instructions, labels
