""" A recursive descent pascal parser. """

import logging
from ...common import CompilerError
from ..tools.recursivedescent import RecursiveDescentParser
from .nodes import expressions, statements, symbols, types
from .symbol_table import Scope


class Parser(RecursiveDescentParser):
    """ Parses pascal into ast-nodes """

    logger = logging.getLogger("pascal.parser")

    def __init__(self, diag):
        super().__init__()
        self.diag = diag
        self.current_scope = None
        self.mod = None

    def parse_source(self, tokens, context):
        """ Parse a module from tokens """
        self.logger.debug("Parsing source")
        self.init_lexer(tokens)

        self._integer_type = context.get_type("integer")
        self._boolean_type = context.get_type("boolean")
        self._real_type = context.get_type("real")
        self._char_type = context.get_type("char")
        self.current_scope = context.root_scope
        try:
            program = self.parse_program(context)
        except CompilerError as ex:
            self.diag.add_diag(ex)
            raise
        self.logger.debug("Parsing complete")
        context.add_program(program)
        return program

    def add_symbol(self, sym):
        """ Add a symbol to the current scope """
        if self.current_scope.has_symbol(sym.name, include_parent=False):
            self.error(
                "Redefinition of {0}".format(sym.name), loc=sym.location
            )
        else:
            self.current_scope.add_symbol(sym)

    def has_local_symbol(self, name: str) -> bool:
        return self.current_scope.has_symbol(name, include_parent=False)

    def lookup_symbol(self, name: str):
        if self.current_scope.has_symbol(name):
            return self.current_scope.get_symbol(name)
        else:
            raise KeyError(name)

    def enter_scope(self):
        """ Enter a lexical scope. """
        scope = Scope(self.current_scope)
        self.current_scope = scope
        return scope

    def leave_scope(self):
        """ Leave the current lexical scope. """
        self.current_scope = self.current_scope.parent

    def parse_program(self, context):
        """ Parse a program """
        self.consume("program")
        name = self.consume("ID")
        if self.has_consumed("("):
            args = []
            args.append(self.consume("ID"))
            while self.has_consumed(","):
                args.append(self.consume("ID"))
            self.consume(")")
            # print("TODO", args)
            # TODO: use args for ??
        self.consume(";")
        self.logger.debug("Parsing program %s", name.val)
        scope = self.enter_scope()
        program = symbols.Program(name.val, scope, name.loc)

        main_code = self.parse_block()
        program.main_code = main_code
        self.consume(".")
        self.consume("EOF")
        return program

    def parse_block(self):
        """ Parse a block.

        A block being constants, types, variables and statements.
        """

        # Parse labels:
        if self.has_consumed("label"):
            labels = []
            label = self.consume("NUMBER")
            labels.append(label)
            while self.has_consumed(","):
                label = self.consume("NUMBER")
                labels.append(label)
            self.consume(";")

        # Handle a toplevel construct
        if self.peek == "const":
            self.parse_constant_definitions()

        if self.peek == "type":
            self.parse_type_definitions()

        if self.peek == "var":
            self.parse_variable_declarations()

        if self.peek == "procedure" or self.peek == "function":
            self.parse_function_declarations()

        return self.parse_compound_statement()

    def parse_constant_definitions(self):
        """ Parse constant definitions.

        This has the form:

        'const'
          'ID' '=' expr;
          'ID' '=' expr;
        """
        self.consume("const")
        while self.peek == "ID":
            name = self.consume("ID")
            self.consume("=")
            val = self.parse_expression()
            self.consume(";")
            # TODO: evaluate expression?
            typ = None
            constant = symbols.Constant(name.val, typ, val, name.loc)
            self.add_symbol(constant)

    def parse_uses(self):
        """ Parse import construct """
        self.consume("uses")
        self.consume("ID").val
        # self.mod.imports.append(name)
        self.consume(";")

    def parse_designator(self):
        """ A designator designates an object with a name. """
        name = self.consume("ID")
        # Look it up!
        if self.current_scope.has_symbol(name.val):
            symbol = self.current_scope.get_symbol(name.val)
            return symbol, name.loc
        else:
            self.error("Unknown identifier {}".format(name.val), name.loc)

    def parse_id_sequence(self):
        """ Parse one or more identifiers seperated by ',' """
        ids = [self.parse_id()]
        while self.has_consumed(","):
            ids.append(self.parse_id())
        return ids

    def parse_id(self):
        return self.consume("ID")

    # Type system
    def parse_type_spec(self, packed=False):
        """ Parse type specification.

        This can be any type, from record to ordinal or boolean.
        """
        # Parse the first part of a type spec:
        if self.peek == "record":
            typ = self.parse_record_type_definition(packed)
        elif self.peek == "packed":
            location = self.consume("packed").loc
            if packed:
                self.error("Duplicate packed indicator", loc=location)
            else:
                typ = self.parse_type_spec(packed=True)
        elif self.peek == "array":
            typ = self.parse_array_type_definition(packed)
        elif self.peek == "set":
            typ = self.parse_set_type_definition(packed)
        elif self.peek == "file":
            location = self.consume("file")
            self.consume("of")
            component_type = self.parse_type_spec()
            typ = types.FileType(component_type, location)
        elif self.peek == "(":
            typ = self.parse_enum_type_definition()
        elif self.peek == "@" or self.peek == "^":
            # Pointer!
            # TODO: move this to lexer?
            if self.peek == "@":
                location = self.consume("@").loc
            else:
                location = self.consume("^").loc
            pointed_type = self.parse_type_spec()
            typ = types.PointerType(pointed_type)
        else:
            typ = self.parse_ordinal_type()

        return typ

    def parse_record_type_definition(self, packed):
        """ Parse record type description. 
        """
        location = self.consume("record").loc
        fields = self.parse_record_type_definition_field_list()
        self.consume("end")
        typ = types.RecordType(fields, location)
        return typ

    def parse_record_type_definition_field_list(self):
        if self.peek == "ID":
            fields = self.parse_record_fixed_list()
            if self.peek == "case":
                variant = self.parse_record_variant()
                fields.append(variant)
            else:
                variant = None
        elif self.peek == "case":
            fields = [self.parse_record_variant()]
        else:
            fields = []

        return fields

    def parse_record_fixed_list(self):
        """ Parse fixed parts of a record type definition. """
        fields = []
        # Fixed fields part:
        while self.peek == "ID":
            identifiers = self.parse_id_sequence()
            self.consume(":")
            field_typ = self.parse_type_spec()
            for identifier in identifiers:
                fields.append(
                    types.RecordField(
                        identifier.val, field_typ, identifier.loc
                    )
                )

            # Loop until no more ';' found
            if self.peek == ";":
                self.consume(";")
            else:
                break
        return fields

    def parse_record_variant(self):
        """ Parse case .. of part. """
        location = self.consume("case").loc
        if self.peek == "ID":
            tag_field = self.consume("ID").val
            self.consume(":")
        else:
            tag_field = None
        tag_type = self.parse_type_spec()
        self.consume("of")
        variants = []
        while True:
            variant_values = self.parse_expression_list()
            self.consume(":")
            self.consume("(")
            variant_fields = self.parse_record_type_definition_field_list()
            self.consume(")")
            variants.append((variant_values, variant_fields))
            if self.peek == ";":
                self.consume(";")
            else:
                break

        variant = types.RecordVariant(tag_field, tag_type, variants, location)
        return variant

    def parse_array_type_definition(self, packed):
        location = self.consume("array").loc
        array_dimensions = []
        if self.peek == "[" or self.peek == "(.":
            use_brackets = self.peek == "["

            if use_brackets:
                self.consume("[")
            else:
                self.consume("(.")

            array_dimension = self.parse_ordinal_type()
            array_dimensions.append(array_dimension)
            while self.peek == ",":
                self.consume(",")
                array_dimension = self.parse_ordinal_type()
                array_dimensions.append(array_dimension)

            if use_brackets:
                self.consume("]")
            else:
                self.consume(".)")
        else:
            self.error("Expected array size definition")
        self.consume("of")
        array_element_type = self.parse_type_spec()
        typ = types.ArrayType(
            array_element_type, array_dimensions, packed, location
        )
        return typ

    def parse_set_type_definition(self, packed):
        location = self.consume("set")
        self.consume("of")
        set_type = self.parse_type_spec()
        # TODO? set?
        typ = 1
        return typ

    def parse_ordinal_type(self):
        if self.peek == "ID":
            # The type is identified by an identifier:
            symbol, location = self.parse_designator()
            if isinstance(symbol, symbols.DefinedType):
                typ = symbol.typ
            else:
                lower_bound = symbol
                self.consume("..")
                upper_bound = self.parse_expression()
                typ = types.SubRange(lower_bound, upper_bound, location)
        else:
            lower_bound = self.parse_expression()
            location = self.consume("..").loc
            upper_bound = self.parse_expression()
            typ = types.SubRange(lower_bound, upper_bound, location)
        return typ

    def parse_enum_type_definition(self):
        """ Parse enumerated type definition.

        This looks like:

        colors = (red, green, blue)
        
        """
        location = self.consume("(").loc
        identifiers = self.parse_id_sequence()
        self.consume(")")

        values = []
        typ = types.EnumType(values, location)
        for value, identifier in enumerate(identifiers):
            enum_value = symbols.EnumValue(
                identifier.val, typ, value, identifier.loc
            )
            self.add_symbol(enum_value)
            values.append(enum_value)

        return typ

    def parse_type_definitions(self):
        """ Parse type definitions.

        These have the form:
        'type'
          'ID' '=' type-spec ';'
          'ID' '=' type-spec ';'
          ...
        """
        self.consume("type")
        while self.peek == "ID":
            typename = self.consume("ID")
            self.consume("=")
            newtype = self.parse_type_spec()
            self.consume(";")

            typedef = symbols.DefinedType(typename.val, newtype, typename.loc)
            self.add_symbol(typedef)

    def parse_variable_declarations(self):
        """ Parse variable declarations """
        self.consume("var")
        variables = []
        variables.extend(self.parse_single_variable_declaration())
        while self.peek == "ID":
            variables.extend(self.parse_single_variable_declaration())
        return variables

    def parse_single_variable_declaration(self):
        """ Parse a single variable declaration line ending in ';' """
        names = self.parse_id_sequence()
        self.consume(":")
        var_type = self.parse_type_spec()

        # Initial value:
        if self.has_consumed("="):
            initial = self.parse_expression()
        else:
            initial = None
        self.consume(";")

        # Create variables:
        variables = []
        for name in names:
            var = symbols.Variable(name.val, var_type, initial, name.loc)
            variables.append(var)
            self.add_symbol(var)
        return variables

    def parse_function_declarations(self):
        """ Parse all upcoming function / procedure definitions """
        while self.peek == "function" or self.peek == "procedure":
            self.parse_function_def()

    def parse_function_def(self):
        """ Parse function definition """
        if self.peek == "function":
            location = self.consume("function").loc
            is_function = True
        else:
            location = self.consume("procedure").loc
            is_function = False

        subroutine_name = self.consume("ID").val
        self.logger.debug("Parsing subroutine %s", subroutine_name)
        if self.has_local_symbol(subroutine_name):
            subroutine = self.lookup_symbol(subroutine_name)
            if is_function:
                if not isinstance(subroutine, symbols.Function):
                    self.error(
                        "Expected a forward declared function", loc=location
                    )
            else:
                if not isinstance(subroutine, symbols.Procedure):
                    self.error(
                        "Expected a forward declared procedure", loc=location
                    )
            self.current_scope, backup_scope = (
                subroutine.inner_scope,
                self.current_scope,
            )
            self.consume(";")
            self.parse_block()
            self.consume(";")
            self.current_scope = backup_scope
        else:
            if is_function:
                subroutine = symbols.Function(subroutine_name, location)
            else:
                subroutine = symbols.Procedure(subroutine_name, location)

            self.add_symbol(subroutine)

            scope = self.enter_scope()
            subroutine.inner_scope = scope

            if self.peek == "(":
                parameters = self.parse_formal_parameter_list()
                for parameter in parameters:
                    self.add_symbol(parameter)
            else:
                parameters = None

            if is_function:
                self.consume(":")
                return_type = self.parse_type_spec()
                subroutine.typ = types.FunctionType(parameters, return_type)
            else:
                subroutine.typ = types.ProcedureType(parameters)

            self.consume(";")

            if self.peek == "forward":
                self.consume("forward")
            else:
                self.parse_block()
            self.consume(";")

            self.leave_scope()

        # paramtypes = [p.typ for p in parameters]
        # func.typ = types.FunctionType(paramtypes, returntype)
        # func.parameters = parameters
        # if self.has_consumed(";"):
        #     func.body = None
        # else:
        #     func.body = self.parse_compound()

    def parse_formal_parameter_list(self):
        """ Parse format parameters to a subroutine.

        These can be immutable values, variables, or
        function pointers.
        """
        self.consume("(")
        parameters = []
        while True:
            if self.peek == "ID":
                identifiers = self.parse_id_sequence()
                self.consume(":")
                typ = self.parse_type_spec()
                for identifier in identifiers:
                    parameter = symbols.FormalParameter(
                        identifier.val, typ, identifier.loc
                    )
                    parameters.append(parameter)
            elif self.peek == "var":
                self.consume("var")
                identifiers = self.parse_id_sequence()
                self.consume(":")
                typ = self.parse_type_spec()
                for identifier in identifiers:
                    parameter = symbols.FormalParameter(
                        identifier.val, typ, identifier.loc
                    )
                    parameters.append(parameter)
            elif self.peek == "function":
                self.consume("function")
                name = self.parse_id()
                params = self.parse_formal_parameter_list()
                self.consume(":")
                return_type = self.parse_type_spec()
                typ = types.FunctionType(params, return_type)
                parameter = symbols.FormalParameter(name.val, typ, name.loc)
                parameters.append(parameter)
            elif self.peek == "procedure":
                self.consume("procedure")
                name = self.parse_id()
                if self.peek == "(":
                    params = self.parse_formal_parameter_list()
                else:
                    params = None
                typ = types.ProcedureType(params)
                parameter = symbols.FormalParameter(name.val, typ, name.loc)
                parameters.append(parameter)
            else:
                self.error("Expected formal parameter!")

            if not self.has_consumed(";"):
                break
        self.consume(")")
        return parameters

    def parse_statement(self) -> statements.Statement:
        """ Determine statement type based on the pending token """
        if self.peek == "if":
            statement = self.parse_if_statement()
        elif self.peek == "while":
            statement = self.parse_while()
        elif self.peek == "repeat":
            statement = self.parse_repeat()
        elif self.peek == "for":
            statement = self.parse_for()
        elif self.peek == "goto":
            statement = self.parse_goto()
        elif self.peek == "case":
            statement = self.parse_case_of()
        elif self.peek == "return":
            statement = self.parse_return()
        elif self.peek == "begin":
            statement = self.parse_compound_statement()
        elif self.peek == "end":
            statement = statements.Empty()
        elif self.peek == ";":
            self.consume(";")
            statement = statements.Empty()
        elif self.peek == "with":
            statement = self.parse_with_statement()
        elif self.peek == "ID":
            symbol, location = self.parse_designator()
            # print(symbol, type(symbol))
            if isinstance(symbol, symbols.Procedure) or isinstance(
                symbol.typ, types.ProcedureType
            ):
                # Procedure call
                if self.peek == "(":
                    arguments = self.parse_actual_parameter_list()
                else:
                    arguments = None
                statement = statements.ProcedureCall(
                    symbol, arguments, location
                )
            else:
                lhs = self.parse_variable_access(symbol, location)
                location = self.consume(":=").loc
                rhs = self.parse_expression()
                statement = statements.Assignment(lhs, rhs, location)
        elif self.peek == "NUMBER":
            # label!
            label = self.consume("NUMBER")
            self.consume(":")
            labeled_statement = self.parse_statement()
            statement = statements.Label(
                label.val, labeled_statement, label.loc
            )
        else:
            self.error("Expected statement here")

        return statement

    def parse_if_statement(self):
        """ Parse if statement """
        location = self.consume("if").loc
        condition = self.parse_expression()
        self.consume("then")
        true_code = self.parse_statement()
        if self.has_consumed("else"):
            false_code = self.parse_statement()
        else:
            false_code = statements.Empty()
        return statements.If(condition, true_code, false_code, location)

    def parse_case_of(self) -> statements.CaseOf:
        """ Parse case-of statement """
        location = self.consume("case").loc
        expression = self.parse_expression()
        self.consume("of")
        options = []
        while self.peek not in ["end", "else"]:
            values = self.parse_expression_list()
            self.consume(":")
            statement = self.parse_statement()
            options.append((values, statement))

            if self.peek == ";":
                self.consume(";")
            else:
                break

        # Optional else clause:
        if self.peek == "else":
            self.consume("else")
            default_statement = self.parse_statement()
            self.consume(";")
            options.append(("else", default_statement))

        self.consume("end")
        return statements.CaseOf(expression, options, location)

    def parse_while(self) -> statements.While:
        """ Parses a while statement """
        location = self.consume("while").loc
        condition = self.parse_expression()
        self.consume("do")
        statement = self.parse_statement()
        return statements.While(condition, statement, location)

    def parse_repeat(self):
        """ Parses a repeat statement """
        location = self.consume("repeat").loc
        inner = []
        while self.peek != "until":
            inner.append(self.parse_statement())
            if self.peek == ";":
                self.consume(";")
            else:
                break
        self.consume("until")
        condition = self.parse_expression()
        return statements.Repeat(inner, condition, location)

    def parse_for(self) -> statements.For:
        """ Parse a for statement """
        loc = self.consume("for").loc
        loop_var, _ = self.parse_designator()
        assert isinstance(loop_var, symbols.Variable)
        self.consume(":=")
        start = self.parse_expression()
        if self.peek == "to":
            self.consume("to")
            up = True
        else:
            self.consume("downto")
            up = False
        stop = self.parse_expression()
        self.consume("do")
        statement = self.parse_statement()
        return statements.For(loop_var, start, up, stop, statement, loc)

    def parse_with_statement(self):
        location = self.consume("with").loc
        record_variables = self.parse_one_or_more(
            self.parse_single_with_level, ","
        )
        self.consume("do")

        # for record_variable in record_variables:

        inner_statement = self.parse_statement()

        for _ in record_variables:
            self.leave_scope()
        return statements.With(record_variables, inner_statement, location)

    def parse_single_with_level(self):
        """ Parse a single with level.
        """

        record_ref = self.parse_variable()

        if not record_ref.typ.is_record:
            self.error(
                "Expected variable of record type", loc=record_ref.location,
            )

        # Enter new scope:
        self.enter_scope()

        # Enhance scope with record field names:
        for field in record_ref.typ.fields:
            field_proxy = symbols.RecordFieldProxy(
                field.name, field.typ, record_ref.location
            )
            self.add_symbol(field_proxy)
        return record_ref

    def parse_goto(self):
        location = self.consume("goto").loc
        label = self.parse_expression()
        return statements.Goto(label, location)

    def parse_actual_parameter_list(self):
        """ Parse a list of parameters """
        self.consume("(")
        parameters = self.parse_one_or_more(self.parse_actual_parameter, ",")
        self.consume(")")
        return parameters

    def parse_actual_parameter(self):
        expr = self.parse_expression()
        if self.has_consumed(":"):
            total_width = self.parse_expression()
            if self.has_consumed(":"):
                frac_digits = self.parse_expression()
        return expr

    def parse_return(self) -> statements.Return:
        """ Parse a return statement """
        loc = self.consume("return").loc
        if self.has_consumed(";"):
            expr = None
        else:
            expr = self.parse_expression()
            self.consume(";")
        return statements.Return(expr, loc)

    def parse_compound_statement(self):
        """ Parse a compound statement """
        location = self.consume("begin").loc
        statement_list = self.parse_one_or_more(self.parse_statement, ";")
        self.consume("end")

        return statements.Compound(statement_list, location)

    def parse_variable(self):
        """ Parse access to a variable with eventual accessor suffixes. """
        symbol, location = self.parse_designator()
        return self.parse_variable_access(symbol, location)

    def parse_variable_access(self, symbol, location):
        """ Process any trailing variable access. """

        if not isinstance(
            symbol,
            (
                symbols.Variable,
                symbols.Constant,
                symbols.EnumValue,
                symbols.Function,
                symbols.Procedure,
                symbols.RecordFieldProxy,
            ),
        ):
            self.error(
                "Expected a variable here, got: {}".format(symbol),
                loc=location,
            )

        lhs = expressions.VariableAccess(symbol, location)
        while self.peek in ["[", ".", "^"]:
            if self.peek == "[":
                # array indexing
                location = self.consume("[").loc
                indici = self.parse_expression_list()
                self.consume("]")

                for index in indici:
                    if not lhs.typ.is_array:
                        self.error(
                            "Expected array type, got: {}".format(lhs.typ),
                            loc=location,
                        )
                    array_typ = lhs.typ
                    # if len(indici) > len(array_typ.dimensions):
                    #     self.error('Too many indici ({}) for array dimensions ({})'.format(len(indici), len(array_typ.dimensions)), loc=location)
                    indexed_typ = array_typ.indexed(1)
                    lhs = expressions.Index(
                        lhs, [index], indexed_typ, index.location
                    )
            elif self.peek == ".":
                location = self.consume(".").loc
                if not lhs.typ.is_record:
                    self.error(
                        "Expected record type, got: {}".format(lhs.typ),
                        loc=location,
                    )
                field_name = self.parse_id().val
                if lhs.typ.has_field(field_name):
                    field = lhs.typ.find_field(field_name)
                    lhs = expressions.Member(
                        lhs, field_name, field.typ, location
                    )
                else:
                    self.error(
                        "No such field {}".format(field_name), loc=location
                    )
            elif self.peek == "^":
                location = self.consume("^").loc
                if not lhs.typ.is_pointer:
                    self.error(
                        "Expected pointer type, got {}".format(lhs.typ),
                        loc=location,
                    )
                typ = lhs.typ.ptype
                lhs = expressions.Deref(lhs, typ, location)
            else:
                raise AssertionError("must be [, ^ or .")
        return lhs

    def parse_expression_list(self):
        """ Parse one or more expressions seperated by ',' """
        expression_list = self.parse_one_or_more(self.parse_expression, ",")
        return expression_list

    def parse_expression(self) -> expressions.Expression:
        lhs = self.parse_simple_expression()
        while self.peek in [
            "=",
            "<>",
            ">",
            "<",
            "<=",
            ">=",
            "in",
            "div",
            "mod",
            "and",
            "or",
        ]:
            operator = self.consume()
            rhs = self.parse_simple_expression()
            lhs = expressions.Binop(
                lhs, operator.typ, rhs, lhs.typ, operator.loc
            )
        return lhs

    def parse_simple_expression(self) -> expressions.Expression:
        """ Parse [-] term [-/+ term]* """
        if self.peek in ["+", "-"]:
            operator = self.consume()
            lhs = self.parse_term()
            lhs = expressions.Unop(operator.typ, lhs, lhs.typ, operator.loc)
        else:
            lhs = self.parse_term()

        while self.peek in ["+", "-"]:
            operator = self.consume()
            rhs = self.parse_term()
            lhs = expressions.Binop(
                lhs, operator.typ, rhs, lhs.typ, operator.loc
            )
        return lhs

    def parse_term(self):
        """ Parse a term (one or more factors) """
        lhs = self.parse_factor()
        while self.peek in ["*", "div", "mod", "/"]:
            operator = self.consume()
            rhs = self.parse_factor()
            lhs = expressions.Binop(
                lhs, operator.typ, rhs, lhs.typ, operator.loc
            )
        return lhs

    def parse_factor(self) -> expressions.Expression:
        """ Parse a factor """
        if self.peek == "not":
            location = self.consume("not").loc
            rhs = self.parse_factor()
            return expressions.Unop("not", rhs, rhs.typ, location)
        else:
            return self.parse_primary_expression()

    def parse_primary_expression(self) -> expressions.Expression:
        """ Literal and parenthesis expression parsing """
        if self.peek == "(":
            self.consume("(")
            expr = self.parse_expression()
            self.consume(")")
        elif self.peek == "NUMBER":
            val = self.consume("NUMBER")
            expr = expressions.Literal(val.val, self._integer_type, val.loc)
        elif self.peek == "REAL":
            val = self.consume("REAL")
            expr = expressions.Literal(val.val, self._real_type, val.loc)
        elif self.peek == "true":
            val = self.consume("true")
            expr = expressions.Literal(True, self._boolean_type, val.loc)
        elif self.peek == "false":
            val = self.consume("false")
            expr = expressions.Literal(False, self._boolean_type, val.loc)
        elif self.peek == "nil":
            location = self.consume("nil").loc
            expr = expressions.Literal(None, None, location)
        elif self.peek == "STRING":
            val = self.consume("STRING")
            expr = expressions.Literal(val.val, None, val.loc)
        elif self.peek == "ID":
            symbol, location = self.parse_designator()
            if isinstance(symbol.typ, types.FunctionType):
                if self.peek == "(":
                    args = self.parse_actual_parameter_list()
                else:
                    args = None
                expr = expressions.FunctionCall(
                    symbol, args, symbol.typ.return_type, location
                )
            else:
                expr = self.parse_variable_access(symbol, location)
        elif self.peek == "[":
            location = self.consume("[")
            elements = []
            if self.peek != "]":
                while True:
                    element = self.parse_expression()
                    if self.peek == "..":
                        self.consume("..")
                        upper = self.parse_expression()
                        element = (element, upper)
                    elements.append(element)

                    if self.peek == ",":
                        self.consume(",")
                    else:
                        break
            self.consume("]")
            expr = expressions.Literal(elements, None, location)
        else:
            self.error(
                "Expected number, identifier or (expr), got {0}".format(
                    self.peek
                )
            )
        return expr

    def parse_one_or_more(self, parse_function, seperator: str):
        """ Parse one or more occurences parsed by parse_function
        seperated by seperator.
        """
        items = []
        items.append(parse_function())
        while self.has_consumed(seperator):
            items.append(parse_function())
        return items
