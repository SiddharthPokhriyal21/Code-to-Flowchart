# parser.py

from astnode import ASTNode

class Parser:
    """
    Recursive-descent parser for a simple C/C++-style language. Handles:
      - Types: int, float, string
      - Literals: integer, floating point, string
      - Declarations, assignments, if/else, loops (while, for, do-while), return
      - Generic statements (treated as raw text) for I/O, etc.
    """

    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def current(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return {'type': 'EOF', 'value': None}

    def eat(self, token_type):
        """
        Consume current token if it matches token_type; otherwise raise an error.
        """
        current = self.current()
        if current['type'] == token_type:
            self.pos += 1
            return current
        raise RuntimeError(f"Expected token type {token_type} but got {current['type']} ({current['value']})")

    def parse(self):
        """
        Entry point: parse a program (single function) and return the AST root.
        """
        return self.program()

    def program(self):
        """
        program → function
        """
        node = ASTNode('program')
        node.add_child(self.function())
        return node

    def function(self):
        """
        function → type_spec MAIN LPAREN RPAREN compound_stmt
        """
        node = ASTNode('function')
        node.add_child(self.type_spec())              # return type
        main_tok = self.eat('MAIN')                   # 'main'
        node.add_child(ASTNode('main', main_tok['value']))
        self.eat('LPAREN')
        self.eat('RPAREN')
        node.add_child(self.compound_stmt())
        return node

    def type_spec(self):
        """
        type_spec → INT | FLOAT_TYPE | STRING_TYPE
        """
        tok = self.current()
        if tok['type'] in ('INT', 'FLOAT_TYPE', 'STRING_TYPE'):
            self.pos += 1
            return ASTNode('type', tok['value'])
        raise RuntimeError(f"Expected a type specifier but got {tok['type']} ({tok['value']})")

    def compound_stmt(self):
        """
        compound_stmt → '{' stmt* '}'
        """
        node = ASTNode('compound_stmt')
        self.eat('LBRACE')
        # A statement can begin with: INT, FLOAT_TYPE, STRING_TYPE, ID, IF, RETURN, WHILE, FOR, DO
        while self.current()['type'] in (
            'INT', 'FLOAT_TYPE', 'STRING_TYPE',
            'ID', 'IF', 'RETURN', 'WHILE', 'FOR', 'DO'
        ):
            node.add_child(self.stmt())
        self.eat('RBRACE')
        return node

    def stmt(self):
        """
        stmt → var_decl
              | assign_stmt
              | if_stmt
              | while_stmt
              | for_stmt
              | do_while_stmt
              | return_stmt
              | generic_stmt (anything ending in ';')
        """
        tok = self.current()

        # --- Variable Declaration ---
        if tok['type'] in ('INT', 'FLOAT_TYPE', 'STRING_TYPE'):
            return self.var_decl()

        # --- Assignment or Generic Statement starting with an identifier ---
        elif tok['type'] == 'ID':
            next_tok = (
                self.tokens[self.pos + 1]
                if (self.pos + 1) < len(self.tokens)
                else {'type': 'EOF'}
            )
            # If next is 'OP' with '=', it's an assignment; otherwise treat as generic.
            if next_tok['type'] == 'OP' and next_tok['value'] == '=':
                return self.assign_stmt()
            else:
                # Generic: gather everything until the next semicolon
                text_tokens = []
                while self.current()['type'] not in ('SEMI', 'EOF'):
                    text_tokens.append(self.current()['value'])
                    self.pos += 1
                if self.current()['type'] == 'SEMI':
                    text_tokens.append(self.eat('SEMI')['value'])
                raw_text = " ".join(text_tokens).strip()
                return ASTNode('stmt', raw_text)

        # --- if-statement ---
        elif tok['type'] == 'IF':
            return self.if_stmt()

        # --- return-statement ---
        elif tok['type'] == 'RETURN':
            return self.return_stmt()

        # --- while-statement ---
        elif tok['type'] == 'WHILE':
            return self.while_stmt()

        # --- for-statement ---
        elif tok['type'] == 'FOR':
            return self.for_stmt()

        # --- do-while-statement ---
        elif tok['type'] == 'DO':
            return self.do_while_stmt()

        else:
            raise RuntimeError(f"Unexpected token in stmt(): {tok['type']} ({tok['value']})")

    def var_decl(self):
        """
        var_decl → ( INT | FLOAT_TYPE | STRING_TYPE ) ID [ '=' expr ] ';'
        """
        node = ASTNode('var_decl')
        node.add_child(self.type_spec())   # e.g. 'int' or 'float' or 'string'
        id_tok = self.eat('ID')
        node.add_child(ASTNode('id', id_tok['value']))

        # Optional initializer
        if self.current()['type'] == 'OP' and self.current()['value'] == '=':
            self.eat('OP')
            node.add_child(self.expr())
        self.eat('SEMI')
        return node

    def assign_stmt(self):
        """
        assign_stmt → ID '=' expr ';'
        """
        node = ASTNode('assign')
        id_tok = self.eat('ID')
        node.add_child(ASTNode('id', id_tok['value']))
        self.eat('OP')  # '='
        node.add_child(self.expr())
        self.eat('SEMI')
        return node

    def if_stmt(self):
        """
        if_stmt → 'if' '(' expr ')' stmt [ 'else' stmt ]
        """
        node = ASTNode('if_stmt')
        self.eat('IF')
        self.eat('LPAREN')
        node.add_child(self.expr())
        self.eat('RPAREN')

        # then-branch
        if self.current()['type'] == 'LBRACE':
            node.add_child(self.compound_stmt())
        else:
            node.add_child(self.stmt())

        # optional else
        if self.current()['type'] == 'ELSE':
            self.eat('ELSE')
            if self.current()['type'] == 'LBRACE':
                node.add_child(self.compound_stmt())
            else:
                node.add_child(self.stmt())

        return node

    def while_stmt(self):
        """
        while_stmt → 'while' '(' expr ')' stmt
        """
        node = ASTNode('while')
        self.eat('WHILE')
        self.eat('LPAREN')
        node.add_child(self.expr())
        self.eat('RPAREN')
        if self.current()['type'] == 'LBRACE':
            node.add_child(self.compound_stmt())
        else:
            node.add_child(self.stmt())
        return node

    def for_stmt(self):
        """
        for_stmt → 'for' '(' [ var_decl | assign_stmt ] ';' [ expr ] ';' [ assign_expr ] ')' stmt
        - init = var_decl or assign_stmt or empty
        - cond = expr or empty
        - update = assign_expr or empty
        """
        node = ASTNode('for')
        self.eat('FOR')
        self.eat('LPAREN')

        # init clause
        if self.current()['type'] in ('INT', 'FLOAT_TYPE', 'STRING_TYPE'):
            init_node = self.var_decl()
        elif self.current()['type'] == 'ID':
            init_node = self.assign_stmt()
        else:
            init_node = None
            self.eat('SEMI')
        node.add_child(init_node)

        # cond clause
        if self.current()['type'] != 'SEMI':
            cond_node = self.expr()
            self.eat('SEMI')
        else:
            cond_node = None
            self.eat('SEMI')
        node.add_child(cond_node)

        # update clause (no trailing semicolon yet)
        if self.current()['type'] == 'ID':
            upd_node = self.assign_expr()
        else:
            upd_node = None
        node.add_child(upd_node)

        self.eat('RPAREN')

        # body
        if self.current()['type'] == 'LBRACE':
            node.add_child(self.compound_stmt())
        else:
            node.add_child(self.stmt())

        return node

    def do_while_stmt(self):
        """
        do_while_stmt → 'do' stmt 'while' '(' expr ')' ';'
        """
        node = ASTNode('do_while')
        self.eat('DO')
        if self.current()['type'] == 'LBRACE':
            node.add_child(self.compound_stmt())
        else:
            node.add_child(self.stmt())
        self.eat('WHILE')
        self.eat('LPAREN')
        node.add_child(self.expr())
        self.eat('RPAREN')
        self.eat('SEMI')
        return node

    def return_stmt(self):
        """
        return_stmt → 'return' expr ';'
        """
        node = ASTNode('return_stmt')
        self.eat('RETURN')
        node.add_child(self.expr())
        self.eat('SEMI')
        return node

    def assign_expr(self):
        """
        assign_expr → ID '=' expr   (used inside for-loop update)
        """
        node = ASTNode('assign')
        id_tok = self.eat('ID')
        node.add_child(ASTNode('id', id_tok['value']))
        self.eat('OP')  # '='
        node.add_child(self.expr())
        return node

    def expr(self):
        """
        expr → arith_expr [ (<|>|==|!=|<=|>=) arith_expr ]
        """
        node = self.arith_expr()
        if (self.current()['type'] == 'OP' and
            self.current()['value'] in ('<', '>', '==', '!=', '<=', '>=')):
            op_tok = self.eat('OP')
            new_node = ASTNode('comparison', op_tok['value'])
            new_node.add_child(node)
            new_node.add_child(self.arith_expr())
            return new_node
        return node

    def arith_expr(self):
        """
        arith_expr → term { (+|-) term }
        """
        node = self.term()
        while (self.current()['type'] == 'OP' and
               self.current()['value'] in ('+', '-')):
            op_tok = self.eat('OP')
            new_node = ASTNode('arith_expr', op_tok['value'])
            new_node.add_child(node)
            new_node.add_child(self.term())
            node = new_node
        return node

    def term(self):
        """
        term → factor { (*|/|%) factor }
        """
        node = self.factor()
        while (self.current()['type'] == 'OP' and
               self.current()['value'] in ('*', '/', '%')):
            op_tok = self.eat('OP')
            new_node = ASTNode('term', op_tok['value'])
            new_node.add_child(node)
            new_node.add_child(self.factor())
            node = new_node
        return node

    def factor(self):
        """
        factor → NUM | FLOAT_NUM | STRING | ID | '(' expr ')'
        """
        tok = self.current()
        if tok['type'] == 'NUM':
            self.eat('NUM')
            return ASTNode('num', tok['value'])
        elif tok['type'] == 'FLOAT_NUM':
            self.eat('FLOAT_NUM')
            return ASTNode('float_num', tok['value'])
        elif tok['type'] == 'STRING':
            self.eat('STRING')
            return ASTNode('string', tok['value'])
        elif tok['type'] == 'ID':
            self.eat('ID')
            return ASTNode('id', tok['value'])
        elif tok['type'] == 'LPAREN':
            self.eat('LPAREN')
            node = self.expr()
            self.eat('RPAREN')
            return node
        else:
            raise RuntimeError(f"Unexpected factor token {tok['type']} ({tok['value']})")
