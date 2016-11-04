import ply.lex as lex
import ply.yacc as yacc

import program as prog


class ASMLexer(object):

    def __init__(self, var_lookup_func, def_lookup_func):
        self.var_lookup_func = var_lookup_func
        self.def_lookup_func = def_lookup_func

    reserved = {
        ".EQU": "EQU",
        ".DEF": "DEF",
        ".ORG": "ORG",
        ".CSEG": "CSEG",
        ".DSEG": "DSEG",
    }

    tokens = ("NUMBER LABEL SYMBOL STRING REGISTER NEWLINE".split() + 
              list(reserved.values()))
    
    literals = "=,@"

    states = (
        ('text', 'exclusive'),
        )
    
    def t_text_BACKSLASH(self, t):
        r'\\\\'
        t.lexer.text_value += r"\\"
        print "escbs"

    def t_text_ESCAPED_QUOTE(self, t):
        r'\"'
        print "escquote"
        t.lexer.text_value += '"'

    def t_text_ESCAPED_OTHER(self, t):
        r'\\.'
        t.lexer.text_value += t.value[1]

    def t_text_INSTRING(self, t):
        r'[^"\\]+'
        print "Read some"
        t.lexer.text_value += t.value

    t_text_ignore = ""

    def t_text_EXITSTRING(self, t):
        r'"'
        t.value = t.lexer.text_value
        t.type = 'STRING'
        t.lexer.begin('INITIAL')
        return t

    def t_STRING(self, t):
        r'\"'
        t.lexer.text_start = t.lexer.lexpos
        t.lexer.text_value = ""
        t.lexer.begin('text')

    def t_COMMENT(self, t):
        r';.*'
        pass # ignore comments

    def t_LABEL(self, t):
        r'[\w_.]+:'
        t.value = t.value[:-1]
        return t

    def t_NUMBER(self, t):
        r'0x[0-9a-fA-F]+ | \$[0-9a-fA-F]+ | 0b[01]+ | \d+'
        r'(\d+)|((\$|(0x))[0-9a-fA-F]+)'
        if t.value.startswith('$'):
            t.value = int(t.value[1:], 16)
        elif t.value.startswith('0x'):
            t.value = int(t.value[2:], 16)
        elif t.value.startswith('0b'):
            t.value = int(t.value[2:], 2)    
        else:
            t.value = int(t.value)
        return t

    def t_REGISTER(self, t):
        r'[rR]\d\d?'
        t.value = int(t.value[1:])
        return t

    def t_NEWLINE(self, t):
        r'\n'
        t.lexer.lineno += 1
        return t

    def t_SYMBOL(self, t):
        r'[\w._]+'
        t.type = reserved.get(t.value.upper(), 'SYMBOL')
        if t.type == 'SYMBOL':
            val = self.var_lookup_func(t.value)
            if val is not None:
                t.type = 'NUMBER'
                t.value = val
            else:
                val = self.def_lookup_func(t.value)
                if val is not None:
                    t.type = 'REGISTER'
                    t.value = val
        return t

    t_ignore = ' \t'

    def t_error(self, t):
        print("Illegal character '%s'" % t.value[0])
        t.lexer.skip(1)

    
    def build(self, **kwargs):
        self.lexer = lex.lex(object=self, **kwargs)
        self.built = True


class ASMParser(object):
    def p_program(self, p):
      '''program : lines'''
      p.cur_seg = 7
      pass

    def p_lines(self, p):
      '''lines : empty
                    | line lines'''
      pass

    def p_line(self, p):
      """
      line : statement
           | LABEL seen_label statement
      """
      pass

    def p_seen_label(self, p):
        """
        seen_label : empty
        """
        # Use embedded action to add labels, so that we can get
        # the program counter _before_ any instruction is added
        self.cur_seg.add_label(p[-1])

    def p_statement(self, p):
      """
      statement : NEWLINE
                | instruction NEWLINE
      """
      pass

    def p_equ_statement(self, p):
        """
        statement : EQU SYMBOL '=' constexpr
                  | SYMBOL '=' constexpr
        """
        # Allow gnu or atmel syntax
        if len(p) == 5:
            varname, varval = p[2],p[4]
        else:
            varname, varval = p[1],p[3]
        if varname in self.variables:
            print "Warning: redeclaring variable:", varname
        self.variables[varname] = varval

    def p_instruction(self, p):
        """
        instruction : SYMBOL arglist
        """
        try:
            op = prog.AllOps[p[1].upper()]
            if len(p[2]) != len(op.args):
               raise prog.ASMError("Operation %s takes %d arguments." % (tok, len(op.args)))
            for idx, (oparg, inarg) in enumerate(zip(op.args, p[2])):
                if oparg.type == prog.kArgConst:
                    if isinstance(inarg, prog.RegisterArg):
                        raise prog.ASMError("Operation %s takes a register for argument %d." % (tok, idx))
                elif oparg.type == prog.kArgReg:
                    if isinstance(inarg, prog.ConstantArg):
                        raise prog.ASMError("Operation %s takes a numeric argument %d." % (tok, idx))

            p[0] = self.cur_seg.add_instruction(op, p[2])

        except KeyError:
            raise prog.ASMError("Unknown operation " + p[1] + " at line: " + str(p.lineno(1)) )


    def p_arglist_empty(self, p):
        'arglist : empty'
        p[0] = []

    def p_arglist(self, p):
        """ arglist : arg
                    | arglist ',' arg
        """
        if len(p) == 2:
            p[0] = [p[1]]
        else:
            p[1].append(p[3])
            p[0] = p[1]

    def p_arg_register(self, p):
        " arg : REGISTER "
        p[0] = prog.RegisterArg(p[1])

    def p_arg_number(self, p):
        "arg : NUMBER"
        p[0] = prog.ConstantArg(p[1])

    def p_arg_symbol(self, p):
        "arg : SYMBOL"
        p[0] = prog.SymbolArg(p[1])
    
    def p_constexpr_num(self, p):
        "constexpr : NUMBER"
        p[0] = int(p[1])

    def p_constexpr_var(self, p):
        "constexpr : SYMBOL"
        # Variable has to have been previously declared
        try:
            p[0] = self.variables[p[1]]
        except KeyError:
            raise prog.ASMError("Unknown variable: " + p[1])
        
    def p_empty(self, p):
      'empty :'
      pass

    def __init__(self):
        self.built = False

    def var_lookup_func(self, varname):
        if varname in self.variables:
            return self.variables[varname]
        else:
            return None

    def def_lookup_func(self, defname):
        if defname in self.defs:
            return self.defs[defname]
        else:
            return None

    def build(self):
        self.lexer = ASMLexer(var_lookup_func = self.var_lookup_func,
                              def_lookup_func = self.def_lookup_func
                          )
        self.lexer.build()
        self.tokens = self.lexer.tokens
        self.parser = yacc.yacc(module=self, write_tables=False, debug=True)
        self.built = True

    def parse(self, text):
        if not self.built:
            self.build()
        self.variables = {}
        self.defs = {}
        self.cur_seg = prog.Segment()
        self.segments = [self.cur_seg]
        self.parser.parse(text)
        
