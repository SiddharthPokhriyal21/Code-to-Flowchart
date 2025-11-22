# semantic.py

from astnode import ASTNode

class SemanticAnalyzer:
    """
    Perform simple semantic checks on the AST:
      - Track declared variables and their types (int, float, string)
      - Enforce no use‐before‐declaration
      - Check type compatibility for assignments and expressions
      - Disallow invalid string arithmetic (except '+' for concatenation)
      - Disallow invalid comparisons (e.g. < or > on strings)
    """

    def __init__(self):
        # Map var_name → declared_type ('int', 'float', 'string')
        self.symbols = {}
        self.errors = []

    def analyze(self, node: ASTNode):
        """
        Entry point: visit the given AST node.
        """
        method_name = 'visit_' + node.type
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node: ASTNode):
        for child in (node.children or []):
            if child:
                self.analyze(child)

    def visit_var_decl(self, node: ASTNode):
        # node.children = [ type_node, id_node, optional initializer_expr ]
        type_node = node.children[0]
        var_name_node = node.children[1]
        var_name = var_name_node.value
        var_type = type_node.value   # e.g. 'int', 'float', 'string'

        # Check redeclaration
        if var_name in self.symbols:
            self.errors.append(f"Semantic Error: Variable '{var_name}' already declared")
        else:
            self.symbols[var_name] = var_type

        # If initializer present, check its type
        if len(node.children) == 3:
            init_expr = node.children[2]
            init_type = self._get_expr_type(init_expr)
            if init_type is not None and not self._is_assignable(var_type, init_type):
                self.errors.append(
                    f"Semantic Error: Cannot initialize variable '{var_name}' of type '{var_type}' with '{init_type}'"
                )

    def visit_assign(self, node: ASTNode):
        # node.children = [ id_node, expr_node ]
        var_name = node.children[0].value
        if var_name not in self.symbols:
            self.errors.append(f"Semantic Error: Variable '{var_name}' used before declaration")
            # Still analyze rhs for deeper errors
            self._get_expr_type(node.children[1])
            return

        lhs_type = self.symbols[var_name]
        rhs_type = self._get_expr_type(node.children[1])
        if rhs_type is not None and not self._is_assignable(lhs_type, rhs_type):
            self.errors.append(
                f"Semantic Error: Cannot assign '{rhs_type}' to variable '{var_name}' of type '{lhs_type}'"
            )

    def visit_id(self, node: ASTNode):
        var_name = node.value
        if var_name not in self.symbols:
            self.errors.append(f"Semantic Error: Variable '{var_name}' used before declaration")
            return None
        return self.symbols[var_name]

    def visit_if_stmt(self, node: ASTNode):
        # children = [ condition_expr, then_node, optional else_node ]
        cond_type = self._get_expr_type(node.children[0])
        # Check then and else branches
        self.analyze(node.children[1])
        if len(node.children) == 3:
            self.analyze(node.children[2])

    def visit_while(self, node: ASTNode):
        # children = [ condition_expr, body_node ]
        self._get_expr_type(node.children[0])
        self.analyze(node.children[1])

    def visit_for(self, node: ASTNode):
        # children = [ init_node, cond_node, upd_node, body_node ]
        if node.children[0]:
            # init (either var_decl or assign)
            self.analyze(node.children[0])
        if node.children[1]:
            self._get_expr_type(node.children[1])
        if node.children[2]:
            # assign_expr
            self.visit_assign(node.children[2])
        self.analyze(node.children[3])

    def visit_do_while(self, node: ASTNode):
        # children = [ body_node, condition_expr ]
        self.analyze(node.children[0])
        self._get_expr_type(node.children[1])

    def visit_return_stmt(self, node: ASTNode):
        # children = [ expr_node ]
        self._get_expr_type(node.children[0])

    # ── Expression Type Inference ──

    def _get_expr_type(self, node: ASTNode):
        """
        Recursively infer the type of an expression node:
          - 'num'         → 'int'
          - 'float_num'   → 'float'
          - 'string'      → 'string'
          - 'id'          → look up in self.symbols
          - 'comparison'  → both sides must be numeric or both string (only '==' or '!=' allowed for strings)
                           result type is 'int'
          - 'arith_expr' / 'term' → 
              • if both operands numeric → 'float' if either is float, else 'int'
              • if both string and operator '+' → 'string' (concatenation)
              • otherwise error
        """
        t = node.type

        if t == 'num':
            return 'int'
        elif t == 'float_num':
            return 'float'
        elif t == 'string':
            return 'string'
        elif t == 'id':
            var_name = node.value
            if var_name not in self.symbols:
                self.errors.append(f"Semantic Error: Variable '{var_name}' used before declaration")
                return None
            return self.symbols[var_name]

        elif t == 'comparison':
            left_type = self._get_expr_type(node.children[0])
            right_type = self._get_expr_type(node.children[1])
            op = node.value  # one of '<', '>', '==', '!=', '<=', '>='

            # If either side is string, both must be string and op must be '==' or '!='
            if left_type == 'string' or right_type == 'string':
                if left_type != 'string' or right_type != 'string':
                    self.errors.append(f"Semantic Error: Cannot compare '{left_type}' with '{right_type}'")
                    return None
                if op not in ('==', '!='):
                    self.errors.append(f"Semantic Error: Only '==' or '!=' allowed on strings, not '{op}'")
                    return None
                return 'int'

            # Numeric comparison: both sides must be int or float
            if left_type in ('int', 'float') and right_type in ('int', 'float'):
                return 'int'

            self.errors.append(f"Semantic Error: Invalid types for comparison: '{left_type}' {op} '{right_type}'")
            return None

        elif t in ('arith_expr', 'term'):
            left_type = self._get_expr_type(node.children[0])
            right_type = self._get_expr_type(node.children[1])
            op = node.value  # '+', '-', '*', '/', '%'

            # String concatenation only if both operands are string and op == '+'
            if left_type == 'string' and right_type == 'string' and op == '+':
                return 'string'
            # Disallow any other arithmetic on strings
            if left_type == 'string' or right_type == 'string':
                self.errors.append(f"Semantic Error: Invalid arithmetic on strings: '{left_type}' {op} '{right_type}'")
                return None

            # Numeric arithmetic: if either is float, result is float; else int
            if left_type in ('int', 'float') and right_type in ('int', 'float'):
                if left_type == 'float' or right_type == 'float':
                    return 'float'
                else:
                    return 'int'

            self.errors.append(f"Semantic Error: Invalid types for arithmetic: '{left_type}' {op} '{right_type}'")
            return None

        else:
            # For any other node (e.g. 'stmt', 'type', etc.), just recurse
            for child in (node.children or []):
                if child:
                    self._get_expr_type(child)
            return None

    def _is_assignable(self, lhs_type: str, rhs_type: str):
        """
        Check if a value of rhs_type can be assigned to a variable of lhs_type:
          - int ← int  OK
          - float ← int  OK  (promotion)
          - int ← float  NOT OK
          - float ← float  OK
          - string ← string OK
          - anything else → invalid
        """
        if lhs_type == rhs_type:
            return True
        if lhs_type == 'float' and rhs_type == 'int':
            return True
        # else not allowed
        return False
