from dataclasses import dataclass, field
from ast import *
import ast
import astunparse
import editdistance
from preprocessing.diff_code_element import DiffModule, DiffClass
from preprocessing.node_transformer import nodeReplace
from preprocessing.utils import get_statement_elements, to_tree, get_expression_elements, different_code_element, \
    ast_to_str, ast_comp_to_str, final_leaf, get_stmts_recursive


@dataclass
class Module:
    name: str
    classes: list = field(init=False)
    methods: list = field(init=False)

    def __post_init__(self):
        self.classes = []
        self.methods = []

    def add_class(self, class_node):
        self.classes.append(class_node)

    def add_method(self, method_node):
        self.methods.append(method_node)

    def module_difference(self, adjacent_module):
        classes1 = self.classes
        classes2 = adjacent_module.classes

        methods1 = self.methods
        methods2 = adjacent_module.methods

        classes_matched, classes_added, classes_removed = different_code_element(classes1, classes2)

        methods_matched, methods_added, methods_removed = different_code_element(methods1, methods2)

        classes_difference = []

        for common_class in classes_matched:
            classes_difference.append(common_class[0].class_difference(common_class[1]))

        return DiffModule(classes_matched, classes_added, classes_removed, classes_difference,
                          methods_matched, methods_added, methods_removed)

    def __eq__(self, other):
        if self.name == other.name:
            return True
        return False


@dataclass
class Class:
    name: str
    module: Module
    class_path: str
    fields: list
    bases: list
    methods: list = field(init=False)
    parent_method: str

    def __post_init__(self):
        self.methods = []

    def class_difference(self, adjacent_class):
        methods1 = self.methods
        methods2 = adjacent_class.methods

        methods_matched, methods_added, methods_removed = different_code_element(methods1, methods2)

        return DiffClass(methods_matched, methods_added, methods_removed)

    def __eq__(self, other):
        if self.name == other.name and self.module == other.module and self.parent_method == other.parent_method:
            return True
        return False


@dataclass
class Method:
    name: str
    module: Module
    class_node: Class
    params: list
    leaf_statements: list = field(init=False)
    composite_statements: list = field(init=False)
    argsToParams: list = field(init=False)
    method_ast: ast.AST

    def __post_init__(self):
        self.leaf_statements = []
        self.composite_statements = []
        self.argsToParams = []
        self.position = self.method_ast.lineno

    def add_statement(self, statement):
        if type(statement).__name__ == "Statement":
            self.leaf_statements.append(statement)
        elif type(statement).__name__ == "CompositeStatement":
            self.composite_statements.append(statement)

    def return_type(self):
        return_nodes = []

        for child in ast.iter_child_nodes(self.method_ast):
            if type(child).__name__ == "Subscript":
                for element in get_statement_elements(to_tree(child)):
                    return_nodes.extend(ast.dump(element.name))
        return return_nodes

    def get_total_stmts_count(self):
        return len(self.get_all_stmts())

    def calls(self, method):
        for statement in self.get_all_stmts():
            for element in ast.walk(statement.ast_node):
                if type(element).__name__ == "Call":
                    # print(self.name, method.name, astunparse.unparse(element.func)[0:-1].split(".")[-1])
                    if method.name == astunparse.unparse(element.func)[0:-1].split(".")[-1]:
                        return True
        return False

    def get_all_stmts(self):
        _stmts = []
        for compo in self.composite_statements:
            _stmts.extend(get_stmts_recursive(compo))
        return self.leaf_statements + list(_stmts) + self.composite_statements

    def get_path(self):
        if not (self.class_node is None):
            return self.module.name + "/" + self.class_node.name
        return self.module.name

    def get_path_string(self):
        if not (self.class_node is None):
            return "from the module " + self.module.name + " in class " + self.class_node.name
        return "from the module " + self.module.name

    def __eq__(self, obj):
        if self.name == obj.name and self.params == obj.params and self.module.name == obj.module.name and \
                self.return_type() == obj.return_type():
            if self.class_node is None and obj.class_node is None:
                return True
            elif self.class_node.name == obj.class_node.name:
                return True
        return False


@dataclass
class Statement:
    elements: list
    method: Method
    ast_node: ast.AST
    processed_ast_node: ast.AST = field(init=False)
    depth: int
    index: int

    def __post_init__(self):
        self.processed_ast_node = None

    def get_ast_node(self):
        return eval(ast.dump(self.ast_node))

    def get_processed_ast_node(self):
        return eval(ast.dump(self.processed_ast_node))

    def set_processed_ast_node(self, ast_node):
        self.processed_ast_node = ast_node

    def replace_and_distance(self, leaf2, element1=None, element2=None, df_replacements=None):
        copy_process_leaf = self.get_processed_ast_node()

        if not (df_replacements is None):
            processed_ast_elements = get_statement_elements(to_tree(self.processed_ast_node))
            df_replacements.apply(lambda row: final_leaf(copy_process_leaf, self.processed_ast_node, row, processed_ast_elements), axis=1)
            distance = editdistance.eval(ast_to_str(copy_process_leaf), ast_to_str(leaf2.get_processed_ast_node()))
        else:
            nodeReplace(element1.name, element2.name, copy_process_leaf, self.processed_ast_node,
                        element1.parent).visit(copy_process_leaf)

            distance = editdistance.eval(ast_to_str(copy_process_leaf), ast_to_str(leaf2.get_processed_ast_node()))

        return distance

    def get_original_elements(self):
        return get_statement_elements(to_tree(self.ast_node))

    def get_elements(self):
        if self.processed_ast_node is None:
            return get_statement_elements(to_tree(self.ast_node))
        return get_statement_elements(to_tree(self.processed_ast_node))

    def ast_type(self):
        return type(self.ast_node).__name__

    def get_distance(self, leaf):
        str_leaf1 = ast_to_str(self.processed_ast_node)
        str_leaf2 = ast_to_str(leaf.processed_ast_node)
        replace_distance = editdistance.eval(str_leaf1, str_leaf2)
        return replace_distance

    def __str__(self):
        return ast_to_str(self.ast_node)

    def get_processed_ast_node_str(self):
        return ast_to_str(self.processed_ast_node)

    def __eq__(self, other):
        if str(self) == str(other):
            return True
        return False


@dataclass
class CompositeStatement(Statement):
    leaf_statements: list = field(init=False)
    composite_statements: list = field(init=False)
    processed_ast_node: ast.AST = field(init=False)

    def __post_init__(self):
        self.leaf_statements = []
        self.composite_statements = []
        self.processed_ast_node = None

    # def get_processed_ast_node(self):
    #     _processed_ast_node = eval(ast.dump(self.processed_ast_node))
    #     _processed_ast_node.body = []
    #     return _processed_ast_node

    def add_statement(self, statement):
        if type(statement).__name__ == "Statement":
            self.leaf_statements.append(statement)
        elif type(statement).__name__ == "CompositeStatement":
            self.composite_statements.append(statement)

    def get_elements(self):
        if self.processed_ast_node is None:
            tree = to_tree(self.ast_node)
            return get_expression_elements(tree)
        tree = to_tree(self.processed_ast_node)
        return get_expression_elements(tree)

    def get_all_stmts(self):
        return self.leaf_statements + self.composite_statements

    def is_identical(self, ast_node):
        ast_node1 = ast_comp_to_str(self.ast_node)
        ast_node2 = ast_comp_to_str(ast_node)
        if ast_node1 == ast_node2:
            return True
        return False

    def replace_and_distance(self, leaf2, element1=None, element2=None, df_replacements=None):
        copy_process_leaf = self.get_processed_ast_node()

        if not (df_replacements is None):
            # print(ast_to_str(copy_process_leaf), ast_to_str(leaf2.get_processed_ast_node()))
            processed_ast_elements = get_expression_elements(to_tree(self.processed_ast_node))
            df_replacements.apply(lambda row: final_leaf(copy_process_leaf, self.processed_ast_node, row,processed_ast_elements), axis=1)
            distance = editdistance.eval(ast_comp_to_str(copy_process_leaf), ast_comp_to_str(leaf2.get_processed_ast_node()))
        else:
            nodeReplace(element1.name, element2.name, copy_process_leaf, self.processed_ast_node,
                        element1.parent).visit(copy_process_leaf)
            distance = editdistance.eval(ast_comp_to_str(copy_process_leaf), ast_comp_to_str(leaf2.get_processed_ast_node()))

        # self.set_processed_ast_node(old_process_leaf)
        return distance

    def get_distance(self, leaf):
        str_leaf1 = ast_comp_to_str(self.processed_ast_node)
        str_leaf2 = ast_comp_to_str(leaf.processed_ast_node)
        replace_distance = editdistance.eval(str_leaf1, str_leaf2)
        return replace_distance

    def get_processed_ast_node_str(self):
        return ast_comp_to_str(self.processed_ast_node)

    def __str__(self):
        return ast_comp_to_str(self.ast_node)
