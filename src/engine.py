import re
import math
import json
import random
import os
from typing import List, Set
from src.tokenizer import LuaTokenizer, Token, LUA_KEYWORDS

class ObfuscatorEngine:
    def __init__(self, sentences: List[str]):
        self.tokenizer = LuaTokenizer()
        self.sentences = sentences

    def _minify_python(self, code: str) -> str:
        pattern = re.compile(r'(""\"[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'|#[^\r\n]*)')
        def replacer(match):
            s = match.group(0)
            if s.startswith('#'):
                return ''
            return s
        no_comments = pattern.sub(replacer, code)
        lines = []
        for line in no_comments.splitlines():
            if line.strip():
                lines.append(line)
        return "\n".join(lines)

    def _minify_javascript(self, code: str) -> str:
        pattern = re.compile(r'(/\*[\s\S]*?\*/|//[^\r\n]*|"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'|`(?:[^`\\]|\\.)*`)')
        def replacer(match):
            s = match.group(0)
            if s.startswith('/*') or s.startswith('//'):
                return ''
            return s
        no_comments = pattern.sub(replacer, code)
        lines = []
        for line in no_comments.splitlines():
            if line.strip():
                lines.append(line)
        return "\n".join(lines)

    def _sentence_to_identifier(self, sentence: str) -> str:
        cleaned = re.sub(r'[^a-zA-Z0-9\s]', ' ', sentence)
        words = [w for w in cleaned.split() if w]
        identifier = "_".join(words)
        if identifier and not (identifier[0].isalpha() or identifier[0] == '_'):
            identifier = "_" + identifier
        return identifier

    def _extract_local_variables(self, tokens: List[Token]) -> Set[str]:
        local_names = set()
        total_tokens = len(tokens)
        idx = 0
        while idx < total_tokens:
            token = tokens[idx]
            if token.type == 'KEYWORD' and token.value == 'local':
                idx += 1
                while idx < total_tokens and tokens[idx].type == 'WHITESPACE':
                    idx += 1
                if idx < total_tokens and tokens[idx].type == 'KEYWORD' and tokens[idx].value == 'function':
                    idx += 1
                    while idx < total_tokens and tokens[idx].type == 'WHITESPACE':
                        idx += 1
                    if idx < total_tokens and tokens[idx].type == 'IDENTIFIER':
                        local_names.add(tokens[idx].value)
                else:
                    while idx < total_tokens:
                        if tokens[idx].type == 'IDENTIFIER':
                            local_names.add(tokens[idx].value)
                        elif tokens[idx].type == 'OP_ONE' and tokens[idx].value == '=':
                            break
                        elif tokens[idx].type == 'WHITESPACE' and '\n' in tokens[idx].value:
                            break
                        idx += 1
            elif token.type == 'KEYWORD' and token.value == 'function':
                while idx < total_tokens and not (tokens[idx].type == 'OP_ONE' and tokens[idx].value == '('):
                    idx += 1
                if idx < total_tokens:
                    idx += 1
                    while idx < total_tokens and not (tokens[idx].type == 'OP_ONE' and tokens[idx].value == ')'):
                        if tokens[idx].type == 'IDENTIFIER':
                            local_names.add(tokens[idx].value)
                        idx += 1
            elif token.type == 'KEYWORD' and token.value == 'for':
                idx += 1
                while idx < total_tokens and not (tokens[idx].type == 'KEYWORD' and tokens[idx].value in ('do', 'in')):
                    if tokens[idx].type == 'IDENTIFIER':
                        local_names.add(tokens[idx].value)
                    idx += 1
            idx += 1
        return local_names

    def _rename_local_variables(self, tokens: List[Token], words: List[str]) -> List[Token]:
        local_names = self._extract_local_variables(tokens)
        assigned_names = set()
        name_mapping = {}
        
        if not words:
            words = ["decoy"]

        def _generate_obfuscated_name():
            attempts = 0
            while True:
                attempts += 1
                parts = [random.choice(words) for _ in range(random.randint(2, 3))]
                name = "_".join(parts)
                if not name[0].isalpha() and name[0] != '_':
                    name = "_" + name
                if attempts > 50:
                    name += f"_{attempts}"
                if name not in assigned_names and name not in LUA_KEYWORDS:
                    assigned_names.add(name)
                    return name

        for var in sorted(list(local_names)):
            if var not in LUA_KEYWORDS:
                name_mapping[var] = _generate_obfuscated_name()
                
        stack = []
        renamed_tokens = []
        total_tokens = len(tokens)
        idx = 0
        while idx < total_tokens:
            token = tokens[idx]
            
            if token.type == 'OP_ONE' and token.value == '{':
                stack.append('brace')
            elif token.type == 'OP_ONE' and token.value == '}':
                if stack and stack[-1] == 'brace':
                    stack.pop()
            elif token.type == 'KEYWORD' and token.value in ('do', 'then', 'repeat', 'function'):
                stack.append('block')
            elif token.type == 'KEYWORD' and token.value in ('else', 'elseif'):
                if stack and stack[-1] == 'block':
                    stack.pop()
                stack.append('block')
            elif token.type == 'KEYWORD' and token.value in ('end', 'until'):
                if stack and stack[-1] == 'block':
                    stack.pop()

            is_property_access = False
            if idx > 0:
                prev_idx = idx - 1
                while prev_idx >= 0 and tokens[prev_idx].type == 'WHITESPACE':
                    prev_idx -= 1
                if prev_idx >= 0 and tokens[prev_idx].type == 'OP_ONE' and tokens[prev_idx].value in ('.', ':'):
                    is_property_access = True

            is_table_key = False
            if token.type == 'IDENTIFIER' and idx + 1 < total_tokens:
                next_idx = idx + 1
                while next_idx < total_tokens and tokens[next_idx].type == 'WHITESPACE':
                    next_idx += 1
                if next_idx < total_tokens and tokens[next_idx].type == 'OP_ONE' and tokens[next_idx].value == '=':
                    if stack and stack[-1] == 'brace':
                        is_table_key = True
                        
            if token.type == 'IDENTIFIER' and token.value in name_mapping and not is_property_access and not is_table_key:
                renamed_tokens.append(Token('IDENTIFIER', name_mapping[token.value], token.line))
            else:
                renamed_tokens.append(token)
            idx += 1
            
        return renamed_tokens

    def _minify_whitespace(self, tokens: List[Token]) -> str:
        minified_tokens = []
        for token in tokens:
            if token.type in ('SL_COMMENT', 'ML_COMMENT'):
                continue
            if token.type == 'WHITESPACE':
                if minified_tokens and minified_tokens[-1].type == 'WHITESPACE':
                    continue
                minified_tokens.append(Token('WHITESPACE', ' ', token.line))
            else:
                minified_tokens.append(token)
        
        if minified_tokens and minified_tokens[0].type == 'WHITESPACE':
            minified_tokens.pop(0)
        if minified_tokens and minified_tokens[-1].type == 'WHITESPACE':
            minified_tokens.pop()
            
        return "".join(t.value for t in minified_tokens)

    def obfuscate(self, code: str, target_lang: str = "lua") -> str:
        lang_map = {
            "lua": "lua",
            "python": "python",
            "py": "python",
            "javascript": "javascript",
            "js": "javascript"
        }
        normalized_lang = lang_map.get(target_lang.lower())
        if not normalized_lang:
            raise ValueError(f"Unsupported target language: {target_lang}")

        words = set()
        for sentence in self.sentences:
            cleaned = re.sub(r'[^a-zA-Z0-9\s]', ' ', sentence)
            for word in cleaned.split():
                word = word.strip().lower()
                if word:
                    words.add(word)
        words_list = sorted(list(words))

        if normalized_lang == 'lua':
            tokens = self.tokenizer.tokenize(code)
            renamed_tokens = self._rename_local_variables(tokens, words_list)
            cleaned_code = self._minify_whitespace(renamed_tokens)
        elif normalized_lang == 'python':
            cleaned_code = self._minify_python(code)
        elif normalized_lang == 'javascript':
            cleaned_code = self._minify_javascript(code)

        source_bytes = cleaned_code.encode('utf-8')
        
        vocab = []
        seen = set()
        for sentence in self.sentences:
            s = sentence.strip()
            if s and s not in seen:
                seen.add(s)
                vocab.append(s)
        
        vocab = sorted(vocab)
        if not vocab:
            vocab = ["Default sentence fallback."]
            
        vocab_size = len(vocab)
        if vocab_size < 2:
            while len(vocab) < 2:
                vocab.append(f"Fallback sentence {len(vocab)}.")
            vocab_size = len(vocab)
            
        words_per_byte = math.ceil(math.log(256) / math.log(vocab_size))
        
        encoded_sentences = []
        for b in source_bytes:
            temp = b
            for _ in range(words_per_byte):
                digit = temp % vocab_size
                encoded_sentences.append(vocab[digit])
                temp //= vocab_size
                
        payload_str = "\n".join(encoded_sentences)
        
        vocab_json = json.dumps(vocab)
        payload_json = json.dumps(payload_str)
        
        vocab_lua = "{" + ",".join(json.dumps(s) for s in vocab) + "}"
        payload_lua = json.dumps(payload_str)
        
        bootstrap_vars = [
            'vocab', 'payload', 'lookup', 'bytes', 'vocab_len',
            'depth', 'byte_val', 'byte_idx', 'multiplier',
            'sentence', 'digit', 'loader', 'lines', 'i', 'j',
            'mult', 'word', 'code'
        ]
        assigned_names = set()
        bootstrap_mapping = {}
        sentences_pool = list(self.sentences)
        random.shuffle(sentences_pool)
        
        for var in bootstrap_vars:
            found = False
            for s in sentences_pool:
                ident = self._sentence_to_identifier(s)
                if ident and ident not in assigned_names and ident not in LUA_KEYWORDS:
                    assigned_names.add(ident)
                    bootstrap_mapping[var] = ident
                    found = True
                    break
            if not found:
                bootstrap_mapping[var] = f"_{var}"

        template_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            "templates",
            f"{normalized_lang}.template"
        )
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()

        replacements = {
            "vocab_lua": vocab_lua,
            "vocab_py": vocab_json,
            "vocab_js": vocab_json,
            "payload_lua": payload_lua,
            "payload_py": payload_json,
            "payload_js": payload_json,
            "words_per_byte": str(words_per_byte),
            "v_vocab": bootstrap_mapping['vocab'],
            "v_payload": bootstrap_mapping['payload'],
            "v_lookup": bootstrap_mapping['lookup'],
            "v_bytes": bootstrap_mapping['bytes'],
            "v_vocab_len": bootstrap_mapping['vocab_len'],
            "v_depth": bootstrap_mapping['depth'],
            "v_byte_val": bootstrap_mapping['byte_val'],
            "v_byte_idx": bootstrap_mapping['byte_idx'],
            "v_multiplier": bootstrap_mapping['multiplier'],
            "v_sentence": bootstrap_mapping['sentence'],
            "v_digit": bootstrap_mapping['digit'],
            "v_loader": bootstrap_mapping['loader'],
            "v_lines": bootstrap_mapping['lines'],
            "v_i": bootstrap_mapping['i'],
            "v_j": bootstrap_mapping['j'],
            "v_mult": bootstrap_mapping['mult'],
            "v_word": bootstrap_mapping['word'],
            "v_code": bootstrap_mapping['code'],
        }

        obfuscated_code = template_content
        for key, val in replacements.items():
            obfuscated_code = obfuscated_code.replace("{" + key + "}", val)

        return obfuscated_code
