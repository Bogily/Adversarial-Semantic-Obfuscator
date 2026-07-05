import re
import unittest
import json
import math
from src.tokenizer import LuaTokenizer
from src.engine import ObfuscatorEngine

TEST_SENTENCES = [
    "The quick brown fox jumps over the lazy dog.",
    "Artificial intelligence is shaping the future of technology.",
    "A journey of a thousand miles begins with a single step.",
    "Exploring the depths of the ocean reveals hidden wonders."
]

class TestSemanticObfuscator(unittest.TestCase):
    def setUp(self):
        self.tokenizer = LuaTokenizer()
        self.engine = ObfuscatorEngine(TEST_SENTENCES)

    def test_tokenizer_roundtrip(self):
        source_code = """
        local x = 10
        -- comment
        local y = "hello \\"world\\""
        local long_str = [[
            multi line string
            with another [=[ nested ]=] lookalike
        ]]
        function test(a)
            return a * 2
        end
        """
        tokens = self.tokenizer.tokenize(source_code)
        reassembled = "".join(t.value for t in tokens)
        self.assertEqual(source_code, reassembled)

    def test_token_types(self):
        source = 'local my_var = "string" -- comment\nlocal num = 0xDEADBEEF'
        tokens = self.tokenizer.tokenize(source)
        
        types = [t.type for t in tokens if t.type != 'WHITESPACE']
        expected_types = [
            'KEYWORD', 'IDENTIFIER', 'OP_ONE', 'DQ_STRING', 'SL_COMMENT',
            'KEYWORD', 'IDENTIFIER', 'OP_ONE', 'NUMBER'
        ]
        self.assertEqual(types, expected_types)

    def test_lua_obfuscation_structure(self):
        source = """
        local hostname = "api.internal.network"
        local retries = 5
        print("Connecting to " .. hostname)
        """
        obfuscated = self.engine.obfuscate(source, target_lang="lua")
        
        self.assertNotIn("api.internal.network", obfuscated)
        self.assertNotIn("Connecting to", obfuscated)

    def test_lua_obfuscation_roundtrip(self):
        source = 'local x = 10 -- comment\nprint("hello")'
        obfuscated = self.engine.obfuscate(source, target_lang="lua")
        
        lines = obfuscated.splitlines()
        v_line = lines[0]
        p_line = lines[1]
        k_line = lines[8]
        
        vocab = json.loads(v_line.split("=", 1)[1].strip().replace('{', '[').replace('}', ']'))
        payload_str = json.loads(p_line.split("=", 1)[1].strip())
        payload = payload_str.split("\n")
        depth = int(k_line.split("=", 1)[1].strip())
        vocab_len = len(vocab)
        
        lookup = {vocab[i]: i for i in range(vocab_len)}
        
        decoded_bytes = bytearray()
        for i in range(0, len(payload), depth):
            val = 0
            mult = 1
            for j in range(depth):
                word = payload[i + j]
                digit = lookup[word]
                val += digit * mult
                mult *= vocab_len
            decoded_bytes.append(val)
            
        decoded_str = decoded_bytes.decode('utf-8')
        
        self.assertNotIn("x", decoded_str.split())
        self.assertIn("local", decoded_str)
        self.assertIn("print(\"hello\")", decoded_str)

    def test_lua_table_key_preservation(self):
        source = """
        local x = 10
        local tbl = { x = 20 }
        return tbl.x
        """
        obfuscated = self.engine.obfuscate(source, target_lang="lua")
        
        lines = obfuscated.splitlines()
        v_line = lines[0]
        p_line = lines[1]
        k_line = lines[8]
        
        vocab = json.loads(v_line.split("=", 1)[1].strip().replace('{', '[').replace('}', ']'))
        payload_str = json.loads(p_line.split("=", 1)[1].strip())
        payload = payload_str.split("\n")
        depth = int(k_line.split("=", 1)[1].strip())
        vocab_len = len(vocab)
        
        lookup = {vocab[i]: i for i in range(vocab_len)}
        
        decoded_bytes = bytearray()
        for i in range(0, len(payload), depth):
            val = 0
            mult = 1
            for j in range(depth):
                word = payload[i + j]
                digit = lookup[word]
                val += digit * mult
                mult *= vocab_len
            decoded_bytes.append(val)
            
        decoded_str = decoded_bytes.decode('utf-8')
        
        self.assertIn("x = 20", decoded_str)
        self.assertTrue(any(part.endswith(".x") for part in decoded_str.split()))
        self.assertNotIn("local x = 10", decoded_str)

    def test_python_obfuscation_roundtrip(self):
        source = "# some test comment\nval = 100 + 20\n"
        obfuscated = self.engine.obfuscate(source, target_lang="python")
        
        scope = {}
        exec(obfuscated, {}, scope)
        self.assertEqual(scope.get("val"), 120)

    def test_javascript_obfuscation_roundtrip(self):
        source = "// JS comment\nlet a = 12;\n/* multi-line comment */\nconsole.log(a);\n"
        obfuscated = self.engine.obfuscate(source, target_lang="javascript")
        
        vocab_match = re.search(r'const\s+\w+\s*=\s*(\[.*?\])\s*;', obfuscated)
        payload_match = re.search(r'const\s+\w+\s*=\s*("(?:[^"\\]|\\.)*")\s*;', obfuscated)
        
        self.assertIsNotNone(vocab_match)
        self.assertIsNotNone(payload_match)
        
        vocab = json.loads(vocab_match.group(1))
        payload_str = json.loads(payload_match.group(1))
        payload = payload_str.split("\n")
        
        vocab_len = len(vocab)
        depth = math.ceil(math.log(256) / math.log(vocab_len))
        
        lookup = {vocab[i]: i for i in range(vocab_len)}
        
        decoded_bytes = bytearray()
        for i in range(0, len(payload), depth):
            val = 0
            mult = 1
            for j in range(depth):
                word = payload[i + j]
                digit = lookup[word]
                val += digit * mult
                mult *= vocab_len
            decoded_bytes.append(val)
            
        decoded_str = decoded_bytes.decode('utf-8')
        
        self.assertIn("let a = 12;", decoded_str)
        self.assertIn("console.log(a);", decoded_str)
        self.assertNotIn("JS comment", decoded_str)
        self.assertNotIn("multi-line comment", decoded_str)
