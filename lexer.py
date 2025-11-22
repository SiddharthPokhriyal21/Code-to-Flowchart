# lexer.py

import re

# 1) Token specification covers:
#    • Keywords: int, float, string, main, if, else, while, for, do, return
#    • Identifiers: [A-Za-z_][A-Za-z0-9_]*
#    • Float literals: \d+\.\d+
#    • Integer literals: \b\d+\b
#    • String literals: ".*?"
#    • Multi-character operators: ==, !=, <=, >=, <<, >>
#    • Single-character operators: + - * / % = < >
#    • Punctuation: ( ) { } ;
#    • Whitespace to skip
#    • MISMATCH for any other unexpected character

token_specification = [
    ('INT',         r'\bint\b'),
    ('FLOAT_TYPE',  r'\bfloat\b'),
    ('STRING_TYPE', r'\bstring\b'),
    ('MAIN',        r'\bmain\b'),
    ('IF',          r'\bif\b'),
    ('ELSE',        r'\belse\b'),
    ('WHILE',       r'\bwhile\b'),
    ('FOR',         r'\bfor\b'),
    ('DO',          r'\bdo\b'),
    ('RETURN',      r'\breturn\b'),

    ('ID',          r'[A-Za-z_][A-Za-z0-9_]*'),  # identifiers

    ('FLOAT_NUM',   r'\d+\.\d+'),                # floating-point literal (must come before integer)
    ('NUM',         r'\b\d+\b'),                 # integer literal
    ('STRING',      r'\".*?\"'),                 # string literal in double quotes

    # multi-character operators
    ('OP',          r'==|!=|<=|>=|<<|>>|[+\-*/%=<>]'),

    ('LPAREN',      r'\('),
    ('RPAREN',      r'\)'),
    ('LBRACE',      r'\{'),
    ('RBRACE',      r'\}'),
    ('SEMI',        r';'),
    ('SKIP',        r'[ \t\n]+'),
    ('MISMATCH',    r'.'),
]

tok_regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in token_specification)
get_token = re.compile(tok_regex).match

def lexer(code: str):
    """
    Convert source code text into a list of tokens.
    Each token is a dict: {'type': ..., 'value': ...}.
    Raises RuntimeError on unexpected character.
    """
    pos = 0
    tokens = []
    mo = get_token(code)
    while mo is not None:
        typ = mo.lastgroup
        val = mo.group(typ)
        if typ == 'SKIP':
            pass
        elif typ == 'MISMATCH':
            raise RuntimeError(f'Unexpected character {val!r} at position {pos}')
        else:
            tokens.append({'type': typ, 'value': val})
        pos = mo.end()
        mo = get_token(code, pos)
    return tokens
