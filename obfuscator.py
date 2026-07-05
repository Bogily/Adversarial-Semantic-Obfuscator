#!/usr/bin/env python3
"""
Semantic Natural Language Obfuscator CLI
"""

import argparse
import logging
import os
import sys

from src.engine import ObfuscatorEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SemanticObfuscator")

def main():
    parser = argparse.ArgumentParser(description="Obfuscate source code using flat lexicon sentences.")
    parser.add_argument("input", nargs="?", help="Path to input source script")
    parser.add_argument("-o", "--output", help="Path to write obfuscated script")
    parser.add_argument("-l", "--lexicon", default="lexicon.txt", help="Path to lexicon.txt")
    parser.add_argument("-t", "--lang", help="Target language (lua, python, javascript). Autodetected if not specified.")
    parser.add_argument("--test", action="store_true", help="Run internal self-tests")
    
    args = parser.parse_args()

    if args.test:
        import unittest
        from src.test_suite import TestSemanticObfuscator
        suite = unittest.TestLoader().loadTestsFromTestCase(TestSemanticObfuscator)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        sys.exit(0 if result.wasSuccessful() else 1)

    if not args.input or not args.output:
        parser.print_usage()
        logger.error("the following arguments are required: input, -o/--output")
        sys.exit(1)

    if not os.path.exists(args.lexicon):
        logger.error(f"Lexicon not found: {args.lexicon}")
        sys.exit(1)

    try:
        with open(args.lexicon, 'r', encoding='utf-8') as f:
            sentences = [line.strip() for line in f if line.strip()]
    except Exception as e:
        logger.error(f"Failed to read lexicon: {e}")
        sys.exit(1)

    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            source_code = f.read()
    except Exception as e:
        logger.error(f"Failed to read input file: {e}")
        sys.exit(1)

    lang = args.lang
    if not lang:
        _, ext = os.path.splitext(args.input)
        ext = ext.lower()
        if ext == '.py':
            lang = 'python'
        elif ext in ('.js', '.mjs', '.cjs'):
            lang = 'javascript'
        elif ext == '.lua':
            lang = 'lua'
        else:
            lang = 'lua'
            logger.info(f"Unknown extension '{ext}', defaulting to target language: lua")

    logger.info(f"Target language: {lang}")
    engine = ObfuscatorEngine(sentences)
    
    try:
        obfuscated_code = engine.obfuscate(source_code, target_lang=lang)
    except Exception as e:
        logger.error(f"Obfuscation failed: {e}")
        sys.exit(1)

    try:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(obfuscated_code)
        logger.info(f"Obfuscated {lang} code written successfully.")
    except Exception as e:
        logger.error(f"Failed to write output: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
