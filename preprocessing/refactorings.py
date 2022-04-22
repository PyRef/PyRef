from dataclasses import dataclass


@dataclass
class Refactoring:
    def __init__(self, _from, _to, _type, _location):
        self._from = _from
        self._to = _to
        self._type = _type
        self._location = _location

    def to_json_format(self):
        output = {
            "Refactoring Type": self._type,
            "Original": self._from,
            "Updated": self._to,
            "Location": self._location
        }
        return output

    def __str__(self):
        pass


class RenameRef(Refactoring):
    def __init__(self, _from, _to, _type, _location, _matched_statements, _removed_m, _added_m, _param_change):
        super().__init__(_from, _to, _type, _location)
        self._removed_m = _removed_m
        self._added_m = _added_m
        self._matched_statements = _matched_statements
        self._param_change = _param_change

    def to_json_format(self):
        output = {
            "Refactoring Type": self._type,
            "Original": self._from,
            "Updated": self._to,
            "Location": self._location,
            "Original Line": self._removed_m.position,
            "Updated Line": self._added_m.position,
            "Description": self.__str__().split("|")[1:-1],
            # "Matched Statements": list(zip(self._matched_statements.stmt1, self._matched_statements.stmt2))
        }
        if "Param" in self._type:
            output["Old Params"] = ' '.join(self._removed_m.params)
            output["New Params"] = ' '.join(self._added_m.params)
        return output

    def __str__(self):
        rename_info = "The method %s %s is renamed to %s" % (self._from, self._removed_m.get_path_string(), self._to)
        return_info = "The return type of method %s %s is updated" % (self._from, self._removed_m.get_path_string())
        param_info = ""

        final_info = ["ref_type: %s" % self._type]
        for change in self._type:
            if change == "Rename Method":
                final_info.append(rename_info)
            if "Param" in change:
                if "Add" in change:
                    # print(change, self._param_change)
                    # print(self._from, self._removed_m.get_path_string(), self._to)
                    param_info = "The parameters [ %s ] are added to the method %s %s" % (
                    ' '.join(self._param_change[0]), self._from, self._removed_m.get_path_string())
                if "Remove" in change:
                    param_info = "The parameters [ %s ] of the method %s %s is/are removed" % (
                    ' '.join(self._param_change[0]), self._from, self._removed_m.get_path_string())
                if "Rename" in change:
                    param_info = "The parameters [ %s ] of the method %s %s are changed/renamed to [%s]" % (
                    ' '.join(self._param_change[0]), self._from, self._removed_m.get_path_string(), ' '.join(self._param_change[1]))
                final_info.append(param_info)
            if "Change Return Type" == change:
                final_info.append(return_info)

        final_info.append("Location: %s" % self._location)
        return "|".join(final_info)


class ExtractInlineRef(Refactoring):
    def __init__(self, _from, _to, _type, _location, _matched_statements, _tuple_methods, _updated_method):
        super().__init__(_from, _to, _type, _location)
        self._matched_statements = _matched_statements
        self._tuple_methods = _tuple_methods
        self._updated_method = _updated_method

    def to_json_format(self):
        output = {
            "Refactoring Type": self._type,
            "Original": self._from,
            "Updated": self._to,
            "Location": self._location,
            "Original Method Line": "(" + str(self._tuple_methods[0].position) + "," + str(self._tuple_methods[1].position) + ")",
            "Extracted/Inlined Method Line": self._updated_method.position,
            "Extracted/Inlined Lines": sorted(self._matched_statements.s1Lineno.tolist()),
            "Description": self.__str__().split("|")[-2],
            # "Matched Statements": list(zip(self._matched_statements.stmt1, self._matched_statements.stmt2))
        }
        return output

    def __str__(self):
        if self._type == "Extract Method":
            return "ref_type: %s| The method %s %s is extracted from method %s %s | Location: %s" % (
                self._type, self._to, self._updated_method.get_path_string(), self._from, self._tuple_methods[0].get_path_string(),
                self._location)
        else:
            return "ref_type: %s| The method %s %s is inlined into method %s %s | Location: %s" % (
                self._type, self._to, self._updated_method.get_path_string(), self._from, self._tuple_methods[0].get_path_string(),
                self._location)


class ClassRef(Refactoring):
    def to_json_format(self):
        output = {
            "Refactoring Type": self._type,
            "Original": self._from,
            "Updated": self._to,
            "Location": self._location,
            "Description": self.__str__().split("|")[-2],
            # "Matched Statements": list(zip(self._matched_statements.stmt1, self._matched_statements.stmt2))
        }
        return output

    def __str__(self):
        if self._type == "Rename Class":
            return "ref_type: %s| class %s was renamed to class %s | Location: %s" % (
                self._type, self._from, self._to, self._location)
        else:
            return "ref_type: %s| class %s was moved to module %s" % (
                self._type, self._from, self._location)


class MoveRef(Refactoring):
    def __init__(self, _from, _to, _type, _location, _old_location, _move, _matched_statements, _removed_m, _added_m):
        super().__init__(_from, _to, _type, _location)
        self._old_location = _old_location
        self._move = _move
        self._matched_statements = _matched_statements
        self._removed_m = _removed_m
        self._added_m = _added_m

    def to_json_format(self):
        output = {
            "Refactoring Type": self._type if self._move == "None" else self._move + " Method",
            "Original": self._from,
            "Updated": self._to,
            "Old Location": self._old_location,
            "New Location": self._location,
            "Old Method Line": self._removed_m.position,
            "New Method Line": self._added_m.position,
            "Description": self.__str__().split("|")[-1],
        }
        return output

    def __str__(self):
        if self._added_m.class_node is not None:
            return "ref_type: %s| %s | method %s %s was moved to class %s of module %s " % (
            self._type, self._move, self._to, self._removed_m.get_path_string(), self._added_m.class_node.name, self._added_m.module.name)
        return "ref_type: %s| %s | method %s %s was moved to module %s " % (
            self._type, self._move, self._to, self._removed_m.get_path_string(),
            self._added_m.module.name)


class ExtractVarRef(Refactoring):
    def __str__(self):
        return "ref_type: Var%s| content %s was extracted to var %s in method %s" % (
            self._type, self._from.strip(), self._to, self._location)
