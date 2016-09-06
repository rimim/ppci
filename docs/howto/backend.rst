
How to write a new backend
--------------------------

This section describes how to add a new backend. The best thing to do is
to take a look at existing backends, like the backends for ARM and X86_64.

A backend consists of the following parts:

#. register descriptions
#. instruction descriptions
#. template descriptions
#. architecture description


Register description
~~~~~~~~~~~~~~~~~~~~

A backend must describe what kinds of registers are available. To do this
define for each register class a subclass of :class:`ppci.arch.isa.Register`.

There may be several register classes, for example 8-bit and 32-bit registers.
It is also possible that these classes overlap.

.. testcode::

    from ppci.arch.encoding import Register

    class X86Register(Register):
        bitsize=32

    class LowX86Register(Register):
        bitsize=8

    AL = LowX86Register('al', num=0)
    AH = LowX86Register('ah', num=4)
    EAX = X86Register('eax', num=0, aliases=(AL, AH))


Tokens
~~~~~~

Tokens are the basic blocks of complete instructions. They correspond to
byte sequences of parts of instructions. Good examples are the opcode token
of typically one byte, the prefix token and the immediate tokens which
optionally follow an opcode. Typically RISC machines will have instructions
with one token, and CISC machines will have instructions consisting of
multiple tokens.

To define a token, subclass the :class:`ppci.arch.token.Token` and optionally
add bitfields:

.. testcode:: encoding

    from ppci.arch.token import Token, bit_range

    class Stm8Token(Token):
        def __init__(self):
            super().__init__(8, '>B')

        opcode = bit_range(0, 8)

In this example an 8-bit token is defined with one field called 'opcode' of
8 bits.


Instruction description
~~~~~~~~~~~~~~~~~~~~~~~

An important part of the backend is the definition of instructions. Every
instruction for a specific machine derives from
:class:`ppci.arch.encoding.Instruction`.


Lets take the nop example of stm8. This instruction can be defined like this:

.. testcode:: encoding

    from ppci.arch.encoding import Instruction, Syntax, FixedPattern

    class Nop(Instruction):
        syntax = Syntax(['nop'])
        tokens = [Stm8Token]
        patterns = [FixedPattern('opcode', 0x9d)]


Here the nop instruction is defined. It has a syntax of 'nop'.
The syntax is used for creating a nice string
representation of the object, but also during parsing of assembly code.
The tokens contains a list of what tokens this instruction contains.

The patterns attribute contains a list of patterns. In this case
the opcode field is set with the fixed pattern 0x9d.

Instructions are also usable directly, like this:

.. doctest:: encoding

    >>> ins = Nop()
    >>> ins
    nop
    >>> type(ins)
    <class 'Nop'>
    >>> ins.encode()
    b'\x9d'

Often, an instruction does not have a fixed syntax. Often an argument
can be specified, for example the stm8 adc instruction:

.. testcode:: encoding

    from ppci.arch.encoding import register_argument, VariablePattern

    class Stm8ByteToken(Token):
        def __init__(self):
            super().__init__(8, '>B')

        byte = bit_range(0, 8)

    class AdcByte(Instruction):
        imm = register_argument('imm', int)
        syntax = Syntax(['adc', ' ', 'a', ',', ' ', imm])
        tokens = [Stm8Token, Stm8ByteToken]
        patterns = [
            FixedPattern('opcode', 0xa9),
            VariablePattern('byte', imm)]

The 'imm' attribute now functions as a variable instruction part. When
constructing the instruction, it must be given:

.. doctest:: encoding

    >>> ins = AdcByte(0x23)
    >>> ins
    adc a, 35
    >>> type(ins)
    <class 'AdcByte'>
    >>> ins.encode()
    b'\xa9#'
    >>> ins.imm
    35

As a benefit of specifying syntax and patterns, the default decode classmethod
can be used to create an instruction from bytes:

.. doctest:: encoding

    >>> ins = AdcByte.decode(bytes([0xa9,0x10]))
    >>> ins
    adc a, 16

Another option of constructing instruction classes is adding different
instruction classes to eachother:

.. testcode:: encoding

    from ppci.arch.encoding import register_argument, VariablePattern

    class Sbc(Instruction):
        syntax = Syntax(['sbc', ' ', 'a'])
        tokens = [Stm8Token]
        patterns = [FixedPattern('opcode', 0xa2)]

    class Byte(Instruction):
        imm = register_argument('imm', int)
        syntax = Syntax([',', ' ', imm])
        tokens = [Stm8ByteToken]
        patterns = [VariablePattern('byte', imm)]

    SbcByte = Sbc + Byte


In the above example, two instruction classes are defined. When combined,
the tokens, syntax and patterns are combined into the last instruction.

.. doctest:: encoding

    >>> ins = SbcByte.decode(bytes([0xa2,0x10]))
    >>> ins
    sbc a, 16
    >>> type(ins)
    <class 'ppci.arch.encoding.SbcByte'>

Instruction groups
~~~~~~~~~~~~~~~~~~

Instructions often not come alone. They are usually grouped into a set of
instructions, or an instruction set architecture (ISA). An isa can be
created and instructions can be added to it, like this:


.. testcode:: encoding

    from ppci.arch.isa import Isa
    my_isa = Isa()
    my_isa.add_instruction(Nop)


The instructions of an isa can be inspected:

.. doctest:: encoding

    >>> my_isa.instructions
    [<class 'Nop'>]

Instead of adding each instruction manually to an isa, one can also specify
the isa in the class definition of the instruction:


.. testcode:: encoding

    class Stm8Instruction(Instruction):
        isa = my_isa

The class Stm8Instruction and all of its subclasses will now be automatically
added to the isa.

Often there are some common instructions for data definition, such as
the db instruction to define a byte. These are already defined in
data_instructions. Isa's can be added to eachother to combine them, like this:

.. testcode:: encoding

    from ppci.arch.data_instructions import data_isa
    my_complete_isa = my_isa + data_isa



Architecture description
~~~~~~~~~~~~~~~~~~~~~~~~
