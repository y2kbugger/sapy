from typing import List, Dict

from sapy.components import opcode_map, mnemonics, implied, absolute, absolute_branching, indirect, indirect_branching, immediate


MNEMONIC = {m.mnemonic:m for m in mnemonics}

def assemble(assembly_text):
    instructions, labels = preprocess(assembly_text)
    bytecode = translate_instructions(instructions, labels)
    return bytecode

def translate_instructions(instructions, labels):
    bytecode = []
    byte_location = 0x00
    for i in instructions:
        try:
            labelname = ':' + labels[byte_location]
        except KeyError:
            # no label
            labelname = ""

        new_bytes = translate_instruction(i)
        bytecode.extend(new_bytes)
        hexdump = ' '.join([f"{new_byte:02X}" for new_byte in new_bytes])

        print(f"0x{byte_location:02X}  {hexdump:8}# {i:10}{labelname}")
        byte_location += len(new_bytes)

    return bytecode

def translate_instruction(instruction):

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

        if mne_chars == 'BYTE':
            assert arg[0] == '#', "BYTES must follow this syntax: \"BYTES #09 33 FA ...\""
            arg = arg[1:]
            arg_list = [int(byte, 16) for byte in arg.split()]
            return arg_list

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
    labels_lookup = dict() # reverse dict for retrieving the original label

    byte_location = 0x00
    for line in assembly_text.split('\n'):
        line = line.strip()

        # blank lines
        if line == '':
            continue

        # remove comments
        if line[0] == ';':
            # full line comment
            continue
        else:
            line = line.split(';', 1)[0]
            line = line.strip()

        # label definition
        if len(line.split()) == 1 and line[-1] == ':':
            labels[line[:-1]] = byte_location # all but last char
            labels_lookup[byte_location] = line[:-1] # The reverse dict
            continue

        try:
            byte_location += len(translate_instruction(line))
        except RuntimeError:
            byte_location += 2 # assume we are dealing with a 2 byte instruction, e.g. an unsubstituted label


        instructions.append(line)

    label_subbed_instructions = []
    for i in instructions:
        for label, label_location in labels.items():
            i = i.replace(label, f"${label_location:02X}")
        label_subbed_instructions.append(i)
    return label_subbed_instructions, labels_lookup
