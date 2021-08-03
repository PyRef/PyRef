import ast
from anytree import findall, Node
import astunparse
import pandas as pd

from preprocessing.node_transformer import nodeReplace


def to_tree(parent_node):
    if isinstance(parent_node, ast.AST):
        parent_node = Node(parent_node)

    for child in ast.iter_child_nodes(parent_node.name):
        current_node = Node(child, parent=parent_node)
        to_tree(current_node)

    return parent_node


def different_code_element(code_elements1, code_elements2):
    matched = []
    for element1 in code_elements1:
        for element2 in code_elements2:
            if element1 == element2:
                matched.append((element1, element2))

    removed = code_elements1[:]
    for element2 in code_elements2:
        for element1 in removed:
            if element1 == element2:
                removed.remove(element1)

    added = code_elements2[:]
    for element1 in code_elements1:
        for element2 in added:
            if element1 == element2:
                added.remove(element2)

    return matched, added, removed


def get_statement_elements(leaf):
    invocations = list(findall(leaf, filter_=lambda node: type(node.name).__name__ == "Call"))
    variables = list(findall(leaf, filter_=lambda node: type(node.name).__name__ == "Name"))
    for variable in variables[:]:  # Remove function names from vars list
        if type(variable.parent.name).__name__ == "Call":
            for index, child_node in enumerate(variable.parent.children):
                if variable is child_node and index == 0:
                    variables.remove(variable)
    constants = list(findall(leaf, filter_=lambda node: type(node.name).__name__ == "Constant"))
    operators = list(findall(leaf, filter_=lambda node: type(node.name).__base__.__name__ == "operator"))
    attributes = findall(leaf, filter_=lambda node: type(node.name).__name__ == "Attribute")
    attributes = [att for att in attributes if
                  not (type(att.parent.name).__name__ == "Call")]  # REMOVING ATTS THAT ARE NOT VARS

    elements = constants + invocations + variables + attributes + operators

    if len(elements) > 0:
        elements_df = pd.DataFrame(elements, columns=['element_object'])

        elements_df['depth'] = elements_df.apply(lambda x: x['element_object'].depth, axis=1)
        elements_df['index'] = elements_df.apply(lambda x: x['element_object'].height, axis=1)

        elements_df = elements_df.sort_values(["depth", "index"], ascending=(False, True))

        return elements_df["element_object"].tolist()

    return []


def get_expression_elements(leaf):
    elements = []
    for node in leaf.children:
        if type(node.name).__base__.__name__ == "expr":
            for element in get_statement_elements(node):
                elements.append(element)
    return elements


def invoc_cover_stmt(leaf, invoc):
    for count, ast_child in enumerate(ast.iter_child_nodes(leaf.ast_node)):
        if (count == len(to_tree(leaf.ast_node).children) - 1) and ast_child == invoc.name:
            return True
    return False


def intersection(lst1, lst2):
    lst3 = [value for value in lst1 if value in lst2]
    return lst3


def ast_to_str(ast_node):
    return astunparse.unparse(ast_node)[0:-1]


def ast_comp_to_str(ast_node):
    tree = to_tree(ast_node)

    expression = [child for child in tree.children if type(child.name).__base__.__name__ == "expr"]

    if len(expression) > 0:
        lastNode = [child for child in tree.children if type(child.name).__base__.__name__ == "expr"][-1]

        lastNode = astunparse.unparse(lastNode.name)[0:-1]

        lastNodeIndex = astunparse.unparse(ast_node).index(lastNode) + len(lastNode)

        return astunparse.unparse(ast_node)[0:lastNodeIndex]

    return astunparse.unparse(ast_node).split(":")[0]  # TRY FINALLY no expression


def final_leaf(copy_leaf, leaf, row, processed_ast_elements):
    node1 = row["node1"]
    node2 = row["node2"]

    found = [element for element in processed_ast_elements if element.name == node1.name]
    if len(found) > 0:
        nodeReplace(node1.name, node2.name, copy_leaf, leaf, node1.parent).visit(copy_leaf)
        processed_ast_elements.remove(found[0])


def get_stmts_recursive(compo_stmt, res=None):
    if res is None:
        res = []
    all_stmts = compo_stmt.get_all_stmts()
    for _stmt in all_stmts:
        res.append(_stmt)
        if type(_stmt).__name__ == "CompositeStatement":
            get_stmts_recursive(_stmt, res)
    return res


def get_node_index(node):
    if type(node.name).__name__ == "Module":
        return 0
    else:
        node_root = node.root
        descends = list(node_root.descendants)
        return descends.index(node)


def is_extracted(row, stmts):
    var = row["node2"]
    content = row["node1"]

    for stmt in stmts:
        if type(stmt).__name__ == "Statement" and stmt.ast_type() == "Assign":
            elements = stmt.get_original_elements()
            for element in elements:
                if type(element.name).__name__ == "Name" and type(
                        element.name.ctx).__name__ == "Store" and element.name.id == var.name.id:
                    if astunparse.unparse(content.name) == astunparse.unparse(stmt.get_ast_node().value):
                        return True
        return False
