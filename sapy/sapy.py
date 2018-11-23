### Components ###

class ProgramCounter():
    def __init__(self):
        self.reset()

    def reset(self):
        self.counter = 0

    def clock(self, data=None, cp=False, lp=False, **kwargs):
        """
        cp : bool
            Whether to increment program counter
        """
        assert not (cp and lp) # either latch or increment
        if cp:
            self.counter += 1
        elif lp:
            self.counter = data

    def data(self, ep=False, **kwargs):
        if ep:
            return self.counter
        else:
            return None

class MemoryAddressRegister():
    def __init__(self):
        self.reset()

    def reset(self):
        self._address = 0x00

    def data(self, **kwargs):
        # mar never outputs to the bus
        return None

    def clock(self, data=None, lm=False, **kwargs):
        if lm:
            assert not data is None
            if data > 0xFF:
                raise ValueError("Address bus limited to 8 bit")
            self._address = data

    def address(self):
        return self._address

class RandomAccessMemory():
    def __init__(self, mar):
        self._mar = mar
        self.reset()

    def reset(self):
        self.values = {x: 0x00 for x in range(0xFF + 1)} # 256 total values

    def clock(self, data=None,  lr=False, **kwargs):
        if lr:
            assert not data is None
            self.values[self._mar.address()] = data

    def data(self, er=False, **kwargs):
        if er:
            return self.values[self._mar.address()]
        else:
            return None

class RegisterA():
    def __init__(self):
        self.reset()

    def reset(self):
        self.value = 0x00

    def clock(self, data=None,  la=False, **kwargs):
        if la:
            assert not data is None
            assert 0x00 <= data <= 0xFF
            self.value = data

    def data(self, ea=False, **kwargs):
        if ea:
            return self.value

class RegisterB():
    def __init__(self):
        self.reset()

    def reset(self):
        self.value = 0x00

    def clock(self, data=None,  lb=False, **kwargs):
        if lb:
            assert not data is None
            assert 0x00 <= data <= 0xFF
            self.value = data

    def data(self, **kwargs):
        return None

class RegisterOutput():
    def __init__(self):
        self.reset()
        self.output_function = lambda x: print(f"Output Display: {x:X}")

    def reset(self):
        self.value = 0x00

    def clock(self, data=None,  lo=False, **kwargs):
        if lo:
            assert not data is None
            assert 0x00 <= data <= 0xFF
            self.value = data
            self.output_function(self.value)


    def data(self, **kwargs):
        return None

class ArithmeticUnit():
    def __init__(self, accumulator, reg_b):
        self.accumulator = accumulator
        self.reg_b = reg_b
        self.reset()

    def reset(self):
        pass

    def clock(self, **kwargs):
        # ArithmeticUnit is static realtime
        pass

    def data(self, eu=False, su=False, **kwargs):
        if not eu:
            return None

        if not su:
            a = self.accumulator.value + self.reg_b.value
        elif su:
            a =  self.accumulator.value - self.reg_b.value

        # Handel overflows
        base = 1 << 8 # eight bits
        return a % base

class RegisterInstruction():
    def __init__(self):
        self.reset()

    def reset(self):
        self.value = 0x00

    def clock(self, data=None,  li=False, **kwargs):
        if li:
            assert not data is None
            assert 0x00 <= data <= 0xFF
            self.value = data

    def data(self, **kwargs):
        return None

    def opcode(self):
        return self.value


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
        self._mar.clock(data=self.address, lm=True)
        # clock data into ram at the address set above
        self._ram.clock(data=self.data, lr=True)

class Clock():
    LDA = {
        4: {'ep': True, 'lm': True, 'cp': True},
        5: {'er': True, 'lm': True},
        6: {'er': True, 'la': True},
        7: {},
        }
    ADD = {
        4: {'ep': True, 'lm': True, 'cp': True},
        5: {'er': True, 'lm': True},
        6: {'er': True, 'lb': True},
        7: {'eu': True, 'la': True},
        }
    SUB = {
        4: {'ep': True, 'lm': True, 'cp': True},
        5: {'er': True, 'lm': True},
        6: {'er': True, 'lb': True},
        7: {'eu': True, 'la': True, 'su': True},
        }
    OUT = {
        4: {'ea': True, 'lo': True},
        5: {},
        6: {},
        7: {},
        }
    JMP = {
        4: {'ep': True, 'lm': True, 'cp': True},
        5: {'er': True, 'lp': True},
        6: {},
        7: {},
        }
    HLT = {
        1: {},
        2: {},
        3: {},
        4: {},
        5: {},
        6: {},
        7: {},
        }
    opcode_microcode = {
        0x00: LDA,
        0x01: ADD,
        0x02: SUB,
        0x03: OUT,
        0x04: JMP,
        0xFF: HLT,
        }

    def __init__(self):
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

    def connect_opcode(self, opcode_function):
        """Connect a function that returns the current opcode"""
        self.opcode = opcode_function

    def data_bus(self, control_word):
        datas = []
        for c in self.components:
            d = c.data(**control_word)
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
            c.clock(data=data, **control_word)

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
            self.microcode.update(self.opcode_microcode[self.opcode()])
        except AttributeError:
            print("No opcode function for decoding instruction attached")


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

        clock = Clock()
        self._clock = clock

        clock.add_component(self.pc)
        clock.add_component(self.mar)
        clock.add_component(self.ram)
        clock.add_component(self.reg_i)
        clock.add_component(self.reg_a)
        clock.add_component(self.reg_b)
        clock.add_component(self.reg_o)
        clock.add_component(self.adder)

        clock.connect_opcode(self.reg_i.opcode)

        # reset CPU
        clock.reset()

    def reset(self):
        self._clock.reset()

    def step(self, *args, **kwargs):
        self._clock.step(*args, **kwargs)

