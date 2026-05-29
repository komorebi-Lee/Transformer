"""Python 3.10 bytecode decompiler for recovering enhanced_coding_generator.py.

Uses the standard `dis` module (same Python version = reliable) to walk all
code objects in a .pyc and reconstruct equivalent Python source.

Usage:
    D:/anaconda3/envs/zthree5/python.exe decompile_pyc.py
"""

import dis
import io
import marshal
import os
import struct
import sys
import time
from types import CodeType
from typing import List, Tuple, Optional, Dict, Any


# ── helpers ──────────────────────────────────────────────────────────────

def load_pyc(path: str) -> CodeType:
    """Load a .pyc file (Python 3.10) and return the top-level code object."""
    with open(path, "rb") as fh:
        magic = fh.read(4)
        _flags = fh.read(4)  # PEP 552 flags
        if _flags == b"\x00\x00\x00\x00":
            # Timestamp-based
            _timestamp = struct.unpack("<I", fh.read(4))[0]
            _source_size = struct.unpack("<I", fh.read(4))[0]
        else:
            # Hash-based
            _hash = fh.read(8)
            _source_size = struct.unpack("<I", fh.read(4))[0]
        co = marshal.loads(fh.read())
    return co


# ── instruction helpers ──────────────────────────────────────────────────

def _get_instructions(co: CodeType) -> List[dis.Instruction]:
    """Get list of disassembled instructions."""
    return list(dis.get_instructions(co))


def _find_linestarts(co: CodeType) -> Dict[int, int]:
    """Map offset -> line number."""
    return dict(dis.findlinestarts(co))


def _is_cond_jump(opname: str) -> bool:
    return opname in (
        "POP_JUMP_IF_FALSE", "POP_JUMP_IF_TRUE",
        "JUMP_IF_FALSE_OR_POP", "JUMP_IF_TRUE_OR_POP",
        "JUMP_IF_NOT_EXC_MATCH",
    )


def _is_jump(opname: str) -> bool:
    return opname in (
        "JUMP_FORWARD", "JUMP_ABSOLUTE", "JUMP_BACKWARD",
    ) or _is_cond_jump(opname)


# ── constant formatting ──────────────────────────────────────────────────

def _fmt_const(val: Any) -> str:
    """Format a constant as Python source."""
    if val is None:
        return "None"
    if val is True:
        return "True"
    if val is False:
        return "False"
    if isinstance(val, str):
        # Use repr for strings
        return repr(val)
    if isinstance(val, (int, float)):
        return repr(val)
    if isinstance(val, bytes):
        return repr(val)
    if isinstance(val, tuple):
        items = ", ".join(_fmt_const(x) for x in val)
        if len(val) == 1:
            return f"({items},)"
        return f"({items})"
    if isinstance(val, frozenset):
        items = ", ".join(_fmt_const(x) for x in sorted(val, key=str))
        return "{" + items + "}"
    if isinstance(val, type):
        return val.__name__
    if isinstance(val, CodeType):
        return f"<code {val.co_name}>"
    return repr(val)


# ── name resolution ──────────────────────────────────────────────────────

def _resolve_name(namei: int, names: Tuple[str, ...]) -> str:
    if namei < len(names):
        return names[namei]
    return f"<name_{namei}>"


def _resolve_varname(vari: int, varnames: Tuple[str, ...]) -> str:
    if vari < len(varnames):
        return varnames[vari]
    return f"<var_{vari}>"


# ── main decompiler ──────────────────────────────────────────────────────

class Decompiler:
    """Reconstruct Python source from a code object."""

    def __init__(self, co: CodeType):
        self.co = co
        self.instructions = _get_instructions(co)
        self.linestarts = _find_linestarts(co)
        self.lines: Dict[int, List[str]] = {}  # line_no -> list of source fragments

    def _emit(self, line: int, code: str):
        if line is None:
            # Attach to last line
            if self.lines:
                last = max(self.lines.keys())
                self.lines[last].append(code)
            return
        if line not in self.lines:
            self.lines[line] = []
        self.lines[line].append(code)

    def _decompile_simple(self) -> str:
        """Simple line-by-line decompilation based on instruction patterns."""
        co = self.co
        instructions = self.instructions
        names = co.co_names
        varnames = co.co_varnames
        consts = co.co_consts
        cellvars = co.co_cellvars
        freevars = co.co_freevars

        # Indent level
        indent = 0
        output_lines: List[str] = []

        i = 0
        line_parts: Dict[int, List[str]] = {}
        current_line = co.co_firstlineno

        def emit(text: str, line: Optional[int] = None):
            nonlocal current_line
            l = line if line is not None else current_line
            if l not in line_parts:
                line_parts[l] = []
            line_parts[l].append(text)

        def current_indent() -> str:
            return "    " * indent

        while i < len(instructions):
            inst = instructions[i]
            if inst.starts_line:
                current_line = inst.starts_line
            op = inst.opname
            arg = inst.argval
            argr = inst.argrepr

            # ── LOAD_CONST ──
            if op == "LOAD_CONST":
                # This is typically part of a larger expression
                # We'll handle it in context of the next STORE/CALL/etc
                pass

            # ── STORE_FAST / STORE_NAME / STORE_ATTR ──
            elif op == "STORE_FAST":
                # Look backwards for what's being stored
                pass

            # For now, do a simpler pass: collect by line
            # Then for each line, try to build the statement

            i += 1

        # Fallback: use the instruction mnemonics to build a rough representation
        return self._decompile_rough()

    def _decompile_rough(self) -> str:
        """Rough decompilation: disassemble each method and convert to Python-like pseudo-code."""
        return self._decompile_method(self.co, 0)

    def _decompile_method(self, co: CodeType, depth: int) -> str:
        """Recursively decompile a code object and all nested ones."""
        names = co.co_names
        varnames = co.co_varnames
        consts = co.co_consts
        freevars = co.co_freevars
        cellvars = co.co_cellvars

        result = []

        # Header
        name = co.co_name
        if name == "<module>":
            pass  # module level
        elif name.startswith("<"):
            # lambda, genexpr, etc
            pass
        else:
            # Method/function
            args = list(varnames[:co.co_argcount])
            result.append(f"    def {name}({', '.join(args)}):")

        # Get instructions
        insts = list(dis.get_instructions(co))
        linemap = {}
        for inst in insts:
            if inst.starts_line:
                linemap[inst.offset] = inst.starts_line

        # Build statements by line
        stmts = self._build_statements(insts, co, linemap)

        for line_no, stmt in sorted(stmts):
            if name == "<module>" or name.startswith("<"):
                result.append(stmt)
            else:
                result.append(f"        {stmt}")

        # Handle nested code objects
        for const in consts:
            if isinstance(const, CodeType):
                nested = self._decompile_method(const, depth + 1)
                if nested:
                    result.append("")
                    result.append(nested)

        return "\n".join(result)

    def _build_statements(
        self, insts: List[dis.Instruction], co: CodeType, linemap: Dict[int, int]
    ) -> List[Tuple[int, str]]:
        """Build source statements from instructions."""
        names = co.co_names
        varnames = co.co_varnames
        consts = co.co_consts
        cellvars = co.co_cellvars
        freevars = co.co_freevars

        # Strategy: walk through instructions, keeping a stack of pending operations
        # For each line, accumulate until we hit something that terminates a statement

        stmts: List[Tuple[int, str]] = []
        i = 0
        n = len(insts)

        # Track pending LOAD operations for expression building
        pending_stack: List[str] = []

        def current_line() -> int:
            # Find the line for current instruction
            off = insts[i].offset
            while off >= 0:
                if off in linemap:
                    return linemap[off]
                off -= 2
            return co.co_firstlineno

        def peek_stack(n: int = 1) -> Optional[str]:
            if len(pending_stack) >= n:
                return pending_stack[-n]
            return None

        def pop_stack() -> str:
            if pending_stack:
                return pending_stack.pop()
            return "<?>"

        def push_stack(val: str):
            pending_stack.append(val)

        def flush_stmt():
            """Flush accumulated operations into a statement."""
            nonlocal pending_stack
            if not pending_stack:
                return
            line = current_line()
            # Simple case: single item on stack
            if len(pending_stack) == 1:
                stmts.append((line, pending_stack[0]))
            else:
                # Build expression from stack
                expr = " ; ".join(pending_stack)
                stmts.append((line, expr))
            pending_stack = []

        while i < n:
            inst = insts[i]
            op = inst.opname
            arg = inst.arg  # raw arg int
            argval = inst.argval
            line = current_line()

            # ── LOAD operations ──
            if op == "LOAD_CONST":
                push_stack(_fmt_const(argval))

            elif op == "LOAD_FAST":
                push_stack(_resolve_varname(arg, varnames))

            elif op == "LOAD_ATTR":
                obj = pop_stack()
                push_stack(f"{obj}.{_resolve_name(arg, names)}")

            elif op == "LOAD_GLOBAL":
                push_stack(_resolve_name(arg, names))

            elif op == "LOAD_METHOD":
                obj = pop_stack()
                push_stack(f"{obj}.{_resolve_name(arg, names)}")

            elif op == "LOAD_DEREF":
                if arg < len(cellvars):
                    push_stack(cellvars[arg])
                elif arg - len(cellvars) < len(freevars):
                    push_stack(freevars[arg - len(cellvars)])
                else:
                    push_stack(f"<deref_{arg}>")

            elif op == "LOAD_CLOSURE":
                if arg < len(cellvars):
                    push_stack(cellvars[arg])
                else:
                    push_stack(f"<closure_{arg}>")

            # ── CALL operations ──
            elif op == "CALL_FUNCTION":
                nargs = arg
                args = []
                for _ in range(nargs):
                    args.insert(0, pop_stack())
                func = pop_stack()
                push_stack(f"{func}({', '.join(args)})")

            elif op == "CALL_METHOD":
                nargs = arg
                args = []
                for _ in range(nargs):
                    args.insert(0, pop_stack())
                method = pop_stack()
                push_stack(f"{method}({', '.join(args)})")

            elif op == "CALL_FUNCTION_KW":
                nargs = arg
                # KW args: one of the consts is a tuple of kw names
                # The top of stack is the kw names tuple
                kw_names = pop_stack()
                args = []
                for _ in range(nargs):
                    args.insert(0, pop_stack())
                func = pop_stack()
                if kw_names:
                    # Build keyword args
                    kw_count = len(kw_names) if isinstance(kw_names, tuple) else 0
                    pos_args = args[:nargs - kw_count] if kw_count else args
                    kw_args = []
                    if kw_count:
                        for j in range(kw_count):
                            kw_args.append(f"{kw_names[j]}={args[nargs - kw_count + j]}")
                    all_args = pos_args + kw_args
                    push_stack(f"{func}({', '.join(all_args)})")
                else:
                    push_stack(f"{func}({', '.join(args)})")

            # ── STORE operations (complete statements) ──
            elif op == "STORE_FAST":
                val = pop_stack()
                var = _resolve_varname(arg, varnames)
                stmts.append((line, f"{var} = {val}"))

            elif op == "STORE_NAME":
                val = pop_stack()
                stmts.append((line, f"{_resolve_name(arg, names)} = {val}"))

            elif op == "STORE_ATTR":
                val = pop_stack()
                obj = pop_stack()
                stmts.append((line, f"{obj}.{_resolve_name(arg, names)} = {val}"))

            elif op == "STORE_DEREF":
                val = pop_stack()
                if arg < len(cellvars):
                    stmts.append((line, f"{cellvars[arg]} = {val}"))
                else:
                    stmts.append((line, f"<deref_{arg}> = {val}"))

            # ── RETURN ──
            elif op == "RETURN_VALUE":
                val = pop_stack() if pending_stack else "None"
                if val != "None":
                    stmts.append((line, f"return {val}"))
                flush_stmt()  # clean up

            # ── IMPORT operations ──
            elif op == "IMPORT_NAME":
                # Usually: LOAD_CONST(level) LOAD_CONST(None) IMPORT_NAME name
                level = pop_stack()
                _fromlist = pop_stack()  # None or tuple
                push_stack(_resolve_name(arg, names))

            elif op == "IMPORT_FROM":
                mod = peek_stack()
                name = _resolve_name(arg, names)
                stmts.append((line, f"from {mod} import {name}"))

            elif op == "IMPORT_STAR":
                mod = pop_stack()
                stmts.append((line, f"from {mod} import *"))

            # ── POP / DISCARD ──
            elif op == "POP_TOP":
                if pending_stack:
                    expr = pop_stack()
                    if expr and expr != "None":
                        stmts.append((line, expr))
                flush_stmt()

            elif op == "POP_JUMP_IF_FALSE":
                cond = pop_stack()
                stmts.append((line, f"if not {cond}: goto {argval}"))

            elif op == "POP_JUMP_IF_TRUE":
                cond = pop_stack()
                stmts.append((line, f"if {cond}: goto {argval}"))

            elif op == "JUMP_IF_TRUE_OR_POP":
                cond = peek_stack()
                stmts.append((line, f"if {cond}: goto {argval}"))

            elif op == "JUMP_IF_FALSE_OR_POP":
                cond = peek_stack()
                stmts.append((line, f"if not {cond}: goto {argval}"))

            # ── UNARY / BINARY / COMPARE ──
            elif op == "UNARY_NOT":
                val = pop_stack()
                push_stack(f"not {val}")

            elif op == "UNARY_NEGATIVE":
                val = pop_stack()
                push_stack(f"-{val}")

            elif op == "BINARY_ADD":
                right = pop_stack()
                left = pop_stack()
                push_stack(f"({left} + {right})")

            elif op == "BINARY_SUBTRACT":
                right = pop_stack()
                left = pop_stack()
                push_stack(f"({left} - {right})")

            elif op == "BINARY_MULTIPLY":
                right = pop_stack()
                left = pop_stack()
                push_stack(f"({left} * {right})")

            elif op == "BINARY_TRUE_DIVIDE":
                right = pop_stack()
                left = pop_stack()
                push_stack(f"({left} / {right})")

            elif op == "BINARY_MODULO":
                right = pop_stack()
                left = pop_stack()
                push_stack(f"({left} % {right})")

            elif op == "BINARY_SUBSCR":
                idx = pop_stack()
                obj = pop_stack()
                push_stack(f"{obj}[{idx}]")

            elif op == "STORE_SUBSCR":
                val = pop_stack()
                idx = pop_stack()
                obj = pop_stack()
                stmts.append((line, f"{obj}[{idx}] = {val}"))

            elif op == "COMPARE_OP":
                right = pop_stack()
                left = pop_stack()
                cmp_op = argval  # e.g., '==', '>', '<', '>=', '<=', '!=', 'in', 'not in', 'is', 'is not'
                push_stack(f"({left} {cmp_op} {right})")

            elif op == "IS_OP":
                right = pop_stack()
                left = pop_stack()
                if arg:
                    push_stack(f"({left} is not {right})")
                else:
                    push_stack(f"({left} is {right})")

            elif op == "CONTAINS_OP":
                right = pop_stack()
                left = pop_stack()
                if arg:
                    push_stack(f"({left} not in {right})")
                else:
                    push_stack(f"({left} in {right})")

            # ── BUILD operations ──
            elif op == "BUILD_LIST":
                items = []
                for _ in range(arg):
                    items.insert(0, pop_stack())
                push_stack(f"[{', '.join(items)}]")

            elif op == "BUILD_TUPLE":
                items = []
                for _ in range(arg):
                    items.insert(0, pop_stack())
                push_stack(f"({', '.join(items)})")

            elif op == "BUILD_SET":
                items = []
                for _ in range(arg):
                    items.insert(0, pop_stack())
                push_stack("{" + ", ".join(items) + "}")

            elif op == "BUILD_MAP":
                push_stack("{}")

            elif op == "BUILD_STRING":
                parts = []
                for _ in range(arg):
                    parts.insert(0, pop_stack())
                push_stack(" + ".join(parts))

            elif op == "BUILD_CONST_KEY_MAP":
                keys = pop_stack()  # tuple of keys
                nkeys = len(keys) if isinstance(keys, tuple) else arg
                vals = []
                for _ in range(nkeys):
                    vals.insert(0, pop_stack())
                pairs = []
                if isinstance(keys, tuple):
                    for k, v in zip(keys, vals):
                        pairs.append(f"{_fmt_const(k)}: {v}")
                push_stack("{" + ", ".join(pairs) + "}")

            # ── DICT / LIST / SET / TUPLE operations ──
            elif op == "LIST_APPEND":
                val = pop_stack()
                # The list is lower on stack - handle in context
                push_stack(val)  # put it back, will be handled by BUILD_LIST

            elif op == "SET_ADD":
                val = pop_stack()
                push_stack(val)

            elif op == "MAP_ADD":
                val = pop_stack()
                key = pop_stack()
                # Dict building
                push_stack(f"{key}: {val}")

            elif op == "DICT_UPDATE":
                val = pop_stack()
                push_stack(val)

            elif op == "DICT_MERGE":
                right = pop_stack()
                left = pop_stack()
                push_stack(f"{{**{left}, **{right}}}")

            # ── SLICE ──
            elif op == "BUILD_SLICE":
                step = None
                if arg == 3:
                    step = pop_stack()
                stop = pop_stack()
                start = pop_stack()
                if step:
                    push_stack(f"slice({start}, {stop}, {step})")
                else:
                    push_stack(f"slice({start}, {stop})")

            # ── FORMAT ──
            elif op == "FORMAT_VALUE":
                val = pop_stack()
                if arg == 0:
                    push_stack(f"str({val})")
                elif arg == 1:
                    push_stack(f"repr({val})")
                elif arg == 2:
                    push_stack(f"ascii({val})")
                else:
                    push_stack(f"format({val})")

            # ── UNPACK ──
            elif op == "UNPACK_SEQUENCE":
                # Will be handled by the consumer
                push_stack(f"<unpack_{arg}>")

            elif op == "UNPACK_EX":
                push_stack(f"<unpackex_{arg}>")

            # ── LIST/SET/DICT comprehensions ──
            elif op == "GET_ITER":
                obj = pop_stack()
                push_stack(f"iter({obj})")

            elif op == "FOR_ITER":
                # The iterator is on TOS
                stmts.append((line, f"# for loop (goto {argval} on exhaustion)"))

            elif op == "GET_YIELD_FROM_ITER":
                push_stack(f"<yield_from_iter>")

            elif op == "YIELD_VALUE":
                val = pop_stack()
                stmts.append((line, f"yield {val}"))

            elif op == "YIELD_FROM":
                val = pop_stack()
                stmts.append((line, f"yield from {val}"))

            # ── Exception handling ──
            elif op == "SETUP_FINALLY":
                stmts.append((line, f"# try:"))

            elif op == "POP_BLOCK":
                pass

            elif op == "POP_EXCEPT":
                stmts.append((line, f"# except"))

            elif op == "RERAISE":
                stmts.append((line, "raise"))

            elif op == "RAISE_VARARGS":
                if arg == 0:
                    stmts.append((line, "raise"))
                elif arg == 1:
                    val = pop_stack()
                    stmts.append((line, f"raise {val}"))
                elif arg == 2:
                    tb = pop_stack()
                    val = pop_stack()
                    stmts.append((line, f"raise {val} from {tb}"))

            elif op == "DUP_TOP":
                if pending_stack:
                    push_stack(peek_stack())

            # ── Others ──
            elif op == "EXTENDED_ARG":
                pass  # handled implicitly by dis

            elif op == "NOP":
                pass

            elif op == "MAKE_FUNCTION":
                # TOS = qualified name, TOS1 = code object
                qualname = pop_stack()
                code_obj = pop_stack()
                push_stack(f"<function {qualname}>")

            elif op == "LOAD_CLASSDEREF":
                push_stack(f"<classderef_{arg}>")

            elif op == "SETUP_ANNOTATIONS":
                pass

            elif op == "DELETE_FAST":
                var = _resolve_varname(arg, varnames)
                stmts.append((line, f"del {var}"))
                pending_stack = []

            elif op == "COPY_DICT_WITHOUT_KEYS":
                keys = pop_stack()
                d = pop_stack()
                push_stack(f"{{k: v for k, v in {d}.items() if k not in {keys}}}")

            elif op == "GEN_START":
                push_stack("<generator>")

            elif op == "ROT_TWO":
                if len(pending_stack) >= 2:
                    a = pending_stack.pop()
                    b = pending_stack.pop()
                    pending_stack.append(a)
                    pending_stack.append(b)

            elif op == "ROT_THREE":
                if len(pending_stack) >= 3:
                    a = pending_stack.pop()
                    b = pending_stack.pop()
                    c = pending_stack.pop()
                    pending_stack.append(a)
                    pending_stack.append(c)
                    pending_stack.append(b)

            elif op == "PUSH_NULL":
                push_stack("<NULL>")

            elif op == "PRECALL":
                pass  # Pre-call marker in 3.11+, might appear in 3.10

            else:
                # Unknown opcode
                stmts.append((line, f"# ??? {op} {argval}"))
                flush_stmt()

            i += 1

        flush_stmt()
        return stmts


# ── main ─────────────────────────────────────────────────────────────────

def decompile_pyc(pyc_path: str, output_path: str):
    """Main entry point."""
    print(f"Loading: {pyc_path}")
    co = load_pyc(pyc_path)
    print(f"Module: {co.co_name}")
    print(f"Names: {len(co.co_names)}, Constants: {len(co.co_consts)}")

    d = Decompiler(co)
    source = d._decompile_rough()

    # For now, also do a full raw dump
    full_dump = _full_dump(co)

    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(full_dump)
    print(f"Written: {output_path} ({len(full_dump)} chars)")

    # Also save the rough decompile
    rough_path = output_path.replace(".py", "_rough.py")
    with open(rough_path, "w", encoding="utf-8") as fh:
        fh.write(source)
    print(f"Rough: {rough_path} ({len(source)} chars)")


def _full_dump(co: CodeType) -> str:
    """Produce a complete source dump using instruction-by-instruction reconstruction."""
    output: List[str] = []

    def dump_code(code: CodeType, indent: int = 0, is_class: bool = False) -> str:
        prefix = "    " * indent
        name = code.co_name
        names = code.co_names
        varnames = code.co_varnames
        consts = code.co_consts
        cellvars = code.co_cellvars
        freevars = code.co_freevars

        lines: List[str] = []

        # Function/method definition
        if name == "<module>":
            pass
        elif name == "<lambda>":
            pass
        elif name.startswith("<"):
            # genexpr, listcomp, dictcomp, setcomp
            lines.append(f"{prefix}# {name}")
        elif is_class:
            lines.append(f"{prefix}class {name}:")
        else:
            args = ", ".join(varnames[:code.co_argcount])
            lines.append(f"{prefix}def {name}({args}):")

        # Get instructions
        insts = list(dis.get_instructions(code))

        # Group instructions by source line
        # Build a line-number map
        linemap = {}
        for inst in insts:
            if inst.starts_line:
                linemap[inst.offset] = inst.starts_line

        # Build a stack-based decompiler for this code object
        decomp = Decompiler(code)
        stmts = decomp._build_statements(insts, code, linemap)

        inner_prefix = prefix + "    "
        for _, stmt in stmts:
            lines.append(f"{inner_prefix}{stmt}")

        # Handle nested code objects
        if name != "<lambda>" and not name.startswith("<"):
            for const in consts:
                if isinstance(const, CodeType):
                    if const.co_name.startswith("<"):
                        # lambda, genexpr, etc - inline
                        nested_src = dump_code(const, indent + 2, False)
                        lines.append(nested_src)
                    else:
                        lines.append("")
                        nested_src = dump_code(const, indent + 1, False)
                        lines.append(nested_src)

        return "\n".join(lines)

    # Find class
    class_co = None
    for const in co.co_consts:
        if isinstance(const, CodeType) and const.co_name == "EnhancedCodingGenerator":
            class_co = const
            break

    # Module header
    output.append("# Recovered from enhanced_coding_generator.cpython-310.pyc")
    output.append(f"# Decompiled at: {time.ctime()}")
    output.append("")

    if class_co:
        # Dump module-level code first
        module_src = dump_code(co, 0)
        output.append(module_src)
        output.append("")

        # Dump class
        class_src = dump_code(class_co, 0, is_class=True)
        output.append(class_src)

    return "\n".join(output)


if __name__ == "__main__":
    pyc_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "__pycache__", "enhanced_coding_generator.cpython-310.pyc",
    )
    output_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "enhanced_coding_generator_recovered.py",
    )
    if not os.path.exists(pyc_path):
        print(f"ERROR: {pyc_path} not found")
        sys.exit(1)
    decompile_pyc(pyc_path, output_path)
