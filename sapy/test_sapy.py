import pytest

from sapy import Clock, ProgramCounter, MemoryAddressRegister, RandomAccessMemory, SwitchBoard, RegisterA, RegisterB, RegisterOutput, ArithmeticUnit, RegisterInstruction

def test_program_counter_increments():
    pc = ProgramCounter()

    pc.clock()
    assert pc.data(ep=True) == 0x00

    pc.clock(cp=True)
    assert pc.data(ep=True) == 0x01

    pc.clock(cp=True)
    assert pc.data(ep=True) == 0x02

def test_program_counter_resets():
    pc = ProgramCounter()

    pc.clock(cp=True)
    assert pc.data(ep=True) == 0x01

    pc.reset()
    assert pc.data(ep=True) == 0x00

def test_program_counter_needs_ep():
    pc = ProgramCounter()

    pc.clock(cp=True)
    assert pc.data() == None

    pc.reset()
    assert pc.data() == None

def test_memory_address_register_latches_data_on_lm():
    mar = MemoryAddressRegister()

    assert mar.data() == None

    mar.clock(data=0xF, lm=True)
    assert mar.address() == 0xF

    mar.clock(data=0x3, lm=True)
    assert mar.address() == 0x3

    mar.clock(data=0xC, lm=False)
    assert mar.address() == 0x3


def test_ram_can_store_values():
    mar = MemoryAddressRegister()
    ram = RandomAccessMemory(mar)

    # store address for ram in register
    mar.clock(data=0xF, lm=True)
    assert mar.address() == 0xF

    # clock data into ram at the address set above
    ram.clock(data=0xAB, lr=True)
    assert ram.data() == None
    assert ram.data(er=True) == 0xAB

    # don't clock data into ram at the address set above
    ram.clock(data=0xAA)
    assert ram.data(er=True) == 0xAB

def test_addresses_must_be_4_bit():
    mar = MemoryAddressRegister()
    ram = RandomAccessMemory(mar)

    fourbitmax = 0xF

    # store address for ram in register
    mar.clock(data=fourbitmax, lm=True)
    assert mar.address() == fourbitmax

    with pytest.raises(ValueError):
        mar.clock(data=fourbitmax + 1, lm=True)


def test_switches_can_give_address_and_data():
    switches = SwitchBoard(ram=None, mar=None)
    assert switches.address == 0x0
    assert switches.data == 0x00

def test_switches_can_initialize_ram():
    program = [0xFA, 0x12]

    mar = MemoryAddressRegister()
    ram = RandomAccessMemory(mar)
    switches = SwitchBoard(ram, mar)

    switches.load_program(program)

    # set ram address
    mar.clock(data=0x0, lm=True)
    assert ram.data(er=True) == 0xFA
    mar.clock(data=0x1, lm=True)
    assert ram.data(er=True) == 0x12
    mar.clock(data=0x0, lm=True)
    assert ram.data(er=True) == 0xFA

def test_a_register_can_store_and_retrieve_values():
    reg_a = RegisterA()

    assert reg_a.data(ea=True) == 0x00
    reg_a.clock(data=0xAB, la=True)
    assert reg_a.value == 0xAB
    assert reg_a.data() == None
    assert reg_a.data(ea=True) == 0xAB

def test_b_register_can_store_and_not_retrieve():
    reg_b = RegisterB()

    # register_b cannot put data on the bus
    assert reg_b.data(eb=True) == None

    reg_b.clock(data=0xAB, lb=True)
    assert reg_b.value == 0xAB
    assert reg_b.data() == None

    # register_b cannot put data on the bus
    assert reg_b.data(eb=True) == None


def test_output_register_can_store_and_not_retrieve():
    reg_o = RegisterOutput()

    # register_o cannot put data on the bus
    assert reg_o.data(eo=True) == None

    reg_o.clock(data=0xAB, lo=True)
    assert reg_o.value == 0xAB
    assert reg_o.data() == None

    # register_o cannot put data on the bus
    assert reg_o.data(eo=True) == None

@pytest.mark.parametrize("a,b,expected", [
    (0x00, 0x00, 0x00),
    (0x03, 0x04, 0x07),
    (0xFF, 0x01, 0x00), # overflow
    ])
def test_arithmetic_unit_adds(a, b, expected):
    reg_a = RegisterA()
    reg_a.clock(data=a, la=True)

    reg_b = RegisterB()
    reg_b.clock(data=b, lb=True)

    adder = ArithmeticUnit(reg_a, reg_b)

    assert adder.data() is None
    assert adder.data(eu=True) == expected

@pytest.mark.parametrize("a,b,expected", [
    (0x04, 0x04, 0x00),
    (0x04, 0x03, 0x01),
    (0x00, 0x01, 0xFF), # underflow
    ])
def test_arithmetic_unit_subtracts(a, b, expected):
    reg_a = RegisterA()
    reg_a.clock(data=a, la=True)

    reg_b = RegisterB()
    reg_b.clock(data=b, lb=True)

    adder = ArithmeticUnit(reg_a, reg_b)

    assert adder.data() is None
    assert adder.data(eu=True, su=True) == expected

def test_instruction_register_splits_value():
    reg_i = RegisterInstruction()
    instruction = 0xCD # both opcode and argument, 8bits
    reg_i.clock(data=instruction, li=True)
    assert reg_i.value == instruction
    assert reg_i.opcode() == 0xC # opcode
    assert reg_i.data() == None
    assert reg_i.data(ei=True) == 0xD # address

def test_clock_add_component():
    clock = Clock()
    pc = ProgramCounter()
    clock.add_component(pc)

def test_clock_gets_data():
    # pull data from connected components from data bus
    clock = Clock()
    reg_a = RegisterA()
    clock.add_component(reg_a)

    reg_a.clock(data=0xCD, la=True)

    control_word = {'ea': True}

    assert clock.data_bus(control_word) == 0xCD

def test_clock_fails_if_multi_data_accessed():
    # pull data from connected components from data bus
    clock = Clock()
    reg_a = RegisterA()
    pc = ProgramCounter()
    clock.add_component(reg_a)
    clock.add_component(pc)

    reg_a.clock(data=0xCD, la=True)
    pc.clock(data=0xAE, ep=True)

    control_word = {'ea': True, 'ep':True}

    with pytest.raises(RuntimeError):
        clock.data_bus(control_word)

def test_clock_resets_components():
    class SpyComponent():
        def __init__(self):
            self.reset_called = False

        def reset(self):
            self.reset_called = True

    c = SpyComponent()
    clock = Clock()

    clock.add_component(c)

    clock.reset()
    assert c.reset_called

def test_t1_transfers_pc_to_mar():
    clock = Clock()
    pc = ProgramCounter()
    mar = MemoryAddressRegister()

    clock.add_component(pc)
    clock.add_component(mar)

    # reset CPU
    clock.reset()

    # contrive for test
    pc.counter = 0xC
    clock.t_state = 1

    # apply single clock cycle
    clock.step()

    assert mar.address() == 0xC

def test_t2_increments_pc():
    clock = Clock()
    pc = ProgramCounter()

    clock.add_component(pc)

    # reset CPU
    clock.reset()

    # contrive for test
    pc.counter = 0xC
    clock.t_state = 2

    # apply single clock cycle
    clock.step()

    assert pc.counter == 0xD

def test_t3_transfers_instruction_from_ram_to_instruction_register():
    clock = Clock()
    reg_i = RegisterInstruction()
    mar = MemoryAddressRegister()
    ram = RandomAccessMemory(mar)

    clock.add_component(mar)
    clock.add_component(ram)
    clock.add_component(reg_i)

    # reset CPU
    clock.reset()

    # contrive for test
    switches = SwitchBoard(ram, mar)
    program = [0xFA, 0x12]
    switches.load_program(program)
    mar.clock(data=0x1, lm=True) # get the second instruction next
    clock.t_state = 3

    # apply single clock cycle
    clock.step()

    assert reg_i.value == 0x12

def test_clock_can_single_step():
    clock = Clock()

    # reset CPU
    clock.reset()

    # contrive for test
    clock.t_state = 3

    # apply single clock cycle
    clock.step()
    assert clock.t_state == 4

def test_clock_can_instruction_step():
    clock = Clock()

    # reset CPU
    clock.reset()

    # contrive for test
    clock.t_state = 3

    # apply single clock cycle
    clock.step(instructionwise=True)
    assert clock.t_state == 1

def test_clock_has_correct_number_of_t_states():
    clock = Clock()

    # reset CPU
    clock.reset()

    # contrive for test
    clock.t_state = 3

    # apply single clock cycle
    clock.step()
    assert clock.t_state == 4
    clock.step()
    assert clock.t_state == 5
    clock.step()
    assert clock.t_state == 6
    clock.step()
    assert clock.t_state == 1

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

def test_opcode_lda():
    pc = Computer()
    program = [
        0x01, # 0x0 LDA 1H
        0xCC, # 0x1 CCH
        ]
    pc.switches.load_program(program)
    pc.step(instructionwise=True)
    assert pc.reg_a.value == 0xCC
