"""Improved Python 3.10 bytecode decompiler v2.

Key improvements over v1:
1. Proper stack management for LOAD_METHOD → CALL_METHOD chains
2. Better LOAD_ATTR → attribute resolution
3. Import statement reconstruction
4. String building
5. Control flow detection (basic)

Usage:
    D:/anaconda3/envs/zthree5/python.exe decompile_pyc_v2.py
"""

import dis
import io
import marshal
import os
import struct
import sys
import time
from types import CodeType
from typing import List, Tuple, Optional, Dict, Any, Set


# ── helpers ──────────────────────────────────────────────────────────────

def load_pyc(path: str) -> CodeType:
    with open(path, "rb") as fh:
        magic = fh.read(4)
        _flags = fh.read(4)
        if _flags == b"\x00\x00\x00\x00":
            _timestamp = struct.unpack("<I", fh.read(4))[0]
            _source_size = struct.unpack("<I", fh.read(4))[0]
        else:
            _hash = fh.read(8)
            _source_size = struct.unpack("<I", fh.read(4))[0]
        co = marshal.loads(fh.read())
    return co


# ── stack-based decompiler ───────────────────────────────────────────────

class ExprBuilder:
    """Builds Python expressions from bytecode stack operations."""

    def __init__(self, names: Tuple[str, ...], varnames: Tuple[str, ...],
                 consts: Tuple, cellvars: Tuple[str, ...],
                 freevars: Tuple[str, ...]):
        self.names = names
        self.varnames = varnames
        self.consts = consts
        self.cellvars = cellvars
        self.freevars = freevars
        self.stack: List[str] = []

    def push(self, val: str):
        self.stack.append(val)

    def pop(self) -> str:
        if self.stack:
            return self.stack.pop()
        return "<?>"

    def peek(self, n: int = 1) -> str:
        if len(self.stack) >= n:
            return self.stack[-n]
        return "<?>"

    def fmt_const(self, val) -> str:
        if val is None:
            return "None"
        if val is True:
            return "True"
        if val is False:
            return "False"
        if isinstance(val, str):
            return repr(val)
        if isinstance(val, (int, float)):
            return repr(val)
        if isinstance(val, bytes):
            return repr(val)
        if isinstance(val, tuple):
            items = ", ".join(self.fmt_const(x) for x in val)
            if len(val) == 1:
                return f"({items},)"
            return f"({items})"
        if isinstance(val, frozenset):
            items = ", ".join(self.fmt_const(x) for x in sorted(val, key=str))
            return "{" + items + "}"
        if isinstance(val, CodeType):
            return f"<code:{val.co_name}>"
        return repr(val)


def decompile_code(co: CodeType, indent: int = 0) -> str:
    """Decompile a single code object to Python source."""

    names = co.co_names
    varnames = co.co_varnames
    consts = co.co_consts
    cellvars = co.co_cellvars
    freevars = co.co_freevars
    name = co.co_name

    eb = ExprBuilder(names, varnames, consts, cellvars, freevars)

    # Get instructions
    insts = list(dis.get_instructions(co))

    # Build line → offset map
    line_of_offset: Dict[int, int] = {}
    for inst in insts:
        if inst.starts_line:
            line_of_offset[inst.offset] = inst.starts_line

    # Output: list of (line_no, statement)
    output: List[Tuple[int, str]] = []

    # Track pending things
    i = 0
    n = len(insts)

    # Helper to get current line
    def curr_line(default: int = 0) -> int:
        off = insts[i].offset if i < n else 0
        # Walk backwards to find nearest line
        for j in range(i, -1, -1):
            if insts[j].starts_line:
                return insts[j].starts_line
        return co.co_firstlineno

    def emit(line: int, stmt: str):
        """Emit a statement."""
        output.append((line, stmt))

    # Track imports for reconstruction
    pending_imports: List[str] = []

    while i < n:
        inst = insts[i]
        op = inst.opname
        arg = inst.arg
        argval = inst.argval
        line = inst.starts_line if inst.starts_line else (output[-1][0] if output else co.co_firstlineno)

        # ── LOAD ──
        if op == "LOAD_CONST":
            eb.push(eb.fmt_const(argval))

        elif op == "LOAD_FAST":
            eb.push(varnames[arg] if arg < len(varnames) else f"<local_{arg}>")

        elif op == "LOAD_GLOBAL":
            eb.push(names[arg] if arg < len(names) else f"<global_{arg}>")

        elif op == "LOAD_ATTR":
            obj = eb.pop()
            attr = names[arg] if arg < len(names) else f"<attr_{arg}>"
            eb.push(f"{obj}.{attr}")

        elif op == "LOAD_METHOD":
            # LOAD_METHOD pushes obj, then method bound to obj
            # The next CALL_METHOD will use the method
            obj = eb.pop()
            method_name = names[arg] if arg < len(names) else f"<method_{arg}>"
            # Push a marker that this is a method call
            eb.push(f"{obj}.{method_name}")

        elif op == "LOAD_DEREF":
            idx = arg
            if idx < len(cellvars):
                eb.push(cellvars[idx])
            else:
                fi = idx - len(cellvars)
                if fi < len(freevars):
                    eb.push(freevars[fi])
                else:
                    eb.push(f"<deref_{idx}>")

        elif op == "LOAD_CLOSURE":
            if arg < len(cellvars):
                eb.push(cellvars[arg])
            else:
                eb.push(f"<closure_{arg}>")

        # ── STORE ──
        elif op == "STORE_FAST":
            val = eb.pop()
            var = varnames[arg] if arg < len(varnames) else f"<local_{arg}>"
            emit(line, f"{var} = {val}")

        elif op == "STORE_NAME":
            val = eb.pop()
            emit(line, f"{names[arg]} = {val}")

        elif op == "STORE_ATTR":
            val = eb.pop()
            obj = eb.pop()
            attr = names[arg] if arg < len(names) else f"<attr_{arg}>"
            emit(line, f"{obj}.{attr} = {val}")

        elif op == "STORE_DEREF":
            val = eb.pop()
            if arg < len(cellvars):
                emit(line, f"{cellvars[arg]} = {val}")
            else:
                emit(line, f"<deref_{arg}> = {val}")

        elif op == "STORE_SUBSCR":
            val = eb.pop()
            idx = eb.pop()
            obj = eb.pop()
            emit(line, f"{obj}[{idx}] = {val}")

        # ── CALL ──
        elif op == "CALL_FUNCTION":
            nargs = arg
            args = [eb.pop() for _ in range(nargs)]
            args.reverse()
            func = eb.pop()
            emit(line, f"{func}({', '.join(args)})")

        elif op == "CALL_METHOD":
            nargs = arg
            args = [eb.pop() for _ in range(nargs)]
            args.reverse()
            method = eb.pop()
            emit(line, f"{method}({', '.join(args)})")

        elif op == "CALL_FUNCTION_KW":
            nargs = arg
            kw_keys = eb.pop()  # tuple of kw names or const
            # Parse kw_keys
            if isinstance(kw_keys, tuple):
                kw_names = kw_keys
            elif kw_keys.startswith("(") and kw_keys.endswith(")"):
                # Try to parse
                kw_names = tuple(kw_keys.strip("()").replace("'", "").split(", "))
            else:
                kw_names = ()

            args = [eb.pop() for _ in range(nargs)]
            args.reverse()

            func = eb.pop()

            if kw_names:
                nkw = len(kw_names)
                pos_args = args[:nargs - nkw]
                kw_pairs = [f"{kw_names[j]}={args[nargs - nkw + j]}" for j in range(nkw)]
                all_args = pos_args + kw_pairs
                emit(line, f"{func}({', '.join(all_args)})")
            else:
                emit(line, f"{func}({', '.join(args)})")

        # ── IMPORT ──
        elif op == "IMPORT_NAME":
            level = eb.pop()
            fromlist = eb.pop()  # None or tuple of names
            modname = names[arg] if arg < len(names) else "<mod>"

            if fromlist == "None":
                # import foo
                emit(line, f"import {modname}")
            elif isinstance(fromlist, str) and fromlist.startswith("("):
                # from foo import a, b, c
                items = fromlist.strip("()").replace("'", "").split(", ")
                emit(line, f"from {modname} import {', '.join(items)}")

        elif op == "IMPORT_FROM":
            name = names[arg] if arg < len(names) else f"<name_{arg}>"
            eb.push(name)

        elif op == "IMPORT_STAR":
            mod = eb.pop()
            emit(line, f"from {mod} import *")

        # ── POP / RETURN ──
        elif op == "POP_TOP":
            if eb.stack:
                expr = eb.pop()
                emit(line, expr)

        elif op == "RETURN_VALUE":
            val = eb.pop() if eb.stack else ""
            emit(line, f"return {val}" if val else "return")

        # ── JUMPS (simplified - just annotate) ──
        elif op == "POP_JUMP_IF_FALSE":
            cond = eb.pop()
            emit(line, f"if not {cond}: goto {argval}")

        elif op == "POP_JUMP_IF_TRUE":
            cond = eb.pop()
            emit(line, f"if {cond}: goto {argval}")

        elif op == "JUMP_IF_TRUE_OR_POP":
            cond = eb.peek()
            emit(line, f"if {cond}: goto {argval} (or pop)")

        elif op == "JUMP_IF_FALSE_OR_POP":
            cond = eb.peek()
            emit(line, f"if not {cond}: goto {argval} (or pop)")

        elif op == "JUMP_FORWARD":
            emit(line, f"# goto {argval}")

        elif op == "JUMP_ABSOLUTE":
            emit(line, f"# goto {argval}")

        elif op == "JUMP_BACKWARD":
            emit(line, f"# goto backward {argval}")

        elif op == "JUMP_IF_NOT_EXC_MATCH":
            eb.push("Exception")  # Placeholder
            emit(line, f"# except matching at {argval}")

        # ── UNARY / BINARY / COMPARE ──
        elif op == "UNARY_NOT":
            eb.push(f"not ({eb.pop()})")

        elif op == "UNARY_NEGATIVE":
            eb.push(f"-({eb.pop()})")

        elif op == "UNARY_INVERT":
            eb.push(f"~({eb.pop()})")

        elif op == "BINARY_ADD":
            r, l = eb.pop(), eb.pop()
            eb.push(f"({l} + {r})")

        elif op == "BINARY_SUBTRACT":
            r, l = eb.pop(), eb.pop()
            eb.push(f"({l} - {r})")

        elif op == "BINARY_MULTIPLY":
            r, l = eb.pop(), eb.pop()
            eb.push(f"({l} * {r})")

        elif op == "BINARY_TRUE_DIVIDE":
            r, l = eb.pop(), eb.pop()
            eb.push(f"({l} / {r})")

        elif op == "BINARY_FLOOR_DIVIDE":
            r, l = eb.pop(), eb.pop()
            eb.push(f"({l} // {r})")

        elif op == "BINARY_MODULO":
            r, l = eb.pop(), eb.pop()
            eb.push(f"({l} % {r})")

        elif op == "BINARY_POWER":
            r, l = eb.pop(), eb.pop()
            eb.push(f"({l} ** {r})")

        elif op == "BINARY_SUBSCR":
            idx = eb.pop()
            obj = eb.pop()
            eb.push(f"{obj}[{idx}]")

        elif op == "BINARY_LSHIFT":
            r, l = eb.pop(), eb.pop()
            eb.push(f"({l} << {r})")

        elif op == "BINARY_RSHIFT":
            r, l = eb.pop(), eb.pop()
            eb.push(f"({l} >> {r})")

        elif op == "BINARY_AND":
            r, l = eb.pop(), eb.pop()
            eb.push(f"({l} & {r})")

        elif op == "BINARY_OR":
            r, l = eb.pop(), eb.pop()
            eb.push(f"({l} | {r})")

        elif op == "BINARY_XOR":
            r, l = eb.pop(), eb.pop()
            eb.push(f"({l} ^ {r})")

        elif op == "INPLACE_ADD":
            r, l = eb.pop(), eb.pop()
            emit(line, f"{l} += {r}")

        elif op == "INPLACE_SUBTRACT":
            r, l = eb.pop(), eb.pop()
            emit(line, f"{l} -= {r}")

        elif op == "INPLACE_MULTIPLY":
            r, l = eb.pop(), eb.pop()
            emit(line, f"{l} *= {r}")

        elif op == "COMPARE_OP":
            r, l = eb.pop(), eb.pop()
            eb.push(f"({l} {argval} {r})")

        elif op == "IS_OP":
            r, l = eb.pop(), eb.pop()
            if arg:
                eb.push(f"({l} is not {r})")
            else:
                eb.push(f"({l} is {r})")

        elif op == "CONTAINS_OP":
            r, l = eb.pop(), eb.pop()
            if arg:
                eb.push(f"({l} not in {r})")
            else:
                eb.push(f"({l} in {r})")

        # ── BUILD ──
        elif op == "BUILD_LIST":
            items = [eb.pop() for _ in range(arg)]
            items.reverse()
            eb.push(f"[{', '.join(items)}]")

        elif op == "BUILD_TUPLE":
            items = [eb.pop() for _ in range(arg)]
            items.reverse()
            if arg == 0:
                eb.push("()")
            elif arg == 1:
                eb.push(f"({items[0]},)")
            else:
                eb.push(f"({', '.join(items)})")

        elif op == "BUILD_SET":
            items = [eb.pop() for _ in range(arg)]
            items.reverse()
            eb.push("{" + ", ".join(items) + "}")

        elif op == "BUILD_MAP":
            eb.push("{}")  # Empty dict, items added via MAP_ADD or STORE_SUBSCR

        elif op == "BUILD_STRING":
            parts = [eb.pop() for _ in range(arg)]
            parts.reverse()
            # These are typically string fragments concatenated
            result = ""
            for p in parts:
                result += p.strip("'\"")
            eb.push(repr(result))

        elif op == "BUILD_CONST_KEY_MAP":
            nkeys = arg
            keys_val = eb.pop()
            # Parse keys
            if isinstance(keys_val, str) and keys_val.startswith("("):
                key_list = [k.strip().strip("'\"") for k in keys_val.strip("()").split(", ")]
            else:
                key_list = [str(i) for i in range(nkeys)]

            vals = [eb.pop() for _ in range(nkeys)]
            vals.reverse()

            pairs = []
            for k, v in zip(key_list, vals):
                pairs.append(f"{eb.fmt_const(k) if k in [str(k2) for k2 in consts[:20]] else repr(k)}: {v}")
            eb.push("{" + ", ".join(pairs) + "}")

        # ── COLLECTION ops ──
        elif op == "LIST_APPEND":
            # Append to list being built, list is below the value on stack
            pass  # handled by BUILD_LIST

        elif op == "MAP_ADD":
            val = eb.pop()
            key = eb.pop()
            # The dict being built is deeper on stack
            # For now, push back as a pair marker
            eb.push(f"{key}: {val}")

        elif op == "SET_ADD":
            pass  # handled by BUILD_SET

        elif op == "DICT_UPDATE":
            val = eb.pop()
            eb.push(f"**{val}")

        elif op == "DICT_MERGE":
            r = eb.pop()
            l = eb.pop()
            eb.push(f"{{**{l}, **{r}}}")

        elif op == "LIST_EXTEND":
            pass

        elif op == "SET_UPDATE":
            pass

        # ── SLICE ──
        elif op == "BUILD_SLICE":
            if arg == 3:
                step = eb.pop()
                stop = eb.pop()
                start = eb.pop()
                eb.push(f"slice({start}, {stop}, {step})")
            else:
                stop = eb.pop()
                start = eb.pop()
                eb.push(f"slice({start}, {stop})")

        # ── FORMAT ──
        elif op == "FORMAT_VALUE":
            val = eb.pop()
            if arg == 0:
                eb.push(f"str({val})")
            elif arg == 1:
                eb.push(f"repr({val})")
            elif arg == 2:
                eb.push(f"ascii({val})")
            else:
                eb.push(f"format({val})")

        # ── UNPACK ──
        elif op == "UNPACK_SEQUENCE":
            val = eb.pop() if eb.stack else "<?>"
            items = [f"<var{j}>" for j in range(arg)]
            emit(line, f"{', '.join(items)} = {val}")

        elif op == "UNPACK_EX":
            eb.push(f"<unpackex_{arg}>")

        # ── ITERATION ──
        elif op == "GET_ITER":
            obj = eb.pop()
            eb.push(f"iter({obj})")

        elif op == "FOR_ITER":
            emit(line, f"# for loop body, delta={argval}")

        # ── YIELD ──
        elif op == "YIELD_VALUE":
            val = eb.pop()
            emit(line, f"yield {val}")

        elif op == "YIELD_FROM":
            val = eb.pop()
            emit(line, f"yield from {val}")

        # ── EXCEPTION ──
        elif op == "SETUP_FINALLY":
            emit(line, "# try:")

        elif op == "POP_BLOCK":
            pass  # End of try block

        elif op == "POP_EXCEPT":
            emit(line, "# except:")

        elif op == "RERAISE":
            if arg == 0:
                emit(line, "raise")
            elif arg == 1:
                emit(line, f"raise {eb.pop() if eb.stack else ''}")

        elif op == "RAISE_VARARGS":
            if arg == 0:
                emit(line, "raise")
            elif arg == 1:
                val = eb.pop()
                emit(line, f"raise {val}")
            elif arg == 2:
                cause = eb.pop()
                val = eb.pop()
                emit(line, f"raise {val} from {cause}")

        elif op == "WITH_EXCEPT_START":
            pass

        elif op == "DUP_TOP":
            if eb.stack:
                eb.push(eb.peek())

        # ── FUNCTION / CLASS ──
        elif op == "MAKE_FUNCTION":
            # TOS = qualified name (str), TOS1 = code object
            qualname = eb.pop()
            code_val = eb.pop()  # This should be the code object
            emit(line, f"# def {qualname}()")

        elif op == "LOAD_BUILD_CLASS":
            eb.push("type")  # placeholder for class creation

        # ── DELETE ──
        elif op == "DELETE_FAST":
            var = varnames[arg]
            emit(line, f"del {var}")

        elif op == "DELETE_NAME":
            emit(line, f"del {names[arg]}")

        elif op == "DELETE_ATTR":
            obj = eb.pop()
            attr = names[arg]
            emit(line, f"del {obj}.{attr}")

        # ── OTHER ──
        elif op == "NOP":
            pass

        elif op == "EXTENDED_ARG":
            pass  # Handled implicitly by dis

        elif op == "PUSH_NULL":
            eb.push("NULL")

        elif op == "PRECALL":
            pass

        elif op == "GEN_START":
            pass

        elif op == "LOAD_ASSERTION_ERROR":
            eb.push("AssertionError")

        elif op == "COPY_DICT_WITHOUT_KEYS":
            keys = eb.pop()
            d = eb.pop()
            eb.push(f"{{k: v for k, v in {d}.items() if k not in {keys}}}")

        elif op == "GET_LEN":
            obj = eb.pop()
            eb.push(f"len({obj})")

        elif op == "LIST_TO_TUPLE":
            l = eb.pop()
            eb.push(f"tuple({l})")

        elif op == "ROT_TWO":
            if len(eb.stack) >= 2:
                a = eb.pop()
                b = eb.pop()
                eb.push(a)
                eb.push(b)

        elif op == "ROT_THREE":
            if len(eb.stack) >= 3:
                c = eb.pop()
                b = eb.pop()
                a = eb.pop()
                eb.push(b)
                eb.push(c)
                eb.push(a)

        elif op == "ROT_FOUR":
            if len(eb.stack) >= 4:
                d = eb.pop()
                c = eb.pop()
                b = eb.pop()
                a = eb.pop()
                eb.push(c)
                eb.push(d)
                eb.push(a)
                eb.push(b)

        elif op == "ROT_N":
            # Complex rotation
            count = arg
            if len(eb.stack) >= count:
                items = [eb.pop() for _ in range(count)]
                # Rotate: top becomes bottom
                eb.push(items[0])
                for item in reversed(items[1:]):
                    eb.push(item)

        elif op == "SETUP_ANNOTATIONS":
            pass

        elif op == "IMPORT_STAR":
            mod = eb.pop()
            emit(line, f"from {mod} import *")

        elif op == "CACHE":
            pass  # Python 3.11 cache, may appear

        else:
            emit(line, f"# ??? {op} {argval}")

        i += 1

    # Handle any remaining stack items
    while eb.stack:
        expr = eb.pop()
        if expr not in ("NULL",) and not expr.startswith("<"):
            last_line = output[-1][0] if output else co.co_firstlineno
            output.append((last_line, expr))

    # Build final source
    if name == "<module>":
        result = _format_module_output(output, co, 0)
    else:
        result = _format_function_output(name, output, co, indent)

    return result


def _format_module_output(output: List[Tuple[int, str]], co: CodeType, indent: int) -> str:
    """Format module-level output."""
    prefix = "    " * indent
    lines = []
    prev_line = -1
    for line_no, stmt in output:
        if line_no != prev_line and prev_line >= 0:
            lines.append("")
        lines.append(f"{prefix}{stmt}")
        prev_line = line_no
    return "\n".join(lines)


def _format_function_output(name: str, output: List[Tuple[int, str]], co: CodeType, indent: int) -> str:
    """Format function/method output."""
    prefix = "    " * indent
    inner = "    " * (indent + 1)

    args = list(co.co_varnames[:co.co_argcount])
    lines = [f"{prefix}def {name}({', '.join(args)}):"]

    curr_indent = indent + 1
    prev_line = -1
    for line_no, stmt in output:
        p = "    " * curr_indent
        # Simple check for control flow keywords that change indentation
        if stmt.startswith("# for "):
            curr_indent = indent + 2
        elif stmt.startswith("# try:") or stmt.startswith("# except"):
            curr_indent = indent + 2
        elif stmt.startswith("return ") or stmt.startswith("return"):
            curr_indent = indent + 1

        p = "    " * curr_indent
        if line_no != prev_line and prev_line >= 0 and stmt:
            lines.append("")
            pass
        lines.append(f"{p}{stmt}")
        prev_line = line_no

    return "\n".join(lines)


# ── main decompiler ──────────────────────────────────────────────────────

class FullDecompiler:
    """Walk all code objects and decompile the full module."""

    def __init__(self, module_co: CodeType):
        self.module_co = module_co

    def decompile_all(self) -> str:
        output_parts: List[str] = []

        # Module header
        output_parts.append("# Recovered from enhanced_coding_generator.cpython-310.pyc")
        output_parts.append(f"# Decompiled v2 at: {time.ctime()}")
        output_parts.append("")

        # Decompile module-level code (imports, etc.)
        module_src = decompile_code(self.module_co, 0)
        output_parts.append(module_src)

        # Find and decompile classes
        for const in self.module_co.co_consts:
            if isinstance(const, CodeType) and not const.co_name.startswith("<"):
                output_parts.append("")
                output_parts.append(self._decompile_class(const))

        return "\n".join(output_parts)

    def _decompile_class(self, class_co: CodeType) -> str:
        """Decompile a class body."""
        lines = [f"class {class_co.co_name}:"]

        # Find methods
        for const in class_co.co_consts:
            if isinstance(const, CodeType) and not const.co_name.startswith("<"):
                method_src = decompile_code(const, 1)
                lines.append("")
                lines.append(method_src)

        # Also handle nested definitions (lambdas, comprehensions) inside the class body
        # by including the class-level code
        class_body = decompile_code(class_co, 0)
        # Parse out methods from class body
        # For now, just include the methods found in consts

        return "\n".join(lines)


# ── entry point ──────────────────────────────────────────────────────────

def main():
    pyc_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "__pycache__", "enhanced_coding_generator.cpython-310.pyc",
    )
    output_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "enhanced_coding_generator_v2.py",
    )

    if not os.path.exists(pyc_path):
        print(f"ERROR: {pyc_path} not found")
        sys.exit(1)

    print(f"Loading: {pyc_path}")
    co = load_pyc(pyc_path)

    print("Decompiling...")
    fd = FullDecompiler(co)
    source = fd.decompile_all()

    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(source)
    print(f"Written: {output_path} ({len(source)} chars, {source.count(chr(10))} lines)")


if __name__ == "__main__":
    main()
