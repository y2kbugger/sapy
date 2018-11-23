import pytest # type: ignore

from .sapy import Register, Clock, ProgramCounter, MemoryAddressRegister, RandomAccessMemory, SwitchBoard, RegisterA, RegisterB, RegisterOutput, ArithmeticUnit, RegisterInstruction, Computer

def test_program_counter_increments():
    pc = ProgramCounter()

    pc.clock()
    assert pc.data(['ep']) == 0x00

    pc.clock(con=['cp'])
    assert pc.data(['ep']) == 0x01

    pc.clock(con=['cp'])
    assert pc.data(['ep']) == 0x02

def test_program_counter_latches():
    pc = ProgramCounter()

    pc.clock()

    pc.clock(data=0x0D, con=['lp'])
    assert pc.data(['ep']) == 0x0D

    pc.clock(con=['cp'])
    assert pc.data(['ep']) == 0x0E

def test_program_counter_resets():
    pc = ProgramCounter()

    pc.clock(con=['cp'])
    assert pc.data(['ep']) == 0x01

    pc.reset()
    assert pc.data(['ep']) == 0x00

def test_program_counter_needs_ep():
    pc = ProgramCounter()

    pc.clock(con=['cp'])
    assert pc.data() == None

    pc.reset()
    assert pc.data() == None

def test_memory_address_register_latches_data_on_lm():
    mar = MemoryAddressRegister()

    assert mar.data() == None

    mar.clock(data=0x0F, con=['lm'])
    assert mar.value == 0x0F

    mar.clock(data=0x03, con=['lm'])
    assert mar.value == 0x03

    mar.clock(data=0x0C, con=[])
    assert mar.value == 0x03


def test_ram_can_store_values():
    mar = MemoryAddressRegister()
    ram = RandomAccessMemory(mar)

    # store address for ram in register
    mar.clock(data=0x0F, con=['lm'])
    assert mar.value == 0x0F

    # clock data into ram at the address set above
    ram.clock(data=0xAB, con=['lr'])
    assert ram.data() == None
    assert ram.data(['er']) == 0xAB

    # don't clock data into ram at the address set above
    ram.clock(data=0xAA)
    assert ram.data(['er']) == 0xAB

def test_addresses_must_be_8_bit():
    mar = MemoryAddressRegister()
    ram = RandomAccessMemory(mar)

    bitmax = 0xFF

    # store address for ram in register
    mar.clock(data=bitmax, con=['lm'])
    assert mar.value == bitmax

    with pytest.raises(ValueError):
        mar.clock(data=bitmax + 1, con=['lm'])


def test_switches_can_give_address_and_data():
    switches = SwitchBoard(ram=None, mar=None)
    assert switches.address == 0x00
    assert switches.data == 0x00

def test_switches_can_initialize_ram():
    program = [0xFA, 0x12]

    mar = MemoryAddressRegister()
    ram = RandomAccessMemory(mar)
    switches = SwitchBoard(ram, mar)

    switches.load_program(program)

    # set ram address
    mar.clock(data=0x00, con=['lm'])
    assert ram.data(['er']) == 0xFA
    mar.clock(data=0x01, con=['lm'])
    assert ram.data(['er']) == 0x12
    mar.clock(data=0x00, con=['lm'])
    assert ram.data(['er']) == 0xFA

def test_a_register_can_store_and_retrieve_values():
    reg_a = RegisterA()

    assert reg_a.data(['ea']) == 0x00
    reg_a.clock(data=0xAB, con=['la'])
    assert reg_a.value == 0xAB
    assert reg_a.data() == None
    assert reg_a.data(['ea']) == 0xAB

def test_b_register_can_store_and_not_retrieve():
    reg_b = RegisterB()

    # register_b cannot put data on the bus
    assert reg_b.data(['eb']) == None

    reg_b.clock(data=0xAB, con=['lb'])
    assert reg_b.value == 0xAB
    assert reg_b.data() == None

    # register_b cannot put data on the bus
    assert reg_b.data(['eb']) == None


def test_output_register_can_store_and_not_retrieve():
    reg_o = RegisterOutput()

    # register_o cannot put data on the bus
    assert reg_o.data(['eo']) == None

    reg_o.clock(data=0xAB, con=['lo'])
    assert reg_o.value == 0xAB
    assert reg_o.data() == None

    # register_o cannot put data on the bus
    assert reg_o.data(['eo']) == None

@pytest.mark.parametrize("a,b,expected", [
    (0x00, 0x00, 0x00),
    (0x03, 0x04, 0x07),
    (0xFF, 0x01, 0x00), # overflow
    ])
def test_arithmetic_unit_adds(a, b, expected):
    reg_a = RegisterA()
    reg_a.clock(data=a, con=['la'])

    reg_b = RegisterB()
    reg_b.clock(data=b, con=['lb'])

    adder = ArithmeticUnit(reg_a, reg_b)

    assert adder.data() is None
    assert adder.data(['eu']) == expected

@pytest.mark.parametrize("a,b,expected", [
    (0x04, 0x04, 0x00),
    (0x04, 0x03, 0x01),
    (0x00, 0x01, 0xFF), # underflow
    ])
def test_arithmetic_unit_subtracts(a, b, expected):
    reg_a = RegisterA()
    reg_a.clock(data=a, con=['la'])

    reg_b = RegisterB()
    reg_b.clock(data=b, con=['lb'])

    adder = ArithmeticUnit(reg_a, reg_b)

    assert adder.data() is None
    assert adder.data(['eu', 'su']) == expected

def test_instruction_register_doesnt_split_value():
    reg_i = RegisterInstruction()
    instruction = 0xCD # both 8bit opcode
    reg_i.clock(data=instruction, con=['li'])
    assert reg_i.value == instruction
    assert reg_i.data() == None
    assert reg_i.data(['ei']) == None

def test_clock_add_component():
    clock = Clock()
    pc = ProgramCounter()
    clock.add_component(pc)

def test_clock_gets_data():
    # pull data from connected components from data bus
    clock = Clock()
    reg_a = RegisterA()
    clock.add_component(reg_a)

    reg_a.clock(data=0xCD, con=['la'])

    control_word = ['ea']

    assert clock.data_bus(control_word) == 0xCD

def test_clock_fails_if_multi_data_accessed():
    # pull data from connected components from data bus
    clock = Clock()
    reg_a = RegisterA()
    pc = ProgramCounter()
    clock.add_component(reg_a)
    clock.add_component(pc)

    reg_a.clock(data=0xCD, con=['la'])
    pc.clock(data=0xAE, con=['ep'])

    control_word = ['ea', 'ep']

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
    pc.clock(data=0x0C, con=['lp'])
    clock.t_state = 1

    # apply single clock cycle
    clock.step()

    assert mar.value == 0x0C

def test_t2_increments_pc():
    clock = Clock()
    pc = ProgramCounter()

    clock.add_component(pc)

    # reset CPU
    clock.reset()

    # contrive for test
    pc.clock(data=0x0C, con=['lp'])
    clock.t_state = 2

    # apply single clock cycle
    clock.step()

    assert pc.value == 0x0D

def test_t3_transfers_instruction_from_ram_to_instruction_register():
    reg_i = RegisterInstruction()
    clock = Clock(reg_i)
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
    mar.clock(data=0x01, con=['lm']) # get the second instruction next
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
    assert clock.t_state == 7
    clock.step()
    assert clock.t_state == 1

def test_opcode_lda():
    pc = Computer()
    program = [
        0x00, 0x02, # 0x00 LDA 02H
        0xCC,       # 0x02 CCH
        ]
    pc.switches.load_program(program)
    pc.step(instructionwise=True, debug=True)
    assert pc.reg_a.value == 0xCC

def test_opcode_add():
    pc = Computer()
    program = [
        0x01, 0x02, # 0x00 ADD 02H
        0x22,       # 0x02 22H
        ]
    pc.switches.load_program(program)
    pc.reg_a.value = 0xCC
    pc.step(instructionwise=True)
    assert pc.reg_a.value == 0xEE

def test_opcode_sub():
    pc = Computer()
    program = [
        0x02, 0x02, # 0x00 SUB 02H
        0x22,       # 0x02 22H
        ]
    pc.switches.load_program(program)
    pc.reg_a.value = 0xCC
    pc.step(instructionwise=True)
    assert pc.reg_a.value == 0xAA

def test_opcode_out():
    pc = Computer()
    program = [
        0x03, # 0x00 OUT
        ]
    pc.switches.load_program(program)
    pc.reg_a.value = 0xF8
    pc.step(instructionwise=True)
    assert pc.reg_o.value == 0xF8

def test_opcode_program_sequence():
    pc = Computer()
    program = [
        0x00, 0x06, # 0x00 LDA 06H
        0x01, 0x07, # 0x02 ADD 07H
        0x03,       # 0x04 OUT
        0xFF,       # 0x05 HLT
        0xA1,       # 0x06 A1H
        0x22,       # 0x07 22H
        ]
    pc.switches.load_program(program)
    pc.step(instructionwise=True)
    pc.step(instructionwise=True)
    pc.step(instructionwise=True)
    pc.step(instructionwise=True)
    pc.step(instructionwise=True)
    assert pc.reg_o.value == 0xC3

def test_opcode_jmp():
    pc = Computer()
    program = [
        0x00, 0x07, # 0x00 LDA 07H
        0x01, 0x08, # 0x20 ADD 08H
        0x03,       # 0x04 OUT
        0x04, 0x02, # 0x05 JMP 02H
        0x00,       # 0x07 A1H
        0x03,       # 0x08 22H
        ]
    pc.switches.load_program(program)
    pc.step(instructionwise=True)
    pc.step(instructionwise=True)
    pc.step(instructionwise=True)
    assert pc.reg_o.value == 0x03
    pc.step(instructionwise=True)

    pc.step(instructionwise=True)
    pc.step(instructionwise=True)
    assert pc.reg_o.value == 0x06
    pc.step(instructionwise=True)

    pc.step(instructionwise=True)
    pc.step(instructionwise=True)
    assert pc.reg_o.value == 0x09
    pc.step(instructionwise=True)

def test_opcode_sta():
    pc = Computer()
    program = [
        0x00, 0x09, # 0x00 LDA 09H
        0x01, 0x0A, # 0x20 ADD 0AH
        0x03,       # 0x04 OUT
        0x05, 0x0A,  # 0x05 STA 0AH
        0x04, 0x02, # 0x07 JMP 02H
        0x00,       # 0x09 A1H
        0x02,       # 0x0A 22H
        ]
    pc.switches.load_program(program)
    pc.step(instructionwise=True)
    pc.step(instructionwise=True)
    pc.step(instructionwise=True)
    pc.step(instructionwise=True)
    assert pc.reg_o.value == 0x02
    pc.step(instructionwise=True)

    pc.step(instructionwise=True)
    pc.step(instructionwise=True)
    pc.step(instructionwise=True)
    assert pc.reg_o.value == 0x04
    pc.step(instructionwise=True)

    pc.step(instructionwise=True)
    pc.step(instructionwise=True)
    pc.step(instructionwise=True)
    assert pc.reg_o.value == 0x08
    pc.step(instructionwise=True)

    pc.step(instructionwise=True)
    pc.step(instructionwise=True)
    pc.step(instructionwise=True)
    assert pc.reg_o.value == 0x10
    pc.step(instructionwise=True)

    pc.step(instructionwise=True)
    pc.step(instructionwise=True)
    pc.step(instructionwise=True)
    assert pc.reg_o.value == 0x20
    pc.step(instructionwise=True)

