from typing import List

MNEMONIC = {
    'LDA': 0x00,
    'ADD': 0x01,
    'SUB': 0x02,
    'OUT': 0x03,
    'JMP': 0x04,
    'HLT': 0xFF,
    }

def assemble(instructions) -> List[int]:
    bytecode = []
    for i in instructions:
        bytecode.extend(translate_instruction(i))
    return bytecode

def translate_instruction(instruction: str) -> List[int]:
    if ' ' in instruction:
        mne, arg = instruction.split(' ', 1)
    else:
        mne = instruction.split(' ', 1)[0]
    return [MNEMONIC[mne]]
