
import numpy as np
import re

kTokenizeRE = re.compile('\s+|(,)')
kRegisterRE = re.compile('[rR](\d\d?)')
kConstantRE = re.compile('[+-]?\d+')
kLabelRE = re.compile('^([a-zA-Z_][a-zA-Z_0-9]+)$')

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
    def __init__(self, op, addr, args):
        self.op = op
        self.addr = addr
        self.args = args[:]
        
    def __repr__(self):
        return (("%04x" % self.addr) + ": <" + self.op.mnemonic + " "
                + ','.join([str(x) for x in self.args]) + '>')
    
    def Size(self):
        return self.op.Size()
    
# Arg types:
kArgConst = 1
kArgReg = 2
kArgXReg = 3
kArgYReg = 4
kArgZReg = 5

class OpArg(object):
    pass

class RegisterArg(OpArg):
    def __init__(self, arg):
        m = kRegisterRE.match(arg)
        if not m or int(m.group(1)) >= 32:
            raise ASMError("Invalid register argument: " + arg)
        self.register = int(m.group(1))
    def __repr__(self):
        return "R%d" % self.register

class ConstantArg(OpArg):
    def __init__(self, arg):
        self.value = int(arg)

class LabelArg(OpArg):
    def __init__(self, arg):
        self.label = arg

def parse_arg(arg, oparg):
    if oparg.startswith('R'):
        return RegisterArg(arg)
    elif arg in ["X", "Y", "Z"]:
        return arg
    elif arg :
        return LabelArg(arg)
    else:
        return int(arg)

class declare_op(object):

    def __init__(self, args, opcode):
        """
        If there are decorator arguments, the function
        to be decorated is not passed to the constructor!
        """
        self.args = args.split(',')
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
    
    
class CPUState(object):
    # Need program mem as the main thing, but should have ways to set
    # status reg flags, SP, etc
    def __init__(self, ramsize):
        self.ram = np.zeros(ramsize, np.uint8)

class ASMError(Exception):
    pass

def tokenize(line):
    for token in kTokenizeRE.split(line.strip()):
        if token:
            yield token

def parse_asm(text):
    cur_addr = 0
    labels = {}
    result = []
    lineno = 0
    for line in text.splitlines():
        lineno += 1
        # remove comments
        line = line.split(';',1)[0]
        toks = list(tokenize(line))
        tok_idx = 0
        if len(toks) == 0:
            continue

        tok = toks[tok_idx]
        if tok.startswith('.'):
            print "Saw directive; skipping line"
            continue
        elif tok.endswith(':'):
            label = tok[:-1]
            if not kLabelRE.match(label):
                raise ASMError("Invalid label: " + label)
            if label in labels:
                raise ASMError("Label " + label + " redeclared at line:" + str(lineno) + ".")
            labels[label] = cur_addr
            tok_idx += 1
            if tok_idx >= len(toks):
                continue
            tok = toks[tok_idx]
        if tok_idx < len(toks):
            if tok in AllOps:
                op = AllOps[tok]
                args = [tok for tok in toks[tok_idx + 1:] if tok != ',']
                if len(args) != len(op.args):
                    raise ASMError("Operation %s takes %d arguments." % (tok, len(op.args)))
                parsed_args = [parse_arg(arg, op_arg) for (arg, op_arg) in zip(args, op.args)]
                inst = Instruction(op, cur_addr, parsed_args)
                cur_addr += inst.Size()
                result.append(inst)
            else:
                raise ASMError("Unknown operation " + op + " at line:" + str(lineno) + ".")

    # resolve labels:
    for inst in result:
        for idx,arg in enumerate(inst.args):
            if isinstance(arg, LabelArg):
                try:                    
                    inst.args[idx] = labels[arg.label]
                except KeyError:
                    raise ASMError("Unknown label " + arg.label + " at line:" + str(lineno) + ".")

                
    return result


@declare_op("Rd,Rr", "0000 11rd dddd rrrr")
def ADD(cpu_state, inst):
    print "ADD " + ",".join(inst.args)

@declare_op("k", "1001 010k kkkk 110k kkkk kkkk kkkk kkkk")
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
