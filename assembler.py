import ply.lex as lex

tokens = "NUMBER SPECIAL LABEL SYMBOL STRING".split()
literals = "=,@"



def ASMLexer():
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

    def t_SPECIAL(t):
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

    def t_newline(t):
        r'\n+'
        t.lexer.lineno += len(t.value)

    t_SYMBOL = r'\w+'
    t_ignore = ' \t'

    def t_error(t):
        print("Illegal character '%s'" % t.value[0])
        t.lexer.skip(1)

    return lex.lex()
