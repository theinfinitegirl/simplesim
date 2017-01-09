
import numpy as np
import re
from collections import namedtuple;

class Op(object):
    def __init__(self, mnemonic, args, opcode, impl):
        self.mnemonic = mnemonic
        self.args = args
        self.opcode = opcode.replace(" ","")        
        self.impl = impl

    def Apply(self, cpu_state):
        self.impl(cpu_state)

    def Emit(self):
        pass

    def Size(self):
        return len(self.opcode) / 8
    
AllOps = {}

class Instruction(object):
    def __init__(self, op, args, addr):
        self.op = op
        self.args = args[:]
        self.addr = addr
        
    def __repr__(self):
        return (("%04x" % self.addr) + ": <" + self.op.mnemonic + " "
                + ','.join([str(x) for x in self.args]) + '>')
    
    def Size(self):
        return self.op.Size()
    
class DefinedBytes(Instruction):
    def __init__(self, byte_vals, addr):
        self.byte_vals = []
        self.addr = addr
        for idx, val in enumerate(byte_vals):
            if isinstance(val, str):
                self.byte_vals.extend(ord(c) for c in val)
            else:
                if val < -128 or val > 255:
                    raise ASMError("Byte value out of range.")
                self.byte_vals.append(val)

    def __repr__(self):
        return (("%04x" % self.addr) + ": DB: " + 
                ', '.join(str(x) for x in self.byte_vals))

    def Size(self):
        return len(self.byte_vals) + len(self.byte_vals) % 2

class DefinedWords(Instruction):
    def __init__(self, word_vals, addr):
        self.word_vals = word_vals
        self.addr = addr
        for idx, val in enumerate(word_vals):
            if val < -32768 or val > 65535:
                raise ASMError("Word value out of range.")
    def __repr__(self):
        return (("%04x" % self.addr) + ": DW: " + 
                ', '.join(str(x) for x in self.word_vals))

    def Size(self):
        return len(self.word_vals) * 2

class Segment(object):
    def __init__(self, seg_type):
        self.origin = None
        self._cur_offset = 0
        self.instructions = []
        self.labels = {}
        self.seg_type = seg_type
        if seg_type not in ["CSEG", "DSEG", "ESEG"]:
            raise ASMError("Invalid segment type")

    def set_origin(self, address):
        self.origin = address

    @property
    def cur_offset(self):
        return self._cur_offset;

    def reserve_bytes(self, nbytes):
        if self.seg_type not in ["DSEG", "ESEG"]:
            raise ASMError("Can only reseve bytes in data segments.")
        self._cur_offset += nbytes
        
    def define_bytes(self, byte_vals):
        bytes_pseudo_op = DefinedBytes(byte_vals, self.cur_offset)
        self.instructions.append(bytes_pseudo_op)
        self._cur_offset += bytes_pseudo_op.Size()

    def define_words(self, word_vals):
        word_pseudo_op = DefinedWords(word_vals, self.cur_offset)
        self.instructions.append(word_pseudo_op)
        self._cur_offset += word_pseudo_op.Size()

    def add_instruction(self, op, args):
        inst = Instruction(op, args, self.cur_offset)
        self.instructions.append(inst)
        self._cur_offset += len(inst.op.opcode) / 8
        return inst
    
    def add_label(self, label):
        if label in self.labels:
            raise ASMError("Duplicate label: %s" % label)
        self.labels[label] = self.cur_offset;
    
    


# Arg types:
kArgConst = 1
kArgReg = 2
kArgXReg = 3
kArgYReg = 4
kArgZReg = 5

#Addressing Flags
kDirect = 0

ArgumentType = namedtuple("ArgumentType", "symbol type bits signed description")

kArgTypes = [
    ArgumentType("Rd", kArgReg, 5, False, "Destination register"),
    ArgumentType("Rr", kArgReg, 5, False, "Source register"),
    ArgumentType("K", kArgConst, 8, False, "Constant data"),
    ArgumentType("k", kArgConst, None, True, "Constant address"),
    ArgumentType("b", kArgConst, 3, False, "Bit in a register"),
    ArgumentType("s", kArgConst, 3, False, "Bit in the status register"),
    ArgumentType("X", kArgReg, 0, False, "Indirect address register (R27:R26)"),
    ArgumentType("Y", kArgReg, 0, False, "Indirect address register (R29:R28)"),
    ArgumentType("Z", kArgReg, 0, False, "Indirect address register (R31:R30)"),
    ArgumentType("A", kArgConst, None, False, "IO location address"),
    ArgumentType("q", kArgConst, 6, False, "Displacement for direct addressing"),
    ]
    
kArgTypesMap = dict((at.symbol,at) for at in kArgTypes)

class OpArg(object):
    pass


class RegisterArg(OpArg):
    def __init__(self, regnum, flags=kDirect):
        self.regnum = regnum
        self.flags = flags
        if regnum >= 32:
            raise ASMError("Invalid register number %d" % regnum)
        
class ConstantArg(OpArg):
    def __init__(self, arg):
        self.value = arg

class SymbolArg(OpArg):
    def __init__(self, arg):
        self.label = arg

class declare_op(object):
    def __init__(self, args, opcode):
        """
        If there are decorator arguments, the function
        to be decorated is not passed to the constructor!
        """
        self.args = []
        if args:
            for arg in args.split(','):
                match = re.match('(\w+):(\d+)', arg)
                if match:
                    arg = match.group(1)
                    bits_required = match.group(2)
                    argtype = kArgTypesMap[arg]
                    argtype = argtype._replace(bits=bits_required)
                else:
                    argtype = kArgTypesMap[arg]
                self.args.append(argtype)
                
            
        self.opcode = opcode.replace(' ','')

    def __call__(self, f):
        """
        If there are decorator arguments, __call__() is only called
        once, as part of the decoration process! You can only give
        it a single argument, which is the function object.
        """
        op = Op(f.__name__, self.args, self.opcode, f)
        AllOps[f.__name__] = op
        return f;
    

def match_arg(argtype, value):
    if (isinstance(value, RegisterArg)):
        if argtype.symbol not in ('Rr', 'Rd'):
            raise ASMError("Expected numeric value, got register.")
    elif (isinstance(value, ConstantArg)):
        if argtype.symbol in ('Rr', 'Rd', 'X', 'Y', 'Z'):
            raise ASMError("Expected a register, got constant.")
        if argtype.signed:
            if -(1 << (argtype.bits - 1)) <= value.value < (1 << (argtype.bits - 1)):
                return
            raise ASMError("Constant exceeds range of argument")
        else:
            if value.value >= (1 << argtype.bits):
                raise ASMError("Constant exceeds range of argument")
            elif value.value < 0:
                raise ASMError("Expected unsigned argument")
            
    elif isinstance(value, SymbolArg):
        # Labels will be resoved later
        pass
    
    
class ASMError(Exception):
    pass



@declare_op("Rd,Rr", "0000 11rd dddd rrrr")
def ADD(cpu_state, inst):
    print "ADD " + ",".join(inst.args)

@declare_op("k:14", "1001 010k kkkk 110k kkkk kkkk kkkk kkkk")
def JMP(cpu_state, inst):
    print " " + ",".join(inst.args)


@declare_op("", "0000 0000 0000 0000")
def NOP(cpu_state, inst):
    print "No-op"


# Idea: decorate function for ops, which takes syntax, args, and validators
# Decorator registers function (hasta deal with same mnemonic for things like LD
# which have multiple addressing modes
# Perhaps we should just special case LD, ST, LPM, SPM

# The function then takes a cpu state (mem, regs, clock?) and modifies it
# How to deal with different archs? maybe stick w/tiny for now.
