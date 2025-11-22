# flowchart.py

import graphviz
from astnode import ASTNode

class FlowchartGenerator:
    """
    Generate a Graphviz Digraph (PNG) representing the flowchart of a given AST. 
    • Ovals: Start / End
    • Boxes: var_decl, assign, return_stmt, generic stmt
    • Diamonds: if_stmt, while, for, do_while
    • Invisible merge nodes to unify multiple branches
    """

    def __init__(self):
        self.dot = graphviz.Digraph('flowchart', format='png')
        self.dot.attr(rankdir='TB')   # Top → Bottom layout
        self.node_count = 0
        self.last_node = None         # The most recent node to connect from
        self.merge_stack = []         # Stack of “merge” points for nested ifs

    def _new_node_id(self):
        """Generate a fresh node ID."""
        self.node_count += 1
        return f'node{self.node_count}'

    def _formatter(self, node: ASTNode):
        """
        Create a short label for each ASTNode:
          - var_decl: "int x = 5" or "float y = 3.14" or "string s = "hello""
          - assign:   "x = expr"
          - return_stmt: "return expr"
          - stmt:     raw text (like "cin >> x;")
          - if_stmt:  "if (cond)"
          - while:    "while (cond)"
          - for:      "for (init; cond; update)"
          - do_while: "do … while"
        """
        t = node.type

        if t == 'var_decl':
            var_type = node.children[0].value    # 'int', 'float', or 'string'
            var_name = node.children[1].value
            if len(node.children) == 3:
                expr = self._expr_to_str(node.children[2])
                return f"{var_type} {var_name} = {expr}"
            return f"{var_type} {var_name}"

        elif t == 'assign':
            var_name = node.children[0].value
            expr = self._expr_to_str(node.children[1])
            return f"{var_name} = {expr}"

        elif t == 'return_stmt':
            expr = self._expr_to_str(node.children[0])
            return f"return {expr}"

        elif t == 'stmt':
            # Generic statement, raw text
            return node.value

        elif t == 'if_stmt':
            cond = self._expr_to_str(node.children[0])
            return f"if ({cond})"

        elif t == 'while':
            cond = self._expr_to_str(node.children[0])
            return f"while ({cond})"

        elif t == 'for':
            init = node.children[0]
            cond = node.children[1]
            upd = node.children[2]
            parts = []
            parts.append(self._formatter(init) if init else "")
            parts.append(self._expr_to_str(cond) if cond else "")
            parts.append(self._formatter(upd) if upd else "")
            return "for (" + "; ".join(parts) + ")"

        elif t == 'do_while':
            return "do … while"

        else:
            return str(node.type)

    def _expr_to_str(self, node: ASTNode):
        """
        Convert an expression subtree into a single line of text, e.g. "x + 1" or "a == b".
        """
        if not node:
            return ""
        if node.type == 'num':
            return node.value
        elif node.type == 'float_num':
            return node.value
        elif node.type == 'id':
            return node.value
        elif node.type in ('comparison', 'arith_expr', 'term'):
            left = self._expr_to_str(node.children[0])
            right = self._expr_to_str(node.children[1])
            return f"{left} {node.value} {right}"
        else:
            return str(node.type)

    def generate(self, ast: ASTNode):
        """
        Build and return a graphviz.Digraph representing the flowchart:
        Start → … → End
        """
        # 1) Create "Start" oval
        start_id = self._new_node_id()
        self.dot.node(start_id, "Start", shape="oval")
        self.last_node = start_id

        # 2) Recursively process the AST
        self._process_node(ast)

        # 3) Create "End" oval
        end_id = self._new_node_id()
        self.dot.node(end_id, "End", shape="oval")
        if self.last_node:
            self.dot.edge(self.last_node, end_id)

        return self.dot

    def _make_invisible_merge(self):
        """
        Create a tiny invisible node to merge multiple incoming edges.
        """
        merge_id = self._new_node_id()
        self.dot.node(merge_id, "", shape="point", width="0.01", style="invis")
        return merge_id

    def _process_node(self, node: ASTNode):
        t = node.type

        # ── Container nodes: recurse on children ──
        if t in ('program', 'function', 'compound_stmt'):
            for child in (node.children or []):
                if child:
                    self._process_node(child)

        # ── Simple statements: boxes ──
        elif t in ('var_decl', 'assign', 'return_stmt', 'stmt'):
            box_id = self._new_node_id()
            label = self._formatter(node)
            self.dot.node(box_id, label, shape="box")
            if self.last_node:
                self.dot.edge(self.last_node, box_id)
            self.last_node = box_id

        # ── if-statement: diamond + branches ──
        elif t == 'if_stmt':
            decision_id = self._new_node_id()
            self.dot.node(decision_id, self._formatter(node), shape="diamond")
            if self.last_node:
                self.dot.edge(self.last_node, decision_id)

            # Process THEN branch
            before_then = self.node_count
            self.last_node = decision_id
            self._process_node(node.children[1])    # then_block
            then_end = self.last_node
            then_entry = f'node{before_then + 1}'

            # Process ELSE branch (if exists)
            if len(node.children) == 3:
                before_else = self.node_count
                self.last_node = decision_id
                self._process_node(node.children[2])
                else_end = self.last_node
                else_entry = f'node{before_else + 1}'

                # Merge true/false
                merge_id = self._make_invisible_merge()
                self.merge_stack.append(merge_id)

                self.dot.edge(then_end, merge_id)
                self.dot.edge(else_end, merge_id)
                self.dot.edge(decision_id, then_entry, label="true")
                self.dot.edge(decision_id, else_entry, label="false")
                self.last_node = merge_id

            else:
                # No ELSE: create an invisible merge after THEN
                reused = False
                if self.merge_stack and then_end == self.merge_stack[-1]:
                    merge_id = then_end
                    reused = True
                else:
                    merge_id = self._make_invisible_merge()
                    self.merge_stack.append(merge_id)

                if not reused:
                    self.dot.edge(then_end, merge_id)
                self.dot.edge(decision_id, then_entry, label="true")
                self.dot.edge(decision_id, merge_id,   label="false")
                self.last_node = merge_id

        # ── while-loop ──
        elif t == 'while':
            cond_id = self._new_node_id()
            self.dot.node(cond_id, self._formatter(node), shape="diamond")
            if self.last_node:
                self.dot.edge(self.last_node, cond_id)

            # Process body (no incoming edge to body until we label it)
            before_body = self.node_count
            self.last_node = None
            self._process_node(node.children[1])  # body
            body_end = self.last_node

            body_entry = f'node{before_body + 1}'
            self.dot.edge(cond_id, body_entry, label="true")
            self.dot.edge(body_end, cond_id)

            merge_id = self._make_invisible_merge()
            self.dot.edge(cond_id, merge_id, label="false")
            self.last_node = merge_id

        # ── for-loop ──
        elif t == 'for':
            init_node = node.children[0]
            if init_node:
                self._process_node(init_node)

            cond_id = self._new_node_id()
            cond_label = self._expr_to_str(node.children[1]) if node.children[1] else ""
            self.dot.node(cond_id, f"for_cond ({cond_label})", shape="diamond")
            if self.last_node:
                self.dot.edge(self.last_node, cond_id)

            before_body = self.node_count
            self.last_node = None
            self._process_node(node.children[3])  # body
            body_end = self.last_node

            body_entry = f'node{before_body + 1}'
            self.dot.edge(cond_id, body_entry, label="true")

            upd_node = node.children[2]
            if upd_node:
                upd_id = self._new_node_id()
                self.dot.node(upd_id, self._formatter(upd_node), shape="box")
                self.dot.edge(body_end, upd_id)
                self.dot.edge(upd_id, cond_id)
            else:
                self.dot.edge(body_end, cond_id)

            merge_id = self._make_invisible_merge()
            self.dot.edge(cond_id, merge_id, label="false")
            self.last_node = merge_id

        # ── do-while-loop ──
        elif t == 'do_while':
            before_body = self.node_count
            self._process_node(node.children[0])  # body
            body_end = self.last_node

            cond_id = self._new_node_id()
            cond_label = self._expr_to_str(node.children[1])
            self.dot.node(cond_id, f"while ({cond_label})", shape="diamond")
            self.dot.edge(body_end, cond_id)

            body_entry = f'node{before_body + 1}'
            self.dot.edge(cond_id, body_entry, label="true")

            merge_id = self._make_invisible_merge()
            self.dot.edge(cond_id, merge_id, label="false")
            self.last_node = merge_id

        # ── Skip type/main nodes ──
        elif t in ('type', 'main'):
            return

        # ── Fallback: recurse on children ──
        else:
            for child in (node.children or []):
                if child:
                    self._process_node(child)
