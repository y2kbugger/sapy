from typing import Tuple

import numpy as np # type: ignore

from dataclasses import dataclass

### Components ###
class Register():
    def __init__(self, name):
        self._name = name
        self.latch_bit = 'l' + name
        self.enable_bit = 'e' + name
        self.reset()

    def reset(self):
        self.value = 0x00

    def clock(self, *, data=None, con=[]):
        if self.latch_bit in con:
            assert not data is None
            if not (0x00 <= data <= 0xFF):
                raise ValueError("data bus is limited to 8 bits")
            self.value = data

    def data(self, con=[]):
        if self.enable_bit in con:
            return self.value

class RegisterA(Register):
    def __init__(self):
        super().__init__(name='a')

class RegisterB(Register):
    def __init__(self):
        super().__init__(name='b')

    def data(self, con=[]):
        """B Register does not output ever"""
        return None

class MemoryAddressRegister(Register):
    def __init__(self):
        super().__init__(name='m')

    def data(self, con=[]):
        """mar never outputs to the bus"""
        return None

class ProgramCounter(Register):
    def __init__(self):
        super().__init__(name='p')
        self.halted = False

    def clock(self, *, data=None, con=[]):
        """
        Control Bits
        ------------
        cp 
            Whether to increment program counter
        hp
            Halt the program counter
        """
        assert not (('cp' in con) and ('lp' in con)) # either increment or latch or neither
        if self.halted:
            return

        if 'cp' in con and not self.halted:
            self.value += 1
        elif 'lp' in con:
            self.value = data
        elif 'hp' in con:
            self.value -= 1 # move back to halt instuction
            self.halted = True

class RegisterOutput(Register):
    def __init__(self):
        super().__init__(name='o')
        self.output_function = lambda x: print(f"Output Display: {x:X}")

    def data(self, con=[]):
        return None

    def clock(self, *, data=None, con=[]):
        super().clock(data=data, con=con)
        if 'lo' in con:
            self.output_function(self.value)

class RandomAccessMemory():
    def __init__(self, mar):
        self._mar = mar
        self.reset()

    def reset(self):
        self.values = {x: 0x00 for x in range(0xFF + 1)} # 256 total values

    def clock(self, *, data=None, con=[]):
        if 'lr' in con:
            assert not data is None
            self.values[self._mar.value] = data

    def data(self, con=[]):
        if 'er' in con:
            return self.values[self._mar.value]
        else:
            return None

class ArithmeticUnit():
    def __init__(self, accumulator, reg_b):
        self.accumulator = accumulator
        self.reg_b = reg_b
        self.reset()

    def reset(self):
        pass

    def clock(self, *, data=None, con=[]):
        # ArithmeticUnit is static realtime
        pass

    def data(self, con=[]):
        if not 'eu' in con:
            return None

        if not 'su' in con:
            a = self.accumulator.value + self.reg_b.value
        elif 'su' in con:
            a =  self.accumulator.value - self.reg_b.value

        # Handel overflows
        base = 1 << 8 # eight bits
        return a % base

class RegisterInstruction(Register):
    def __init__(self):
        super().__init__(name='o')

    def clock(self, *, data=None, con=[]):
        if 'li' in con:
            assert not data is None
            assert 0x00 <= data <= 0xFF
            self.value = data

    def data(self, con=[]):
        return None

### Controller Parts ###
class SwitchBoard():
    def __init__(self, ram, mar):
        self._ram = ram
        self._mar = mar
        self.reset()

    def reset(self):
        self.address = 0x00
        self.data = 0x00

    def load_program(self, program):
        self.address = 0x00
        for opcode in program:
            self.data = opcode
            self.write_ram_location()
            self.address += 1

    def write_ram_location(self):
        # store address for ram in register
        self._mar.clock(data=self.address, con=['lm'])
        # clock data into ram at the address set above
        self._ram.clock(data=self.data, con=['lr'])

class DMAReader():
    def __init__(self, ram, mar):
        self._ram = ram
        self._mar = mar
        def handler(ram_array):
            print(ram_array)
        self.set_dma_handler = handler

    def reset(self):
        pass

    def read_ram(self):
        bitmap = np.zeros((0xF + 1, 0xF + 1))

        for address_high in range(0x0, 0xF + 1):
            for address_low in range(0x0, 0xF + 1):
                byte = self.read_ram_location(address_high, address_low)
                bitmap[address_high, address_low] = byte
        return bitmap

    def read_ram_location(self, address_high, address_low):
        address = (address_high << 4) + address_low
        self._mar.clock(data=address, con=['lm'])
        byte = self._ram.data(con=['er'])
        return byte

    def connect_dma_handler(self, handler):
        self._dma_handler = handler

    def clock(self, *, data=None, con=[]):
        if 'dma' in con:
            self._dma_handler(self.read_ram())

    def data(self, con=[]):
        return None

@dataclass
class AddressingMode:
    arg_fetch_microcode: Tuple[Tuple[str]]
    high_nibble: int

@dataclass
class Mnemonic:
    # do something with ram at the operand address, eg er to use, lr to save
    operation_microcode: Tuple[Tuple[str]]
    low_nibble: int
    addressing_modes: Tuple[AddressingMode]
    mnemonic: str

@dataclass
class OpCode:
    # Possible combinations of AddressingModes and Mnemonics
    mne: Mnemonic
    mode: AddressingMode

    def decode(self):
        return fetch_microcode \
            + self.mode.arg_fetch_microcode \
            + self.mne.operation_microcode

def generate_opcode_map(mnemonics):
    opcode_map = dict()
    for mne in mnemonics:
        for adm in mne.addressing_modes:
            opcode = (adm.high_nibble << 4) + mne.low_nibble
            opcode_map[opcode] = OpCode(mne, adm)
    return opcode_map

fetch_microcode = (
    ('ep', 'lm', 'cp'), # get next memory loc
    ('er', 'li'),       # put that opcode at that loc into instruction register 
    )

implied = AddressingMode(
    arg_fetch_microcode=tuple(),
    high_nibble=0xF,
    )

immediate = AddressingMode(
    arg_fetch_microcode=(
        ('ep', 'lm', 'cp'), # get next memory loc
        ),
    high_nibble=0x2,
    )

absolute = AddressingMode(
    arg_fetch_microcode=(
        ('ep', 'lm', 'cp'), # get next memory loc
        ('er', 'lm'),       # get operand address from next memory loc
        ),
    high_nibble=0x0,
    )

indirect = AddressingMode(
    arg_fetch_microcode=(
        ('ep', 'lm', 'cp'), # get next memory loc
        ('er', 'lm'),       # get operand address from next memory loc
        ('ep', 'lm'),       # get next memory loc
        ('er', 'lm'),       # get operand address from next memory loc
        ),
    high_nibble=0x1,
    )

absolute_branching = AddressingMode(
    arg_fetch_microcode=(
        ('ep', 'lm', 'cp'), # get next memory loc
        ),
    high_nibble=0x3,
    )

indirect_branching = AddressingMode(
    arg_fetch_microcode=(
        ('ep', 'lm', 'cp'), # get next memory loc
        ('er', 'lm'),       # get operand address from next memory loc
        ),
    high_nibble=0x4,
    )

# Mnemonics
LDA = Mnemonic(
    operation_microcode=(
        ('er', 'la'),
        ),
    low_nibble=0x0,
    addressing_modes=(immediate, absolute, indirect),
    mnemonic='LDA'
    )

ADD = Mnemonic(
    operation_microcode=(
        ('er', 'lb'),
        ('eu', 'la'),
        ),
    low_nibble=0x1,
    addressing_modes=(immediate, absolute, indirect),
    mnemonic='ADD'
    )

SUB = Mnemonic(
    operation_microcode=(
        ('er', 'lb'),
        ('eu', 'la', 'su'),
        ),
    low_nibble=0x2,
    addressing_modes=(immediate, absolute, indirect),
    mnemonic='SUB'
    )

OUT = Mnemonic(
    operation_microcode=(
        ('er', 'lo'),
        ),
    low_nibble=0x3,
    addressing_modes=(immediate, absolute, indirect),
    mnemonic='OUT'
    )

JMP = Mnemonic(
    operation_microcode=(
        ('er', 'lp'),
        ),
    low_nibble=0x4,
    addressing_modes=(absolute_branching, indirect_branching),
    mnemonic='JMP'
    )

STA = Mnemonic(
    operation_microcode=(
        ('er', 'lm'),
        ('ea', 'lr'),
        ),
    low_nibble=0x5,
    addressing_modes=(absolute_branching, indirect_branching),
    mnemonic='STA'
    )

# Output A register
OTA = Mnemonic(
    operation_microcode=(
        ('ea', 'lo'),
        ),
    low_nibble=0x6,
    addressing_modes=(implied,),
    mnemonic='OTA'
    )

# read Char (8bits) from input to the A register
BAI = Mnemonic(
    operation_microcode=(
        ('ec', 'lc'),
        ),
    low_nibble=0x7,
    addressing_modes=(implied,),
    mnemonic='BAI'
    )

DMA = Mnemonic(
    operation_microcode=(
        ('dma',),
        ),
    low_nibble=0xD,
    addressing_modes=(implied,),
    mnemonic='DMA'
    )

NOP = Mnemonic(
    operation_microcode=(
        tuple(),
        ),
    low_nibble=0xE,
    addressing_modes=(implied,),
    mnemonic='NOP'
    )

HLT = Mnemonic(
    operation_microcode=(
        ('hp',),
        ),
    low_nibble=0xF,
    addressing_modes=(implied,),
    mnemonic='HLT'
    )

mnemonics = [LDA, ADD, SUB, OUT, STA, JMP, HLT, NOP, DMA, OTA, BAI]
opcode_map = generate_opcode_map(mnemonics)

class Clock():
    def __init__(self, reg_i=None):
        self.reg_i = reg_i
        self.components = []
        self.reset()

    def reset(self):
        self.t_state = 0
        self.microcode = fetch_microcode

        for c in self.components:
            c.reset()

    def add_component(self, component):
        self.components.append(component)

    def data_bus(self, control_word):
        datas = []
        for c in self.components:
            d = c.data(control_word)
            # print(c, d)
            if not d is None:
                datas.append(d)

        if len(datas) == 1:
            return datas[0]
        elif len(datas) == 0:
            return None
        elif len(datas) > 1:
            raise RuntimeError("More than one component outputting to the data bus")

    def step(self, instructionwise=False, debug=True):
        try:
            control_word = self.microcode[self.t_state]
        except IndexError:
            self.t_state = 0
            self.microcode = fetch_microcode
            if instructionwise:
                return
            control_word = self.microcode[self.t_state]

        data = self.data_bus(control_word)
        if debug:
            if self.t_state == 0:
                print('-' * 42)
                print(f"PCADDRESS: ${data:02X}")
            if data is not None:
                print(f"T{self.t_state}: Data: ${data:02X}, Control Word: {control_word}")
            else:
                print(f"T{self.t_state}: Data: None, Control Word: {control_word}")

        for c in self.components:
            c.clock(data=data, con=control_word)

        if self.t_state == 1 and self.reg_i is not None:
            self.decode(self.reg_i.value)
            if debug:
                print(f"OPCODE: ${self.reg_i.value:02X}, MNE: {opcode_map[self.reg_i.value].mne.mnemonic}")

        self.t_state += 1

        # run until back to 0
        if instructionwise:
            self.step(instructionwise=True, debug=debug)

    def decode(self, opcode):
        try:
            new_microcode = opcode_map[opcode].decode()
        except AttributeError:
            print("No reg_i attached")
            new_microcode = opcode_map[0xFE].decode()
        except KeyError:
            print("Trying to execute a non-existant opcode")
            new_microcode = opcode_map[0xFE].decode()
        self.microcode = new_microcode

class Computer():
    def __init__(self):
        self.pc = ProgramCounter()
        self.mar = MemoryAddressRegister()
        self.ram = RandomAccessMemory(self.mar)

        self.reg_a = RegisterA()
        self.reg_b = RegisterB()
        self.adder = ArithmeticUnit(self.reg_a, self.reg_b)

        self.reg_o = RegisterOutput()
        self.reg_i = RegisterInstruction()

        self.switches = SwitchBoard(self.ram, self.mar)
        self.dma = DMAReader(self.ram, self.mar)

        clock = Clock(self.reg_i)
        self._clock = clock

        clock.add_component(self.pc)
        clock.add_component(self.mar)
        clock.add_component(self.ram)
        clock.add_component(self.reg_i)
        clock.add_component(self.reg_a)
        clock.add_component(self.reg_b)
        clock.add_component(self.reg_o)
        clock.add_component(self.adder)
        clock.add_component(self.dma)

        # reset CPU
        clock.reset()

    def reset(self):
        self._clock.reset()

    def step(self, *args, **kwargs):
        self._clock.step(*args, **kwargs)

