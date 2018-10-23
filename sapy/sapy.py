class ProgramCounter():
    def __init__(self):
        self.reset()

    def reset(self):
        self.counter = 0

    def clock(self, cp=False, **kwargs):
        """
        cp : bool
            Whether to increment program counter
        """
        if cp:
            self.counter += 1

    def data(self, ep=False, **kwargs):
        if ep:
            return self.counter
        else:
            return None

class MemoryAddressRegister():
    def __init__(self):
        self.reset()

    def reset(self):
        self._address = 0x0

    def data(self, **kwargs):
        # mar never outputs to the bus
        return None

    def clock(self, data=None, lm=False, **kwargs):
        if data > 0xF:
            raise ValueError("Address bus limited to 4 bit")
        if lm:
            assert not data is None
            self._address = data

    def address(self):
        return self._address

class RandomAccessMemory():
    def __init__(self, mar):
        self._mar = mar
        self.reset()

    def reset(self):
        self.values = {x: 0x00 for x in range(0xf + 1)} # 16 total values

    def clock(self, data=None,  lr=False, **kwargs):
        if lr:
            assert not data is None
            self.values[self._mar.address()] = data

    def data(self, er=False, **kwargs):
        if er:
            return self.values[self._mar.address()]
        else:
            return None

class SwitchBoard():
    def __init__(self, ram, mar):
        self._ram = ram
        self._mar = mar
        self.reset()

    def reset(self):
        self.address = 0x0
        self.data = 0x00

    def load_program(self, program):
        self.address = 0x0
        for opcode in program:
            self.data = opcode
            self.write_ram()
            self.address += 1

    def write_ram(self):
        # store address for ram in register
        self._mar.clock(data=self.address, lm=True)
        # clock data into ram at the address set above
        self._ram.clock(data=self.data, lr=True)

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

    def reset(self):
        self.value = 0x00

    def clock(self, data=None,  lo=False, **kwargs):
        if lo:
            assert not data is None
            assert 0x00 <= data <= 0xFF
            self.value = data
            print(f"Output: {self.value}")

    def data(self, **kwargs):
        return None

class ArithmeticUnit():
    def __init__(self, accumulator, reg_b):
        self.accumulator = accumulator
        self.reg_b = reg_b
        self.reset()

    def reset(self):
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

    def data(self, ei=False, **kwargs):
        if ei:
            # return self.value
            return self.value & 0x0F # low nibble is the argument that goes to the bus

    def opcode(self):
        return (self.value & 0xF0) >> 4 # high nibble is the opcode

class Clock():
    microcode = {
        1: {'ep': True, 'lm': True},
        2: {'cp': True},
        }

    def __init__(self):
        self.components = []

    def reset(self):
        for c in self.components:
            c.reset()

    def add_component(self, component):
        self.components.append(component)

    def data_bus(self, control_word):
        datas = []
        for c in self.components:
            d = c.data(**control_word)
            if not d is None:
                datas.append(d)
        print(datas)
        print(self.components)
        if len(datas) == 1:
            return datas[0]
        elif len(datas) == 0:
            return None
        elif len(datas) > 1:
            raise RuntimeError("More than one component outputting to the data bus")


    def step(self):
        control_word = self.microcode[self.t_state]
        data = self.data_bus(control_word)
        print(data)

        for c in self.components:
            c.clock(data=data, **control_word)
