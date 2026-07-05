import re
from dataclasses import dataclass
from typing import List

LUA_KEYWORDS = {
    "and", "break", "do", "else", "elseif", "end", "false", "for", "function",
    "goto", "if", "in", "local", "nil", "not", "or", "repeat", "return",
    "then", "true", "until", "while"
}

@dataclass
class Token:
    type: str
    value: str
    line: int

class LuaTokenizer:
    def __init__(self):
        self.patterns = [
            ('ML_COMMENT', r'--\[(=*)\[[\s\S]*?\]\1\]'),
            ('SL_COMMENT', r'--[^\r\n]*'),
            ('ML_STRING', r'\[(=*)\[[\s\S]*?\]\1\]'),
            ('DQ_STRING', r'"[^"\\]*(?:\\.[^"\\]*)*"'),
            ('SQ_STRING', r"'[^'\\]*(?:\\.[^'\\]*)*'"),
            ('NUMBER', r'0[xX][0-9a-fA-F]+(?:\.[0-9a-fA-F]*)?(?:[pP][+-]?[0-9]+)?|0[xX]\.[0-9a-fA-F]+(?:[pP][+-]?[0-9]+)?|\d+(?:\.\d*)?(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?'),
            ('IDENTIFIER', r'[a-zA-Z_][a-zA-Z0-9_]*'),
            ('OP_THREE', r'\.\.\.'),
            ('OP_TWO', r'==|~=|<=|>=|\.\.|::'),
            ('OP_ONE', r'[-+*/%^#=<>(){}[\];:.,]'),
            ('WHITESPACE', r'[ \t\r\n]+'),
        ]
        self.compiled = [(name, re.compile(pat)) for name, pat in self.patterns]

    def tokenize(self, source: str) -> List[Token]:
        tokens = []
        pos = 0
        n = len(source)
        line = 1
        while pos < n:
            match_found = False
            for name, rx in self.compiled:
                m = rx.match(source, pos)
                if m:
                    val = m.group(0)
                    newlines = val.count('\n')
                    tname = name
                    if tname == 'IDENTIFIER' and val in LUA_KEYWORDS:
                        tname = 'KEYWORD'
                    tokens.append(Token(tname, val, line))
                    line += newlines
                    pos += len(val)
                    match_found = True
                    break
            if not match_found:
                char = source[pos]
                tokens.append(Token('ERROR', char, line))
                if char == '\n':
                    line += 1
                pos += 1
        return tokens

