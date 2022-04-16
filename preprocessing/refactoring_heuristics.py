import ast
import pandas as pd
import editdistance
from preprocessing.refactorings_info import RefInfo
from preprocessing.conditions_match import body_mapper
from preprocessing.refactorings import ExtractInlineRef, RenameRef, MoveRef, ClassRef, ExtractVarRef
from preprocessing.utils import intersection, get_stmts_recursive, is_extracted


def extract_method_ref(common_methods, added_methods):
    refs = []

    for tuple_m in common_methods:
        for added_m in added_methods[:]:
            method1 = tuple_m[0]
            method2 = tuple_m[1]
            if not method1.calls(added_m) and method1.class_node == added_m.class_node and method2.calls(added_m):
                mapped_stmts = body_mapper(tuple_m, added_m, RefInfo.EXTRACT)
                if len(mapped_stmts.index) == 0:
                    continue

                method1_stmts = [{"stmt1": str(stmt)} for stmt in method1.get_all_stmts()]
                method2_stmts = [{"stmt1": str(stmt)} for stmt in method2.get_all_stmts()]

                method1_stmts_df = pd.DataFrame(method1_stmts).groupby("stmt1")["stmt1"].agg('count').reset_index(
                    name="count")
                method2_stmts_df = pd.DataFrame(method2_stmts).groupby("stmt1")["stmt1"].agg('count').reset_index(
                    name="count")

                stmts_merge = method1_stmts_df.merge(method2_stmts_df, how="outer", on="stmt1").fillna(0)

                mapped_stmts_agg = mapped_stmts.groupby("stmt1")["stmt1"].agg('count').reset_index(name="count")

                mapped_stmts_merge = mapped_stmts_agg.merge(stmts_merge, how="outer", on="stmt1").dropna()

                to_remove = mapped_stmts_merge[~(
                        abs(mapped_stmts_merge["count"] - mapped_stmts_merge["count_x"]) >= mapped_stmts_merge[
                    "count_y"])]["stmt1"].tolist()

                mapped_stmts = mapped_stmts[~(mapped_stmts["stmt1"].isin(to_remove))]

                mapped_stmts_len = len(mapped_stmts[~mapped_stmts.type.str.contains("inner")].index)

                method2_unmapped = added_m.get_total_stmts_count() - mapped_stmts_len
                if mapped_stmts_len >= method2_unmapped:
                    added_methods.remove(added_m)
                    refs.append(
                        ExtractInlineRef(method1.name, added_m.name, "Extract Method", added_m.get_path(), mapped_stmts,
                                         tuple_m, added_m))
    return refs


def change_class_signature(removed_classes: list, added_classes: list, common_classes: list):
    refs = []
    sub_refs = []
    for removed_class in removed_classes[:]:
        for added_class in added_classes[:]:

            removed_class_methods = set([method.name for method in removed_class.methods])
            added_class_methods = set([method.name for method in added_class.methods])
            removed_class_fields = set(removed_class.fields)
            added_class_fields = set(added_class.fields)

            common_methods_len = len(removed_class_methods.intersection(added_class_methods))
            total_methods_len = len(removed_class_methods) if len(removed_class_methods) > len(
                added_class_methods) else len(added_class_methods)

            if ((removed_class_methods.issubset(added_class_methods) or added_class_methods.issubset(
                    removed_class_methods)) and (
                        removed_class_fields.issubset(added_class_fields) or added_class_fields.issubset(
                    removed_class_fields))) or (common_methods_len > total_methods_len / 2 and (
                    removed_class_fields.issubset(added_class_fields) or added_class_fields.issubset(
                removed_class_fields))):
                if not (removed_class.name == added_class.name):
                    if not total_methods_len == 0:
                        matched_method_ratio = common_methods_len / total_methods_len
                    else:
                        matched_method_ratio = 0
                    sub_refs.append({"Removed Class": removed_class.name, "Added Class": added_class.name,
                                     "Matched Method": matched_method_ratio,
                                     "Name Similarity": editdistance.eval(added_class.name, removed_class.name),
                                     "Ref": ClassRef(removed_class.name, added_class.name, "Rename Class",
                                                     added_class.module.name)})
                if not (removed_class.module.name == added_class.module.name):
                    sub_refs.append({"Removed Class": removed_class.name, "Added Class": added_class.name,
                                     "Matched Method": matched_method_ratio,
                                     "Name Similarity": editdistance.eval(added_class.name, removed_class.name),
                                     "Ref": ClassRef(removed_class.name, added_class.name, "Move Class",
                                                     added_class.module.name)})

    sub_refs = pd.DataFrame(sub_refs)
    if len(sub_refs.index) > 0:
        sub_refs = sub_refs.sort_values(["Matched Method", "Name Similarity"], ascending=[False, True]).groupby(
            'Added Class').head(1)
        sub_refs = sub_refs.sort_values(["Matched Method", "Name Similarity"], ascending=[False, True]).groupby(
            'Removed Class').head(1)

        refs = sub_refs["Ref"].tolist()
        # remove class and add to common

    return refs


def inline_method_ref(common_methods, removed_methods):
    refs = []
    for tuple_m in common_methods:
        for removed_m in removed_methods[:]:
            method1 = tuple_m[0]
            adjacent_method = tuple_m[1]
            if method1.calls(removed_m) and adjacent_method.class_node == removed_m.class_node and \
                    not adjacent_method.calls(removed_m):
                mapped_stmts = body_mapper(tuple_m, removed_m, RefInfo.INLINE)
                if len(mapped_stmts.index) == 0:
                    continue

                method1_stmts = [{"stmt1": str(stmt)} for stmt in method1.get_all_stmts()]
                method2_stmts = [{"stmt1": str(stmt)} for stmt in adjacent_method.get_all_stmts()]

                method1_stmts_df = pd.DataFrame(method1_stmts).groupby("stmt1")["stmt1"].agg('count').reset_index(
                    name="count")
                method2_stmts_df = pd.DataFrame(method2_stmts).groupby("stmt1")["stmt1"].agg('count').reset_index(
                    name="count")

                stmts_merge = method1_stmts_df.merge(method2_stmts_df, how="outer", on="stmt1").fillna(0)

                mapped_stmts_agg = mapped_stmts.groupby("stmt1")["stmt1"].agg('count').reset_index(name="count")

                mapped_stmts_merge = mapped_stmts_agg.merge(stmts_merge, how="outer", on="stmt1").dropna()

                to_remove = mapped_stmts_merge[~(
                        abs(mapped_stmts_merge["count"] + mapped_stmts_merge["count_x"]) <= mapped_stmts_merge[
                    "count_y"])]["stmt1"].tolist()

                mapped_stmts = mapped_stmts[~(mapped_stmts["stmt1"].isin(to_remove))]
                mapped_stmts_len = len(mapped_stmts[~mapped_stmts.type.str.contains("inner")].index)
                method1_unmapped = adjacent_method.get_total_stmts_count() - mapped_stmts_len
                method2_unmapped = removed_m.get_total_stmts_count() - mapped_stmts_len
                if mapped_stmts_len > method2_unmapped:
                    removed_methods.remove(removed_m)
                    refs.append(
                        ExtractInlineRef(method1.name, removed_m.name, "Inline Method", removed_m.get_path(),
                                         mapped_stmts,
                                         tuple_m, removed_m))
                    break
    return refs


def move_method_ref(diff_common_element):
    diff_common_element = diff_common_element[:]
    refs = []

    removed_methods = []
    added_methods = []
    for diff_element in diff_common_element:
        removed_methods.extend(diff_element.removed_methods)
        added_methods.extend(diff_element.added_methods)
        for sub_diff_element in diff_element.diff_common_classes:
            removed_methods.extend(sub_diff_element.removed_methods)
            added_methods.extend(sub_diff_element.added_methods)
    for removed_method in removed_methods:
        metrics = []
        sub_refs = []
        for added_method in added_methods:
            mapped_stmts = body_mapper(removed_method, added_method, RefInfo.RENAME)
            if len(mapped_stmts.index) == 0:
                continue
            mapped_stmts_len = len(mapped_stmts[~mapped_stmts.type.str.contains("inner")].index)
            method1_unmapped = abs(removed_method.get_total_stmts_count() - mapped_stmts_len)
            method2_unmapped = abs(added_method.get_total_stmts_count() - mapped_stmts_len)
            if mapped_stmts_len >= method1_unmapped and mapped_stmts_len >= method2_unmapped and added_method.name == removed_method.name:
                priority = len(mapped_stmts[mapped_stmts['replacements'].isnull()])
                total_distance = mapped_stmts["distance"].sum()
                if len(metrics) == 0:
                    metrics = [priority / mapped_stmts_len, total_distance, mapped_stmts_len]
                else:
                    if not (priority / mapped_stmts_len >= metrics[0] and total_distance <= metrics[
                        1] and mapped_stmts_len >= metrics[2]):
                        continue
                    else:
                        sub_refs = []
                        metrics = [priority / mapped_stmts_len, total_distance, mapped_stmts_len]
                _move = "None"
                if not (removed_method.module.name == added_method.module.name):
                    if removed_method.class_node is not None and added_method.class_node is not None:
                        if added_method.class_node.name in removed_method.class_node.bases:
                            _move = "Pull Up"
                        if removed_method.class_node.name in added_method.class_node.bases:
                            _move = "Push Down"
                    sub_refs.append(
                        MoveRef(removed_method.name, added_method.name, "Move Method", added_method.get_path(),
                                removed_method.get_path(), _move, mapped_stmts, removed_method,
                                added_method))
                    # break

                elif removed_method.class_node is not None and added_method.class_node is not None:
                    if not (removed_method.class_node == added_method.class_node):
                        if added_method.class_node.name in removed_method.class_node.bases:
                            _move = "Pull Up"
                        if removed_method.class_node.name in added_method.class_node.bases:
                            _move = "Push Down"
                        sub_refs.append(
                            MoveRef(removed_method.name, added_method.name, "Move Method", added_method.get_path(),
                                    removed_method.get_path(), _move, mapped_stmts, removed_method,
                                    added_method))
                    # break
                elif removed_method.class_node is not None or added_method.class_node is not None:
                    sub_refs.append(
                        MoveRef(removed_method.name, added_method.name, "Move Method", added_method.get_path(),
                                removed_method.get_path(), _move, mapped_stmts, removed_method,
                                added_method))
                    # break
        refs = refs + sub_refs

    return refs


def method_signature_change_ref(added_methods, removed_methods, common_methods):
    refs = []
    matched_methods = pd.DataFrame(
        columns=['from', 'to', 'ref_type', 'priority', 'total_distance', 'path', 'm1', 'm2', 'mapped_stmts', 'param_change'])
    mapped_stmts = []
    for removed_method in removed_methods:
        for added_m in added_methods:
            mapped_stmts = body_mapper(removed_method, added_m, RefInfo.RENAME)
            if len(mapped_stmts.index) == 0:
                continue
            # mapped_stmts_index = len(mapped_stmts.apply(lambda row: not ("inner" in row["type"]), axis=1))
            mapped_stmts_len = len(mapped_stmts[~mapped_stmts.type.str.contains("inner")].index)
            method1_unmapped = abs(removed_method.get_total_stmts_count() - mapped_stmts_len)
            method2_unmapped = abs(added_m.get_total_stmts_count() - mapped_stmts_len)
            other_added_methods = [added_m for added_m in added_methods if not added_m.name == added_m.name]
            extracted_refs = extract_method_ref([(removed_method, added_m)], other_added_methods)
            refs.extend(extracted_refs)
            if added_m.class_node == removed_method.class_node and \
                    ((method1_unmapped == 0 and method2_unmapped == 0) or (
                            (mapped_stmts_len >= method1_unmapped and mapped_stmts_len >= method2_unmapped) and
                            (set(added_m.params).issuperset(set(removed_method.params)) or
                             set(removed_method.params).issuperset(set(added_m.params)) or
                             len(intersection(set(added_m.params), set(removed_method.params))) >
                             len(set(added_m.params + removed_method.params).difference(
                                 intersection(set(added_m.params), set(removed_method.params))))))
                     or (len(extracted_refs) >= 1 and mapped_stmts_len > method2_unmapped)
                    ):

                _changes = []
                _param_change = []
                if not added_m.name == removed_method.name:
                    _changes.append("Rename Method")
                if len(set(added_m.params).difference(set(removed_method.params))) > 0 or len(set(removed_method.params).difference(set(added_m.params))) > 0:
                    pre_params = [i for i in removed_method.params if i not in added_m.params]
                    post_params = [i for i in added_m.params if i not in removed_method.params]
                    if len(set(added_m.params)) > len(set(removed_method.params)):
                        _changes.append("Add Parameter")
                        _param_change = [post_params[len(pre_params):]]
                        # _param_change = [set(added_m.params).difference(removed_method.params)]
                    elif len(set(added_m.params)) < len(set(removed_method.params)):
                        _changes.append("Remove Parameter")
                        _param_change = [pre_params[len(post_params):]]
                        # _param_change = [set(removed_method.params).difference(added_m.params)]
                    else:
                        _changes.append("Change/Rename Parameter")
                        _param_change = [pre_params, post_params]
                        # _param_change = [set(removed_method.params).difference(added_m.params),
                        #                  set(added_m.params).difference(removed_method.params)]
                if not added_m.return_type() == removed_method.return_type():
                    _changes.append("Change Return Type")

                priority = len(mapped_stmts[mapped_stmts['replacements'].isnull()])
                total_distance = mapped_stmts["distance"].sum()
                common_methods.append((removed_method, added_m))
                if len(_changes) > 0:
                    matched_methods = matched_methods.append(
                        {"from": removed_method.name, "to": added_m.name,
                         "ref_type": _changes,
                         "priority": priority, "total_distance": total_distance, "path": added_m.get_path(),
                         "m1": removed_method,
                         "m2": added_m, 'mapped_stmts': mapped_stmts, 'param_change': _param_change},
                        ignore_index=True
                    )

    if len(matched_methods.index) > 0:
        gp = matched_methods.groupby(['from'])

        toKeep = []

        for name, group in gp:
            toKeep.append(
                group.sort_values(['priority', 'total_distance'], ascending=[False, True]).iloc[0])

        matched_methods = pd.DataFrame(toKeep)  # FURTHER CHECK
        toKeep = []

        gp = matched_methods.groupby(['to'])

        for name, group in gp:
            toKeep.append(
                group.sort_values(['priority', 'total_distance'], ascending=[False, True]).iloc[0])

        matched_methods = pd.DataFrame(toKeep)

    matched_methods = matched_methods.values.tolist()

    for matched_method in matched_methods:
        refs.append(
            RenameRef(matched_method[0], matched_method[1], matched_method[2], matched_method[5], matched_method[-1],
                      matched_method[6], matched_method[7], matched_method[9]))
        added_m_rm = [added_m for added_m in added_methods if added_m.name == matched_method[1]]
        remove_m_rm = [removed_m for removed_m in removed_methods if removed_m.name == matched_method[0]]

        if len(added_m_rm) > 0 and len(remove_m_rm) > 0:
            added_methods.remove(added_m_rm[0])
            removed_methods.remove(remove_m_rm[0])
    return refs
