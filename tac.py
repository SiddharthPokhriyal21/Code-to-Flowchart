# tac.py

from astnode import ASTNode

class TACGenerator:
    """
    Walk the AST and emit Three-Address Code (TAC). Every instruction has at most
    three operands (two sources, one target). Introduces temporaries: t1, t2, …
    and labels: L1, L2, …
    """

    def __init__(self):
        self.temp_count = 0   # counter for temporary variables
        self.label_count = 0  # counter for labels
        self.code = []        # list of TAC lines (strings)

    def new_temp(self):
        """Return a fresh temp name, e.g. 't1'."""
        self.temp_count += 1
        return f"t{self.temp_count}"

    def new_label(self):
        """Return a fresh label, e.g. 'L1'."""
        self.label_count += 1
        return f"L{self.label_count}"

    def generate(self, ast_root: ASTNode) -> [str]:
        """
        Given the AST root (program node), return a list of TAC instructions.
        """
        self.code.clear()
        self.temp_count = 0
        self.label_count = 0

        function_node = ast_root.children[0]
        self._emit("# ---------- three-address code ----------")
        self._process_node(function_node)
        return self.code

    def _emit(self, line: str):
        """Append a line of TAC to the output list."""
        self.code.append(line)

    def _process_node(self, node: ASTNode):
        t = node.type

        # ── Containers: recurse ──
        if t in ('program', 'function', 'compound_stmt'):
            for child in (node.children or []):
                if child:
                    self._process_node(child)

        # ── Declarations ──
        elif t == 'var_decl':
            # children = [ type_node, id_node, optional initializer ]
            var_type = node.children[0].value
            var_name = node.children[1].value
            if len(node.children) == 3:
                init_temp = self._process_node(node.children[2])
                self._emit(f"{var_name} = {init_temp}")
            else:
                self._emit(f"# declare {var_name}")

        # ── Assignment ──
        elif t == 'assign':
            var_name = node.children[0].value
            expr_temp = self._process_node(node.children[1])
            self._emit(f"{var_name} = {expr_temp}")

        # ── Return ──
        elif t == 'return_stmt':
            expr_temp = self._process_node(node.children[0])
            self._emit(f"return {expr_temp}")

        # ── Generic statement (I/O etc.) ──
        elif t == 'stmt':
            raw = node.value.strip()
            self._emit(f"# {raw}")

        # ── if-then[-else] ──
        elif t == 'if_stmt':
            cond_node = node.children[0]
            then_node = node.children[1]
            else_node = node.children[2] if len(node.children) == 3 else None

            cond_temp = self._process_node(cond_node)

            label_true = self.new_label()
            label_false = self.new_label()
            label_end = self.new_label()

            self._emit(f"if {cond_temp} goto {label_true}")
            self._emit(f"goto {label_false}")

            self._emit(f"{label_true}:")
            self._process_node(then_node)
            self._emit(f"goto {label_end}")

            self._emit(f"{label_false}:")
            if else_node:
                self._process_node(else_node)
            self._emit(f"{label_end}:")

        # ── while-loop ──
        elif t == 'while':
            cond_node = node.children[0]
            body_node = node.children[1]

            label_start = self.new_label()
            label_body = self.new_label()
            label_end = self.new_label()

            self._emit(f"goto {label_start}")

            self._emit(f"{label_body}:")
            self._process_node(body_node)

            self._emit(f"{label_start}:")
            cond_temp = self._process_node(cond_node)
            self._emit(f"if {cond_temp} goto {label_body}")
            self._emit(f"{label_end}:")

        # ── for-loop ──
        elif t == 'for':
            # children = [ init_node, cond_node, upd_node, body_node ]
            init_node = node.children[0]
            cond_node = node.children[1]
            upd_node = node.children[2]
            body_node = node.children[3]

            if init_node:
                self._process_node(init_node)

            label_start = self.new_label()
            label_body = self.new_label()
            label_end = self.new_label()

            self._emit(f"goto {label_start}")

            self._emit(f"{label_body}:")
            self._process_node(body_node)

            if upd_node:
                self._process_node(upd_node)

            self._emit(f"{label_start}:")
            if cond_node:
                cond_temp = self._process_node(cond_node)
                self._emit(f"if {cond_temp} goto {label_body}")
            else:
                self._emit(f"goto {label_body}")

            self._emit(f"{label_end}:")

        # ── do-while-loop ──
        elif t == 'do_while':
            body_node = node.children[0]
            cond_node = node.children[1]

            label_body = self.new_label()
            label_end = self.new_label()

            self._emit(f"{label_body}:")
            self._process_node(body_node)

            cond_temp = self._process_node(cond_node)
            self._emit(f"if {cond_temp} goto {label_body}")
            self._emit(f"{label_end}:")

        # ── Expressions: return a temp (or literal) ──
        elif t == 'comparison':
            left_temp = self._process_node(node.children[0])
            right_temp = self._process_node(node.children[1])
            target = self.new_temp()
            self._emit(f"{target} = {left_temp} {node.value} {right_temp}")
            return target

        elif t in ('arith_expr', 'term'):
            left_temp = self._process_node(node.children[0])
            right_temp = self._process_node(node.children[1])
            target = self.new_temp()
            self._emit(f"{target} = {left_temp} {node.value} {right_temp}")
            return target

        elif t == 'num':
            return node.value

        elif t == 'float_num':
            return node.value

        elif t == 'id':
            return node.value

        elif t == 'string':
            return node.value

        else:
            # Recurse any other node types (should handle nested expressions/statements)
            for child in (node.children or []):
                if child:
                    self._process_node(child)
            return None
