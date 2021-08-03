import ast

import astunparse
from anytree import findall
from preprocessing.code_element import Method, Class, Module, Statement, CompositeStatement
from preprocessing.diff_code_element import DiffRev
from preprocessing.utils import get_statement_elements, get_expression_elements, different_code_element


class Rev:
    def __init__(self):
        self.modules = []
        self.methods = []
        self.classes = []

    def extract_code_elements(self, tree, path):
        if tree is None:
            print("Tree is null...")
        else:
            # module_name = path.split("/")[-1]
            module_name = path
            module = Module(module_name)

            classes = findall(tree, filter_=lambda node: type(node.name).__name__ == "ClassDef")
            methods = findall(tree, filter_=lambda node: type(node.name).__name__ == "FunctionDef")

            for class_node in classes:
                name = class_node.name.name
                init_methods = [method for method in methods if
                                method.name.name == "__init__"]  # Search for init methods
                init_fields = []
                if len(init_methods) > 0:  # there exists an init method
                    init_method = init_methods[0]
                    init_fields = findall(init_method, filter_=lambda node: type(node.name).__name__ == "Attribute")
                    init_fields = [field.name.attr for field in [field for field in init_fields if
                                                                 'self' in astunparse.unparse(
                                                                     field.name.value) and type(
                                                                     field.name.ctx).__name__ == "Store"]]

                fields = findall(class_node, filter_=lambda node: type(node.name).__name__ == "Name")
                fields = [field.name.id for field in fields if
                          type(field.name.ctx).__name__ == "Store" and len([parent for parent in list(field.path) if
                                                                            type(
                                                                                parent.name).__name__ == "FunctionDef"]) == 0]
                fields = fields + init_fields

                class_bases = [base.id for base in class_node.name.bases if type(base).__name__ == "Name"]

                class_parent_method = ""
                if type(class_node.parent.name).__name__ == "FunctionDef":
                    class_parent_method = class_node.parent.name.name

                rev_class = Class(name, module, str(class_node.path), fields, class_bases, class_parent_method)

                module.add_class(rev_class)
                self.classes.append(rev_class)

            # extract methods

            for method in methods:
                name = method.name.name

                method_classes = [node for node in method.path if
                                  type(node.name).__name__ == "ClassDef"]  # last class in case of inner class

                method_class = None
                if len(method_classes) > 0 and len(self.classes) > 0:
                    method_class = \
                        [rev_class for rev_class in self.classes if
                         rev_class.name == method_classes[-1].name.name and rev_class.class_path == str(method_classes[-1].path) and rev_class.module.name == path][0]

                params = [arg.arg for arg in method.name.args.args]

                rev_method = Method(name, module, method_class, params, method.name)

                if method_class is not None:
                    method_class.methods.append(rev_method)

                for index, stmt in enumerate(method.children):
                    if type(stmt.name).__base__.__name__ == "stmt":
                        if type(stmt.name) == ast.Expr and astunparse.unparse(stmt.children[0].name).startswith('\'') or \
                                "<class 'ast.Ellipsis'>" in astunparse.unparse(stmt.name):
                            continue  # skipping docstrings
                        attrs = stmt.name.__dict__
                        if "body" in attrs:
                            elements = get_expression_elements(stmt)  # Filtering out elements only in expression
                            composite_statement = CompositeStatement(elements, rev_method, stmt.name, stmt.depth, index)
                            extract_inner_statements(composite_statement, stmt, rev_method)
                            rev_method.add_statement(composite_statement)
                        else:
                            leaf_statement = Statement(get_statement_elements(stmt), rev_method, stmt.name, stmt.depth,
                                                       index)
                            rev_method.add_statement(leaf_statement)
                # module.add_method(rev_method)
                if method_class is None:
                    module.add_method(rev_method)
                self.methods.append(rev_method)
            self.modules.append(module)

    def revision_difference(self, rev_b):
        rev_a_modules = self.modules
        rev_b_modules = rev_b.modules

        modules_matched, modules_added, modules_removed = different_code_element(rev_a_modules, rev_b_modules)

        modules_difference = []

        for matched_module in modules_matched:
            modules_difference.append(matched_module[0].module_difference(matched_module[1]))

        diff_rev = DiffRev(modules_matched, modules_added, modules_removed, modules_difference)

        return diff_rev


def extract_inner_statements(composite_statement, stmt, method):
    for index, inner_stmt in enumerate(stmt.children):
        if type(
                inner_stmt.name).__base__.__name__ == "stmt":  # TODO: exceptHanlder is skipped here child stmts are skipped with it
            attrs = inner_stmt.name.__dict__
            if "body" in attrs:
                elements = get_expression_elements(stmt)
                inner_comp_stmt = CompositeStatement(elements, method, inner_stmt.name, inner_stmt.depth, index)
                composite_statement.add_statement(inner_comp_stmt)
                extract_inner_statements(inner_comp_stmt, inner_stmt, method)
            else:
                inner_leaf_stmt = Statement(get_statement_elements(inner_stmt), method, inner_stmt.name,
                                            inner_stmt.depth, index)
                composite_statement.add_statement(inner_leaf_stmt)
