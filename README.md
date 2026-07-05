# Adversarial Semantic Obfuscator

A tool to obfuscate Lua, Python, and JavaScript source code by encoding it into sentences. Using a lexicon of policy-violating phrases triggers adversarial LLM safety refusals, blocking automated deobfuscation.

---

## How It Works

1. **Minification:** Strips comments and whitespace. (Lua also renames variables).
2. **Encoding:** Converts source bytes into sentences from `lexicon.txt` via base-N encoding.
3. **Bootstrapping:** Embeds the payload in a language-specific decoder wrapper with lexicon-obfuscated variable names.

---

## Adversarial Safety Triggering

Using sensitive terms (e.g., CBRN, explosives) in your lexicon causes LLMs (Claude, GPT, Gemini) to refuse to analyze or deobfuscate the script due to safety alignment guardrails.

> [!IMPORTANT]
> To comply with GitHub Terms of Service, the default `lexicon.txt` contains only harmless sentences. To trigger adversarial refusals, you must populate your own `lexicon.txt` locally with safety-triggering phrases.

| Claude Refusal | Gemini Refusal |
| --- | --- |
| ![Claude Refusal](assets/claude.png) | ![Gemini Refusal](assets/gemini.png) |

---

## Usage

Language is auto-detected from the file extension (`.lua`, `.py`, `.js`), but can be overridden with `-t` / `--lang`.

> *Customize the lexicon.txt file to trigger adversarial refusals.*

```bash
# Auto-detect language (e.g., Python)
python obfuscator.py input.py -o output.py

# Manually specify target language (e.g., JavaScript)
python obfuscator.py input.txt -o output.js -t js

# Run tests
python obfuscator.py --test
```
