from dataclasses import dataclass

from preprocessing.refactoring_heuristics import extract_method_ref, method_signature_change_ref, inline_method_ref, \
    move_method_ref, change_class_signature


@dataclass
class DiffRev:
    common_modules: list
    added_modules: list
    removed_modules: list
    diff_common_modules: list

    def get_refactorings(self):
        refactorings = []

        for diff_module in self.diff_common_modules:
            refactorings = refactorings + diff_module.get_refactorings()  # append

        refactorings = refactorings + move_method_ref(self.diff_common_modules)
        return refactorings


@dataclass
class DiffModule:
    common_classes: list
    added_classes: list
    removed_classes: list
    diff_common_classes: list
    common_methods: list
    added_methods: list
    removed_methods: list

    def get_refactorings(self):
        refactorings = []

        for diff_class in self.diff_common_classes:
            refactorings = refactorings + diff_class.get_refactorings()

        refactorings = refactorings + \
                       method_signature_change_ref(self.added_methods, self.removed_methods,
                                                   self.common_methods) + change_class_signature(self.removed_classes,
                                                                                                 self.added_classes,
                                                                                                 self.common_classes) + \
                       extract_method_ref(self.common_methods, self.added_methods) + inline_method_ref(
            self.common_methods, self.removed_methods)

        return refactorings


@dataclass
class DiffClass:
    common_methods: list
    added_methods: list
    removed_methods: list

    def get_refactorings(self):
        refactorings = []
        refactorings = refactorings + method_signature_change_ref(self.added_methods, self.removed_methods,
                                                                  self.common_methods) + \
                       extract_method_ref(self.common_methods, self.added_methods) + inline_method_ref(
            self.common_methods, self.removed_methods)
        return refactorings
