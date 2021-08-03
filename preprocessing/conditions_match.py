from ast import *
import ast
import astunparse
import editdistance
from preprocessing.node_transformer import nodeReplace, replaceProt
import pandas as pd

from preprocessing.refactorings_info import RefInfo
from preprocessing.utils import get_node_index


def body_mapper(methods1, method2, heuristic_info):
    if heuristic_info is RefInfo.RENAME:
        method1 = methods1
    elif heuristic_info is RefInfo.EXTRACT:
        method1 = methods1[0]
        method3 = methods1[1]
        argsToParams = get_args_to_params(method3, method2)
    elif heuristic_info is RefInfo.INLINE:
        method1 = methods1[1]
        method3 = methods1[0]
        argsToParams = get_args_to_params(method3, method2)

    matched_statements = pd.DataFrame(
        columns=['stmt1', 's1Index', 'stmt2', 's2Index', 'type', 'distance', 'depth_diff', 'index_diff',
                 "replacements"])

    i = 0

    matched_statements = statements_match(method1.get_all_stmts(), method2.get_all_stmts(), matched_statements, i)

    matched_statements = matched_statements[~(matched_statements.type.str.contains("inner"))]

    if len(matched_statements.index) > 0:
        gp = matched_statements.groupby(['stmt1', 's1Index'])

        toKeep = []

        for name, group in gp:
            toKeep.append(
                group.sort_values(['distance', 'depth_diff', 'index_diff'], ascending=[True, True, True]).iloc[0])

        matched_statements = pd.DataFrame(toKeep)  # FURTHER CHECK

        toKeep = []

        gp = matched_statements.groupby(['stmt2', 's2Index'])

        for name, group in gp:
            toKeep.append(
                group.sort_values(['distance', 'depth_diff', 'index_diff'], ascending=[True, True, True]).iloc[0])
        return pd.DataFrame(toKeep)

    return matched_statements


def statements_match(statements1, statements2, matched_statements, i, _type=""):
    for statement1 in statements1:
        for statement2 in statements2:
            if type(statement1).__name__ == "Statement" and type(statement2).__name__ == "Statement":
                identical, reps = process_leaf(statement1, statement2)
                if identical:
                    if reps is not None:
                        reps = reps.to_dict()
                    matched_statements = matched_statements.append(
                        {"stmt1": str(statement1), 's1Index': statement1.index, "s1Lineno": statement1.ast_node.lineno, "stmt2": str(statement2),
                         's2Index': statement2.index,
                         "type": _type + "leaf",
                         "distance": editdistance.eval(str(statement1),
                                                       str(statement2)),
                         "depth_diff": abs(
                             statement1.depth - statement2.depth),
                         "index_diff": abs(
                             statement1.index - statement2.index),
                         "replacements": reps
                         },
                        ignore_index=True)

            elif type(statement1).__name__ == "CompositeStatement" and type(
                    statement2).__name__ == "CompositeStatement":
                compo_matched_statements = pd.DataFrame(
                    columns=['stmt1', 's1Index', 's1Lineno', 'stmt2', 's2Index', 'type', 'distance', 'depth_diff', 'index_diff',
                             "replacements"])
                # matched_statements = {}
                compo_matched_statements = statements_match(statement1.get_all_stmts(),
                                                            statement2.get_all_stmts(), compo_matched_statements, i,
                                                            "inner")
                if len(compo_matched_statements.index) > 0:
                    identical, reps = process_leaf(statement1, statement2)
                    if identical:
                        if reps is not None:
                            reps = reps.to_dict()
                        matched_statements = matched_statements.append(
                            {"stmt1": str(statement1), 's1Index': statement1.index, "s1Lineno": statement1.ast_node.lineno, "stmt2": str(statement2),
                             's2Index': statement2.index,
                             "type": _type + "compo",
                             "distance": editdistance.eval(str(statement1),
                                                           str(statement2)),
                             "depth_diff": abs(
                                 statement1.depth - statement2.depth),
                             "index_diff": abs(
                                 statement1.index - statement2.index),
                             "replacements": reps
                             },
                            ignore_index=True)
                        matched_statements = matched_statements.append(compo_matched_statements, ignore_index=True)

    return matched_statements


def process_leaf(leaf1, leaf2):
    leaf1_ast = leaf1.get_ast_node()
    leaf2_ast = leaf2.get_ast_node()
    abstract_node = ["Return", "Raise", "Assert"]

    if leaf1.ast_type() in abstract_node:
        leaf1_children = list(ast.iter_child_nodes(leaf1_ast))
        if len(leaf1_children) == 0:
            leaf1_ast = ast.Expr(ast.Constant("", kind=""))
        else:
            leaf1_ast = ast.Expr(list(ast.iter_child_nodes(leaf1_ast))[0])
        if leaf2.ast_type() not in abstract_node and 'value' in leaf2_ast.__dict__.keys():
            leaf2_ast = ast.Expr(leaf2_ast.value)

    if leaf2.ast_type() in abstract_node:
        leaf2_children = list(ast.iter_child_nodes(leaf2_ast))
        if len(leaf2_children) == 0:
            leaf2_ast = ast.Expr(ast.Constant("", kind=""))
        else:
            leaf2_ast = ast.Expr(list(ast.iter_child_nodes(leaf2_ast))[0])
        if leaf1.ast_type() not in abstract_node and 'value' in leaf1_ast.__dict__.keys():
            leaf1_ast = ast.Expr(leaf1_ast.value)

    # print("processed leaf1 from: ", str(old_str_leaf1), " to ", str(leaf1).replace('\n', ''))
    # print("processed leaf2 from: ", str(old_str_leaf2), " to ", str(leaf2).replace('\n', ''))

    leaf1.set_processed_ast_node(leaf1_ast)
    leaf2.set_processed_ast_node(leaf2_ast)

    leaf1_elements = leaf1.get_elements()
    leaf2_elements = leaf2.get_elements()

    argsToParams1 = leaf1.method.argsToParams
    argsToParams2 = leaf2.method.argsToParams

    if not len(argsToParams1) == 0:
        argumentization(leaf1_ast, leaf1_elements, argsToParams1)
    if not len(argsToParams2) == 0:
        argumentization(leaf2_ast, leaf2_elements, argsToParams2)

    leaf1.set_processed_ast_node(leaf1_ast)
    leaf2.set_processed_ast_node(leaf2_ast)

    c1, c2, c3 = False, False, False

    replacements = None

    c1 = condition1(leaf1, leaf2)
    if not c1:
        c2 = condition2(leaf1, leaf2)
        if not c2:
            c3, replacements = condition3(leaf1, leaf2)
    return c1 or c2 or c3, replacements


def argumentization(leaf_ast, leaf_elements, argsToParams):
    invocations = []

    for element in leaf_elements:
        if type(element.name).__name__ == "Call":
            invocations.append(element)

    variables = []
    for element in leaf_elements:
        if type(element.name).__name__ == "Name":
            variables.append(element)

    for invoc in invocations:
        args = invoc.name.args
        for arg in args:
            if type(arg).__name__ == "Name":
                possible_args = [ele[1] for ele in argsToParams if ele[0] == arg.id]
                if len(possible_args) > 0:
                    replacement = possible_args[0]
                    nodeReplace(arg, replacement).visit(leaf_ast)

    for var in variables:
        possible_args = [ele[1] for ele in argsToParams if ele[0] == var.name.id]
        if len(possible_args) > 0:
            replacement = possible_args[0]
            nodeReplace(var.name, replacement).visit(leaf_ast)


def get_args_to_params(adjacent_m, added_m):
    if adjacent_m.calls(added_m):
        invocations = []
        for statement in adjacent_m.get_all_stmts():
            for element in ast.walk(statement.get_ast_node()):
                if type(element).__name__ == "Call":
                    if added_m.name == astunparse.unparse(element.func)[0:-1].split(".")[-1]:
                        invocations.append(element)

        args = invocations[0].args  # TODO: check others invocs

        params = added_m.params

        for param in params:
            if param == "self":
                params.remove(param)

        if len(params) == len(args):
            argsToparams = list(zip(params, args))
            # print("args to params:")
            # for element in argsToparams:
            #     print(element[0], "->", astunparse.unparse(element[1]))
            added_m.argsToParams = argsToparams
            return argsToparams  # not needed
    return None


def condition1(leaf1, leaf2):
    if leaf1.get_distance(leaf2) == 0 and leaf1.depth == leaf2.depth:
        return True
    return False


def condition2(leaf1, leaf2):
    if leaf1.get_distance(leaf2) == 0:
        return True
    return False


def condition3(leaf1, leaf2):
    leaf1_elements = leaf1.get_elements()
    leaf2_elements = leaf2.get_elements()

    common_elements = get_common_element(leaf1_elements, leaf2_elements)

    replacements = match_elements(leaf1_elements, leaf2_elements, leaf1,
                                  leaf2)

    if len(replacements.index) == 0:
        return False, None

    replacements.sort_values(by=['distance'], inplace=True, ascending=True)

    distance = leaf1.replace_and_distance(leaf2, df_replacements=replacements)

    # print(leaf1, leaf2)
    #
    # replacements.apply(lambda row: display(row), axis=1)

    return distance == 0, replacements


def display(row):
    print(astunparse.unparse(row['node1'].name).replace('\n', ''), row['node1'].name)
    print(astunparse.unparse(row['node2'].name).replace('\n', ''), row['node1'].name)


def compare(element1, element2):
    type1 = type(element1.name).__name__
    type2 = type(element2.name).__name__

    if type1 == "Constant" and type2 == "Constant":
        return element1.name.value == element2.name.value
    elif type1 == "Name" and type2 == "Name":
        if type(element1.name.ctx).__name__ == type(element2.name.ctx).__name__:
            return element1.name.id == element2.name.id
    elif type1 == "Call" and type2 == "Call":
        return astunparse.unparse(element1.name) == astunparse.unparse(element2.name)
    elif type1 == "Attribute" and type2 == "Attribute":
        return element1.name.attr == element2.name.attr
    elif type(element1.name).__base__.__name__ == "operator" and type(
            element2.name).__base__.__name__ == "operator":
        return ast.dump(element1.name) == ast.dump(element2.name)
    return False


def get_common_element(elements1, elements2):
    common_elements = []

    for element1 in elements1:
        for element2 in elements2:
            if compare(element1, element2) and get_node_index(element1) == get_node_index(element2):
                common_elements.append((element1, element2))

    for common_element in common_elements:
        for element in elements1:
            if compare(element, common_element[0]):
                elements1.remove(element)

    for common_element in common_elements:
        for element in elements2:
            if compare(element, common_element[1]):
                elements2.remove(element)

    return common_elements


def is_replaceable(element1, element2):
    type1 = type(element1.name).__name__
    type2 = type(element2.name).__name__
    replaceable = ["Name", "Call", "Attribute"]
    if type1 == type2:
        return True
    elif type1 == "Call" and is_invoc_cover_stmt(element1) and type2 == "Name":
        return False
    elif type2 == "Call" and is_invoc_cover_stmt(element2) and type1 == "Name":
        return False
    elif type1 == "Name" and type2 == "Call":
        if type(element1.name.ctx).__name__ == "Store":
            return False
        else:
            return True
    elif type1 in replaceable and type2 in replaceable:
        return True
    elif type(element1.name).__base__.__name__ == "operator" and type(
            element2.name).__base__.__name__ == "operator":
        return True
    return False


def match_elements(elements1, elements2, leaf1, leaf2):
    originalDistance = leaf1.get_distance(leaf2)
    _dict = {}
    replacements = {}
    i = 0
    nr = replaceProt()
    for element1 in elements1:
        nr.iter = nr.iter + 1
        for element2 in elements2:
            if is_replaceable(element1, element2):
                replace_distance = nr.replace(element1, element2, leaf1, leaf2)
                # replace_distance = leaf1.replace_and_distance(leaf2, element1, element2)
                if replace_distance <= originalDistance:
                    if type(element1.name).__name__ == "Call" and type(element2.name).__name__ == "Call":
                        compatible = compatible_invocs_subexpression(element1, element2)
                        if compatible:
                            replacements[i] = {"node1": element1, "node2": element2, "distance": replace_distance,
                                               'type': type(element1.name).__name__ + "To" + type(
                                                   element2.name).__name__}
                            i = i + 1
                    else:
                        replacements[i] = {"node1": element1, "node2": element2, "distance": replace_distance,
                                           'type': type(element1.name).__name__ + "To" + type(element2.name).__name__}
                        i = i + 1
        distances = []
        for key in replacements.keys():
            if replacements[key]["distance"] == 0:
                distances.append(0)

        if len(distances) > 0:
            break

    replacements = pd.DataFrame.from_dict(replacements, "index")
    if len(replacements.index) > 0:
        for element1 in elements1:
            min_dist = replacements[replacements.node1 == element1].distance.min()
            replacements = replacements.drop(replacements[(replacements.distance > min_dist)
                                                          & (replacements.node1 == element1)].index)
        for element2 in elements2:
            min_dist = replacements[replacements.node2 == element2].distance.min()
            replacements = replacements.drop(replacements[(replacements.distance > min_dist)
                                                          & (replacements.node2 == element2)].index)
    return replacements


def compatible_invocs_subexpression(invoc1, invoc2):
    if is_invoc_cover_stmt(invoc1) and is_invoc_cover_stmt(invoc2):  # strict checking on invoc cover stmt
        if not (astunparse.unparse(invoc1.name).split(".")[-1].split("(")[0] ==
                astunparse.unparse(invoc2.name).split(".")[-1].split("(")[0] or
                invoc1.name.args == invoc2.name.args):
            return False
    subexp1 = astunparse.unparse(invoc1.name).split(".")[0:-1]
    subexp2 = astunparse.unparse(invoc2.name).split(".")[0:-1]
    intersection = [value for value in subexp1 if value in subexp2]
    difference1 = list(set(subexp1).difference(set(intersection)))
    difference2 = list(set(subexp2).difference(set(intersection)))
    if len(subexp1) <= 1 and len(subexp2) <= 1:
        return True
    if len(difference1) <= len(intersection) and len(difference2) <= len(intersection):
        return True
    return False


def is_invoc_cover_stmt(invoc):
    if type(invoc.parent.name) == ast.Expr:
        return True
    return False
