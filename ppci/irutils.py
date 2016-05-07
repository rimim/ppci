
"""
    Some utilities for ir-code.
"""
import logging
import re
from . import ir
from .domtree import CfgInfo
from .common import IrFormError


IR_FORMAT_INDENT = 2


class Writer:
    """ Write ir-code to file """
    def __init__(self, extra_indent=''):
        self.extra_indent = extra_indent

    def print(self, *txt):
        print(self.extra_indent + ''.join(txt), file=self.f)

    def write(self, module, f):
        """ Write ir-code to file f """
        assert type(module) is ir.Module
        self.f = f
        self.print('{}'.format(module))
        for v in module.variables:
            self.print()
            self.print('{}'.format(v))
        for function in module.functions:
            self.print()
            self.write_function(function)

    def write_function(self, fn):
        self.print('{}'.format(fn))
        for block in fn.blocks:
            self.print('  {}'.format(block))
            for ins in block:
                self.print('    {}'.format(ins))


class IrParseException(Exception):
    pass


class Reader:
    """ Read IR-code from file """
    def __init__(self):
        pass

    def read(self, f):
        """ Read ir code from file f """
        # Read lines from the file:
        lines = [line.rstrip() for line in f]

        # Create a regular expression for the lexing part:
        tok_spec = [
            ('NUMBER', r'\d+'),
            ('ID', r'[A-Za-z][A-Za-z\d_]*'),
            ('SKIP', r' +'),
            ('OTHER', r'[\.,=:;\-+*\[\]/\(\)]|>|<|{|}|&|\^|\|')
            ]
        tok_re = '|'.join('(?P<%s>%s)' % pair for pair in tok_spec)
        gettok = re.compile(tok_re).match

        def tokenize():
            for line in lines:
                if not line:
                    continue  # Skip empty lines
                mo = gettok(line)
                first = True
                while mo:
                    typ = mo.lastgroup
                    val = mo.group(typ)
                    if typ == 'ID':
                        if val in ['function', 'module']:
                            typ = val
                        yield (typ, val)
                    elif typ == 'OTHER':
                        typ = val
                        yield (typ, val)
                    elif typ == 'SKIP':
                        if first:
                            assert len(val) % IR_FORMAT_INDENT == 0
                            if len(val) == IR_FORMAT_INDENT:
                                typ = 'SKIP1'
                            elif len(val) == IR_FORMAT_INDENT * 2:
                                typ = 'SKIP2'
                            else:
                                raise Exception()
                            yield (typ, val)
                    elif typ == 'NUMBER':
                        yield (typ, int(val))
                    else:
                        raise NotImplementedError(str(typ))
                    first = False
                    pos = mo.end()
                    mo = gettok(line, pos)
                if len(line) != pos:
                    raise IrParseException('Lex fault')
                yield ('eol', 'eol')
            yield ('eof', 'eof')
        self.tokens = tokenize()
        self.token = self.tokens.__next__()

        try:
            module = self.parse_module()
            return module
        except IrParseException as e:
            print(e)
            raise Exception(str(e))

    def next_token(self):
        t = self.token
        if t[0] != 'eof':
            self.token = self.tokens.__next__()
        return t

    @property
    def Peak(self):
        return self.token[0]

    @property
    def PeakVal(self):
        return self.token[1]

    def Consume(self, typ, val=None):
        if self.Peak == typ:
            if val is not None:
                assert self.PeakVal == val
            return self.next_token()
        else:
            raise IrParseException('Expected "{}" got "{}"'
                                   .format(typ, self.Peak))

    def parse_module(self):
        """ Entry for recursive descent parser """
        self.Consume('module')
        name = self.Consume('ID')[1]
        module = ir.Module(name)
        self.Consume('eol')
        while self.Peak != 'eof':
            if self.Peak == 'function':
                module.add_function(self.parse_function())
            else:
                raise IrParseException('Expected function got {}'
                                       .format(self.Peak))
        return module

    def parse_function(self):
        self.Consume('function')
        self.parse_type()

        # Setup maps:
        self.val_map = {}
        self.block_map = {}
        self.resolve_worklist = []

        name = self.Consume('ID')[1]
        function = ir.Function(name)
        self.Consume('(')
        while self.Peak != ')':
            ty = self.parse_type()
            name = self.Consume('ID')[1]
            ty = self.find_type(ty)
            param = ir.Parameter(name, ty)
            function.add_parameter(param)
            self.add_val(param)
            if self.Peak != ',':
                break
            else:
                self.Consume(',')
        self.Consume(')')
        self.Consume('eol')
        while self.Peak == 'SKIP1':
            block = self.parse_block()
            function.add_block(block)
            self.block_map[block.name] = block

        for ins, blocks in self.resolve_worklist:
            for b in blocks:
                b2 = self.find_block(b.name)
                ins.change_target(b, b2)
        return function

    def parse_type(self):
        return self.Consume('ID')[1]

    def parse_block(self):
        self.Consume('SKIP1')
        name = self.Consume('ID')[1]
        block = ir.Block(name)
        self.Consume(':')
        self.Consume('eol')
        while self.Peak == 'SKIP2':
            ins = self.parse_statement()
            block.add_instruction(ins)
        return block

    def add_val(self, v):
        self.val_map[v.name] = v

    def find_val(self, name):
        return self.val_map[name]

    def find_type(self, name):
        ty_map = {'i32': ir.i32}
        return ty_map[name]

    def find_block(self, name):
        return self.block_map[name]

    def parse_assignment(self):
        ty = self.Consume('ID')[1]
        name = self.Consume('ID')[1]
        self.Consume('=')
        if self.Peak == 'ID':
            a = self.Consume('ID')[1]
            if self.Peak in ['+', '-']:
                # Go for binop
                op = self.Consume(self.Peak)[1]
                b = self.Consume('ID')[1]
                a = self.find_val(a)
                ty = self.find_type(ty)
                b = self.find_val(b)
                ins = ir.Binop(a, op, b, name, ty)
            else:
                raise Exception()
        elif self.Peak == 'NUMBER':
            cn = self.Consume('NUMBER')[1]
            ty = self.find_type(ty)
            ins = ir.Const(cn, name, ty)
        else:
            raise Exception()
        return ins

    def parse_cjmp(self):
        self.Consume('ID', 'cjmp')
        a = self.Consume('ID')[1]
        op = self.Consume(self.Peak)[0]
        b = self.Consume('ID')[1]
        L1 = self.Consume('ID')[1]
        L2 = self.Consume('ID')[1]
        L1 = ir.Block(L1)
        L2 = ir.Block(L2)
        a = self.find_val(a)
        b = self.find_val(b)
        ins = ir.CJump(a, op, b, L1, L2)
        self.resolve_worklist.append((ins, (L1, L2)))
        return ins

    def parse_jmp(self):
        self.Consume('ID', 'jmp')
        L1 = self.Consume('ID')[1]
        L1 = ir.Block(L1)
        ins = ir.Jump(L1)
        self.resolve_worklist.append((ins, (L1,)))
        return ins

    def parse_return(self):
        self.Consume('ID', 'return')
        val = self.find_val(self.Consume('ID')[1])
        # TODO: what to do with return value?
        ins = ir.Terminator()
        return ins

    def parse_statement(self):
        self.Consume('SKIP2')
        if self.Peak == 'ID' and self.PeakVal == 'jmp':
            ins = self.parse_jmp()
        elif self.Peak == 'ID' and self.PeakVal == 'cjmp':
            ins = self.parse_cjmp()
        elif self.Peak == 'ID' and self.PeakVal == 'return':
            ins = self.parse_return()
        elif self.Peak == 'ID' and self.PeakVal == 'store':
            raise Exception()
        elif self.Peak == 'ID' and self.PeakVal == 'Terminator':
            self.Consume('ID')
            ins = ir.Terminator()
        else:
            ins = self.parse_assignment()
            self.add_val(ins)
        self.Consume('eol')
        return ins


# Constructing IR:

class NamedClassGenerator:
    def __init__(self, prefix, cls):
        self.prefix = prefix
        self.cls = cls

        def NumGen():
            a = 0
            while True:
                yield a
                a = a + 1
        self.nums = NumGen()

    def gen(self, prefix=None):
        if not prefix:
            prefix = self.prefix
        return self.cls('{0}{1}'.format(prefix, self.nums.__next__()))


def split_block(block, pos=None, newname='splitblock'):
    """ Split a basic block into two which are connected """
    if pos is None:
        pos = int(len(block) / 2)
    rest = block.instructions[pos:]
    block2 = ir.Block(newname)
    block.function.add_block(block2)
    for instruction in rest:
        block.remove_instruction(instruction)
        block2.add_instruction(instruction)

    # Add a jump to the original block:
    block.add_instruction(ir.Jump(block2))
    return block, block2


class Builder:
    """ Base class for ir code generators """
    def __init__(self):
        self.prepare()
        self.block = None
        self.module = None
        self.function = None

    def prepare(self):
        self.newBlock2 = NamedClassGenerator('block', ir.Block).gen
        self.block = None
        self.module = None
        self.function = None

    # Helpers:
    def set_module(self, module):
        self.module = module

    def new_function(self, name):
        f = ir.Function(name)
        self.module.add_function(f)
        return f

    def new_block(self):
        """ Create a new block and add it to the current function """
        assert self.function is not None
        block = self.newBlock2()
        self.function.add_block(block)
        return block

    def set_function(self, f):
        self.function = f
        self.block = f.entry if f else None

    def set_block(self, block):
        self.block = block

    def emit(self, instruction):
        """ Append an instruction to the current block """
        assert isinstance(instruction, ir.Instruction), str(instruction)
        if self.block is None:
            raise Exception('No basic block')
        self.block.add_instruction(instruction)
        return instruction


class Verifier:
    """ Checks an ir module for correctness """
    def __init__(self):
        self.logger = logging.getLogger('verifier')

    def verify(self, module):
        """ Verifies a module for some sanity """
        assert isinstance(module, ir.Module)
        for function in module.functions:
            self.verify_function(function)

    def verify_function(self, function):
        """ Verify all blocks in the function """
        self.name_map = {}
        for block in function:
            self.verify_block_termination(block)

        # Verify predecessor and successor:
        for block in function:
            preds = set(b for b in function if block in b.successors)
            assert preds == set(block.predecessors)

        # Check that phi's have inputs for each predecessor:
        for block in function:
            for phi in block.phis:
                for predecessor in block.predecessors:
                    used_value = phi.get_value(predecessor)
                    # Check that phi 'use' info is good:
                    assert used_value in phi.uses

        # Now we can build a dominator tree
        function.cfg_info = CfgInfo(function)
        for block in function:
            assert block.function == function
            self.verify_block(block)

    def verify_block_termination(self, block):
        """ Verify that the block is terminated correctly """
        assert not block.empty
        assert block.last_instruction.is_terminator
        assert all(not i.is_terminator for i in block.instructions[:-1])

    def verify_block(self, block):
        """ Verify block for correctness """
        for instruction in block:
            self.verify_instruction(instruction, block)

    def verify_instruction(self, instruction, block):
        """ Verify that instruction belongs to block and that all uses
            are preceeded by defs """

        # Check that instruction is contained in block:
        assert instruction.block == block
        assert instruction in block.instructions

        # Check that binop operands are of same type:
        if isinstance(instruction, ir.Binop):
            assert instruction.ty is instruction.a.ty
            assert instruction.ty is instruction.b.ty
        elif isinstance(instruction, ir.Load):
            assert instruction.address.ty is ir.ptr
        elif isinstance(instruction, ir.Store):
            assert instruction.address.ty is ir.ptr
        elif isinstance(instruction, ir.Phi):
            for inp_val in instruction.inputs.values():
                assert instruction.ty is inp_val.ty
        elif isinstance(instruction, ir.CJump):
            assert instruction.a.ty is instruction.b.ty

        # Verify that all uses are defined before this instruction.
        for value in instruction.uses:
            assert value.dominates(instruction), \
                "{} does not dominate {}".format(value, instruction)
            # Check that a value is not undefined:
            if isinstance(value, ir.Undefined):
                raise IrFormError(
                    '{} used uninitialized'.format(value), loc=value.loc)
