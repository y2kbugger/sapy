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

    def clock(self, *, data=None, con=[]):
        """
        Control Bits
        ------------
        cp 
            Whether to increment program counter
        """
        assert not (('cp' in con) and ('lp' in con)) # either increment or latch or neither
        if 'cp' in con:
            self.value += 1
        elif 'lp' in con:
            self.value = data

class RegisterOutput(Register):
    def __init__(self):
        super().__init__(name='o')
        self.output_function = lambda x: print(f"Output Display: {x:X}")

    def output_function(value):
        print(f"Output: {value}")

    def data(self, con=[]):
        return None

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
            self.write_ram()
            self.address += 1

    def write_ram(self):
        # store address for ram in register
        self._mar.clock(data=self.address, con=['lm'])
        # clock data into ram at the address set above
        self._ram.clock(data=self.data, con=['lr'])

class Clock():
    LDA = {
        4: ['ep', 'lm', 'cp'],
        5: ['er', 'lm'],
        6: ['er', 'la'],
        7: [],
        }
    ADD = {
        4: ['ep', 'lm', 'cp'],
        5: ['er', 'lm'],
        6: ['er', 'lb'],
        7: ['eu', 'la'],
        }
    SUB = {
        4: ['ep', 'lm', 'cp'],
        5: ['er', 'lm'],
        6: ['er', 'lb'],
        7: ['eu', 'la', 'su'],
        }
    OUT = {
        4: ['ea', 'lo'],
        5: [],
        6: [],
        7: [],
        }
    JMP = {
        4: ['ep', 'lm', 'cp'],
        5: ['er', 'lp'],
        6: [],
        7: [],
        }
    HLT = {
        1: [],
        2: [],
        3: [],
        4: [],
        5: [],
        6: [],
        7: [],
        }
    opcode_microcode = {
        0x00: LDA,
        0x01: ADD,
        0x02: SUB,
        0x03: OUT,
        0x04: JMP,
        0xFF: HLT,
        }

    def __init__(self, reg_i=None):
        self.reg_i = reg_i
        self.components = []
        self.reset()

    def reset(self):
        self.t_state = 1
        self.microcode = {
            1: {'ep': True, 'lm': True},
            2: {'cp': True},
            3: {'er': True, 'li': True},
            4: {},
            5: {},
            6: {},
            7: {},
            }

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

    def step(self, instructionwise=False, debug=False):
        control_word = self.microcode[self.t_state]
        data = self.data_bus(control_word)
        if debug:
            if self.t_state == 1:
                print('-' * 42)
            print(f"T{self.t_state}: Data: {data}, Control Word: {control_word}")

        for c in self.components:
            c.clock(data=data, con=control_word)

        if self.t_state == 3:
            self.decode()

        self.t_state += 1
        if self.t_state > 7:
            self.t_state = 1

        # run until back to 1
        if instructionwise and self.t_state != 1:
            self.step(instructionwise=True, debug=debug)

    def decode(self):
        try:
            new_microcode = self.opcode_microcode[self.reg_i.value]
            self.microcode.update(new_microcode)
        except AttributeError:
            print("No reg_i attached")
        except KeyError:
            print("Trying to execute a non-existant opcode")


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

        # reset CPU
        clock.reset()

    def reset(self):
        self._clock.reset()

    def step(self, *args, **kwargs):
        self._clock.step(*args, **kwargs)

