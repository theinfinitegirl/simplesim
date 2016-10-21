import ply.lex as lex
import ply.yacc as yacc

import program as prog

tokens = "NUMBER DIRECTIVE LABEL SYMBOL STRING REGISTER NEWLINE".split()
literals = "=,@"


states = (
    ('text', 'exclusive'),
    )
def t_text_BACKSLASH(t):
    r'\\\\'
    t.lexer.text_value += r"\\"
    print "escbs"

def t_text_ESCAPED_QUOTE(t):
    r'\"'
    print "escquote"
    t.lexer.text_value += '"'

def t_text_ESCAPED_OTHER(t):
    r'\\.'
    t.lexer.text_value += t.value[1]

def t_text_INSTRING(t):
    r'[^"\\]+'
    print "Read some"
    t.lexer.text_value += t.value


t_text_ignore = ""

def t_text_EXITSTRING(t):
    r'"'
    t.value = t.lexer.text_value
    t.type = 'STRING'
    t.lexer.begin('INITIAL')
    return t

def t_STRING(t):
    r'\"'
    t.lexer.text_start = t.lexer.lexpos
    t.lexer.text_value = ""
    t.lexer.begin('text')

def t_COMMENT(t):
    r';.*'
    pass # ignore comments

def t_LABEL(t):
    r'\w+:'
    t.value = t.value[:-1]
    return t

def t_DIRECTIVE(t):
    r'\.[A-Za-z]+'
    t.value = t.value[1:]
    return t

def t_NUMBER(t):
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

def t_REGISTER(t):
    r'[rR]\d\d?'
    t.value = int(t.value[1:])
    return t

def t_NEWLINE(t):
    r'\n'
    t.lexer.lineno += 1
    return t


t_SYMBOL = r'\w+'
t_ignore = ' \t'

def t_error(t):
    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)


def test_lexer():
  test_str = ("""
     .equ symbol = 45
     label1: BR R01,R02
     numbers: 15 0x0F $000f 0b01111""")
  
  lexer = lex.lex()
  lexer.input(test_str)
  toks = []
  while 1:
    tok = lexer.token()
    if tok is None:
      return toks
    toks.append(tok)

lexer = lex.lex()

def p_program(p):
  '''program : lines'''
  pass

def p_lines(p):
  '''lines : empty
                | line lines'''
  pass

def p_line(p):
  """
  line : statement
       | LABEL statement
  """
  pass

def p_statement(p):
  """
  statement : NEWLINE
            | instruction NEWLINE
            | DIRECTIVE NEWLINE
  """
  pass

def p_instruction(p):
    """
    instruction : SYMBOL arglist
    """
    print p[2]
    try:
        op = prog.AllOps[p[1].upper()]
        if len(p[2]) != len(op.args):
           raise prog.ASMError("Operation %s takes %d arguments." % (tok, len(op.args)))
         

    except KeyError:
        raise prog.ASMError("Unknown operation " + p[1] + " at line: " + str(p.lineno(1)) )


def p_arglist_empty(p):
    'arglist : empty'
    p[0] = []

def p_arglist(p):
    """ arglist : arg
                | arglist ',' arg
    """
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[1].append(p[3])
        p[0] = p[1]

def p_arg_register(p):
    " arg : REGISTER "
    p[0] = prog.RegisterArg(p[1])

def p_arg_number(p):
    "arg : NUMBER"
    p[0] = prog.ConstantArg(p[1])

def p_arg_symbol(p):
    "arg : SYMBOL"
    p[0] = prog.SymbolArg(p[1])
    
def p_empty(p):
  'empty :'
  pass

parser = yacc.yacc(write_tables=False, debug=True)
