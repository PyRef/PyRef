import ast
import re
from ast import *
import astunparse
import editdistance


class replaceProt:
    def __init__(self):
        self.prev_nodes = []
        self.iter = 0
        self.prevIter = 1

    def replace(self, node1, node2, leaf1, leaf2=None):
        leaf1_text = ast.dump(leaf1.get_processed_ast_node()).replace('\\', '\\\\')
        leaf2_text = ast.dump(leaf2.get_processed_ast_node()).replace('\\', '\\\\')

        if type(leaf1).__name__ == "CompositeStatement" and type(leaf2).__name__ == "CompositeStatement":
            procleaf1 = leaf1.get_processed_ast_node()
            procleaf2 = leaf2.get_processed_ast_node()
            procleaf1.body = []
            procleaf2.body = []
            leaf1_text = ast.dump(procleaf1).replace('\\', '\\\\')
            leaf2_text = ast.dump(procleaf2).replace('\\', '\\\\')

        # print(astunparse.unparse(eval(leaf1_text)))
        # print(astunparse.unparse(eval(leaf2_text)))

        node1_text = ast.dump(node1.name).replace('\\', '\\\\')
        node2_text = ast.dump(node2.name).replace('\\', '\\\\')

        # print("node1:", astunparse.unparse(node1.name))
        # print("node2:", astunparse.unparse(node2.name))

        matches = re.finditer(r'%s' % re.escape(node1_text), leaf1_text)
        matches = list(matches)
        matches_count = len(matches)

        _index = 1

        found = False
        target_node = None
        for prev_node in self.prev_nodes:
            if prev_node[0] == node1_text:
                found = True
                target_node = prev_node
                break

        if found and target_node is not None:
            if not (self.prevIter == self.iter):
                target_node[1] = target_node[1] + 1
                _index = target_node[1]
        else:
            self.prev_nodes.append([node1_text, 1])
            _index = 1

        if matches_count > 0:
            self.prevIter = self.iter
            # print(_index, matches_count)
            if _index <= matches_count:
                _from = matches[_index - 1].start()
                copy_text = leaf1_text[_from:]
                copy_text = re.sub(r'%s' % re.escape(node1_text), node2_text, copy_text, count=1)
                copy_text = leaf1_text[:_from] + copy_text
                distance = editdistance.eval(repr(copy_text), repr(leaf2_text))
                # print("Distance", distance)
                return distance
        return


class nodeReplace(ast.NodeTransformer):
    def __init__(self, node1, node2, copy_ast=None, processed_node=None, parent=None):
        self.node1 = node1
        self.node2 = node2
        self.parent = parent
        self.copy_ast = copy_ast
        self.processed_node = processed_node

    def generic_visit(self, node):
        ast.NodeTransformer.generic_visit(self, node)
        if self.is_ast_equal(node, self.node1):
            if self.parent is not None:
                if type(self.parent.name).__name__ == "JoinedStr":
                    return ast.FormattedValue(value=self.node2, conversion=-1, format_spec=None)
            if type(self.node1).__name__ == "Attribute" and type(self.node2).__name__ == "Attribute":
                node.attr = self.node2.attr
                return node
            elif type(self.node1).__name__ == "Attribute":
                node2Value = astunparse.unparse(self.node2)
                if node2Value[-1] == "\n":
                    node2Value = node2Value[0:-1]
                node.attr = node2Value
                return node
            elif type(self.node2).__name__ == "Attribute":
                if type(self.node1).__name__ == "Name":
                    return ast.Name(id=self.node2.attr, ctx=self.node1.ctx)
                return ast.Name(id=self.node2.attr, ctx=ast.Load())
            return self.node2
        return node

    def is_ast_equal(self, node, node1):
        if self.processed_node is None and self.copy_ast is None:
            return node == node1

        copy_elements = list(ast.walk(self.copy_ast))
        proc_elements = list(ast.walk(self.processed_node))

        node_index = copy_elements.index(node)
        node1_index = proc_elements.index(node1)

        if node_index == node1_index:
            if ast.dump(copy_elements[node_index]) == ast.dump(proc_elements[node1_index]):
                return True
        return False
