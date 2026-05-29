"""Post-process the rough decompiled output to fix systematic errors.

Applies a series of regex-based fixes to convert the rough decompiled code
into closer-to-valid Python.

Usage:
    D:/anaconda3/envs/zthree5/python.exe fix_decompiled.py
"""

import re
import sys


def fix_goto_if_blocks(lines: list) -> list:
    """Convert 'if cond: goto N' patterns into proper if/else blocks."""
    # This is complex - for now, convert the goto comments to more readable forms
    result = []
    for line in lines:
        # Fix: 'if not cond: goto N' -> keep as comment for now
        # The actual control flow reconstruction would need a CFG
        result.append(line)
    return result


def fix_method_calls(lines: list) -> list:
    """Fix LOAD_METHOD/CALL_METHOD mismatches.

    Pattern: obj('arg').method → should be obj.method
    Pattern: <?>.method → clean up
    """
    result = []
    for line in lines:
        # Fix: func = module after IMPORT_NAME pattern
        # "Config = config" -> remove (wrong import)
        if re.match(r'^\s*(Config|CodingLibraryManager|SemanticMatcher|logging|jieba|numpy|re|Counter|defaultdict)\s*=\s*\1\s*$', line):
            continue

        # Fix: variable = <?>  ->  variable = None
        line = re.sub(r'=\s*<\?>', '= None', line)

        # Fix: standalone '<?.something' patterns
        line = re.sub(r'<\?>\.', '', line)

        # Fix: 'obj.method = self' (wrong attr order from KW call)
        line = re.sub(r'\.concept_anchor_index = self', '', line)

        # Fix: function tuples on stack
        # Patterns like "('value', str) ; ('seen', self, variants)"
        if re.match(r"^\s*\(['\"]", line) and ';' in line:
            continue  # Skip these stack-artifact lines

        # Remove trailing semicolons from stack-artifact lines
        if re.match(r"^\s*\(.*\).*;\s*\(.*\)\s*$", line):
            continue

        result.append(line)
    return result


def fix_imports(lines: list) -> list:
    """Fix import statements."""
    result = []
    seen_imports = set()

    # Known imports from bytecode analysis
    known_imports = [
        "import logging",
        "import numpy as np",
        "from typing import Dict, List, Any, Optional, Callable, Set, Tuple",
        "import re",
        "import jieba",
        "from jieba.posseg import pseg",
        "from collections import Counter, defaultdict",
    ]

    for line in lines:
        # Remove garbled import results
        if re.match(r"^\s*(logging|np|jieba|re|Config|Counter|defaultdict|Dict|List|Any|Optional|Callable|Set|Tuple|pseg)\s*=\s*(<\?>|\1)\s*$", line):
            continue

        # Fix: standalone variable names from failed LOAD_NAME
        if re.match(r"^\s*e = None\s*$", line) and "except" not in result[-2] if len(result) >= 2 else False:
            continue

        # Skip lines that are just a single identifier (stack remnants)
        if re.match(r"^\s*[a-zA-Z_][\w.]*\s*$", line):
            if not any(kw in line for kw in ['import', 'return', 'raise', 'pass', 'break', 'continue']):
                # Check if it's a known module or class name used as a remnant
                if line.strip() in ('Exception', 'e', 'dict', 'str', 'int', 'float', 'bool', 'list',
                                     'set', 'tuple', 'type', 'os', 'Config', 'CodingLibraryManager',
                                     'SemanticMatcher'):
                    continue

        result.append(line)

    # Replace initial import section with clean imports
    # Find where the class definition starts
    class_idx = None
    for i, line in enumerate(result):
        if re.match(r'^\s*class\s+EnhancedCodingGenerator', line):
            class_idx = i
            break

    if class_idx:
        # Replace everything before the class with clean imports + logger
        clean_header = [
            "# Recovered and cleaned from bytecode",
            "# Auto-generated - may need manual fixes",
            "",
            "import logging",
            "import numpy as np",
            "from typing import Dict, List, Any, Optional, Callable, Set, Tuple",
            "import re",
            "import jieba",
            "from jieba.posseg import pseg",
            "from collections import Counter, defaultdict",
            "import os",
            "",
            "logger = logging.getLogger(__name__)",
            "",
            "# Optional imports - may fail gracefully",
            "try:",
            "    from config import Config",
            "except Exception:",
            "    Config = None  # type: ignore",
            "",
            "try:",
            "    from coding_library_manager import CodingLibraryManager",
            "except Exception as e:",
            "    logger.warning('导入CodingLibraryManager失败: ' + str(e))",
            "    CodingLibraryManager = None  # type: ignore",
            "",
            "try:",
            "    from semantic_matcher import SemanticMatcher",
            "except Exception as e:",
            "    logger.warning('导入SemanticMatcher失败: ' + str(e))",
            "    SemanticMatcher = None  # type: ignore",
            "",
            "try:",
            "    from quality_learner import HighQualitySampleLearner",
            "except Exception as e:",
            "    logger.warning('导入HighQualitySampleLearner失败: ' + str(e))",
            "    HighQualitySampleLearner = None  # type: ignore",
            "",
            "",
        ]
        result = clean_header + result[class_idx:]

    return result


def fix_expressions(lines: list) -> list:
    """Fix malformed expressions."""
    result = []
    for line in lines:
        # Fix: "obj = ''.strip()" -> "obj = ''.strip()" (already OK)
        # Fix: "code('').strip()" -> "code.strip()"
        # This is from LOAD_FAST code, LOAD_CONST '', LOAD_ATTR strip
        # Actually in bytecode: LOAD_FAST code, LOAD_CONST '', BUILD_STRING, LOAD_ATTR strip
        # This means: ((code) + ('')) . strip  →  code.strip()
        line = re.sub(r"(\w+)\(''\)\.(\w+)", r"\1.\2", line)
        line = re.sub(r"(\w+)\(''\)\s*=\s*", r"\1 = ", line)

        # Fix: "sentence_part.get('text', '')('')" → "sentence_part.get('text', '')"
        # This is from redundant BUILD_STRING
        # Pattern: dict.get(k, d)('')  means the parens were artifacts
        line = re.sub(r"(\.get\([^)]+\))\(''\)", r"\1", line)

        # Skip lines that are just a string literal (docstring artifacts)
        if re.match(r"^\s*['\"]", line) and not any(kw in line for kw in ['import', 'return', '=', '(']):
            # Keep docstrings
            if not re.match(r"^\s*['\"]{3}", line):
                continue

        # Fix: standalone "str" lines
        if line.strip() == 'str':
            continue

        # Fix: "(\w+, \w+)" as a standalone expression (tuple remnant)
        if re.match(r"^\s*\(\w+(,\s*\w+)*\)\s*$", line):
            continue

        # Fix: "(key, value) ; (key2, value2)" remnants
        if re.match(r"^\s*\(.*\);.*\(.*\)", line):
            continue

        result.append(line)
    return result


def fix_control_flow(lines: list) -> list:
    """Improve readability of control flow annotations."""
    result = []
    for line in lines:
        # Convert goto comments to be more informative
        if '# goto' in line and 'if' in line and 'goto' in line:
            # Keep the if condition but mark as needing fix
            line = re.sub(r'# goto \d+', '# FIXME: control flow', line)

        # Clean up redundant markers
        line = re.sub(r'# \?\?\? .*', '# FIXME: needs manual fix', line)
        line = re.sub(r'# for loop.*goto (\d+) on exhaustion', r'# FIXME: for loop', line)

        result.append(line)
    return result


def fix_docstrings(lines: list) -> list:
    """Fix docstring handling."""
    result = []
    for line in lines:
        # Broken multiline docstrings from decompilation
        # Many garbled Chinese strings are actually docstrings
        if re.match(r"^\s*'\\\\[n].*����.*'\s*$", line):
            line = re.sub(r"'\\\\[n](.*)'", r'"""\1"""', line)
        result.append(line)
    return result


def main():
    input_file = "enhanced_coding_generator_recovered.py"
    output_file = "enhanced_coding_generator_cleaned.py"

    with open(input_file, "r", encoding="utf-8") as fh:
        content = fh.read()

    lines = content.split("\n")
    print(f"Input: {len(lines)} lines")

    # Apply fixes
    lines = fix_imports(lines)
    lines = fix_method_calls(lines)
    lines = fix_expressions(lines)
    lines = fix_control_flow(lines)
    lines = fix_docstrings(lines)

    # Remove consecutive blank lines
    cleaned = []
    prev_blank = False
    for line in lines:
        if line.strip() == "":
            if not prev_blank:
                cleaned.append(line)
            prev_blank = True
        else:
            cleaned.append(line)
            prev_blank = False

    output = "\n".join(cleaned)

    with open(output_file, "w", encoding="utf-8") as fh:
        fh.write(output)

    print(f"Output: {len(cleaned)} lines")
    print(f"Written to: {output_file}")


if __name__ == "__main__":
    main()
