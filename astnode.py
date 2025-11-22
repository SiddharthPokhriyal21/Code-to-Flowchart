# astnode.py

class ASTNode:
    """
    A simple AST node holding:
      - type:    a string (e.g. 'var_decl', 'arith_expr', 'id', etc.)
      - value:   optional payload (e.g. literal text or operator symbol)
      - children: a list of ASTNode children
    """
    def __init__(self, nodetype, value=None):
        self.type = nodetype      # node type (string)
        self.value = value        # e.g. literal value, identifier name, operator
        self.children = []        # list of child ASTNode

    def add_child(self, node):
        self.children.append(node)

    def __repr__(self, level=0):
        """Pretty-print the AST recursively."""
        ret = "  " * level + f"{self.type}" + (f": {self.value}" if self.value else "") + "\n"
        for child in self.children:
            if child:
                ret += child.__repr__(level + 1)
        return ret
