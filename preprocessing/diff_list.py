import json
import time
from os import path

from preprocessing.revision import Rev
from preprocessing.conditions_match import *
from ast import *
import os

from preprocessing.utils import to_tree


def build_diff_lists(changes_path, commit=None, directory=None):
    refactorings = []
    t0 = time.time()
    if commit is not None:
        print(commit)
        name = commit + ".csv"
        df = pd.read_csv(changes_path + "/" + name)
        if directory is not None:
            df = df[df["Path"].isin(directory)]
        rev_a = Rev()
        rev_b = Rev()
        df.apply(lambda row: populate(row, rev_a, rev_b), axis=1)
        # try:
        rev_difference = rev_a.revision_difference(rev_b)
        refs = rev_difference.get_refactorings()
        for ref in refs:
            refactorings.append((ref, name.split(".")[0]))
            print(">>>", str(ref))
    else:
        for root, dirs, files in os.walk(changes_path):
            for name in files:
                if name.endswith(".csv"):
                    print(name)
                    df = pd.read_csv(changes_path + "/" + name)
                    if directory is not None:
                        df = df[df["Path"].isin(directory)]
                    rev_a = Rev()
                    rev_b = Rev()
                    df.apply(lambda row: populate(row, rev_a, rev_b), axis=1)
                    try:
                        rev_difference = rev_a.revision_difference(rev_b)
                        refs = rev_difference.get_refactorings()
                        for ref in refs:
                            refactorings.append((ref, name.split(".")[0]))
                            print(">>>", str(ref))
                    except Exception as e:
                        print("Failed to process commit.", e)

    t1 = time.time()
    total = t1 - t0
    print("-----------------------------------------------------------------------------------------------------------")
    print("Total Time:", total)
    print("Total Number of Refactorings:", len(refactorings))
    refactorings.sort(key=lambda x: x[1])
    json_outputs = []
    for ref in refactorings:
        print("commit: %3s - %s" % (ref[1], str(ref[0]).strip()))
        data = ref[0].to_json_format()
        data["Commit"] = ref[1]
        json_outputs.append(data)
        # ref[0].to_graph()
    repo_name = changes_path.split("/")[-3]
    with open(repo_name + '_data.json', 'w') as outfile:
        outfile.write(json.dumps(json_outputs, indent=4))

    return refactorings


def extract_refs(args):
    # owner_name = args.repo.split("/")[0]
    # repo_name = args.repo.split("/")[1]

    from repomanager import repo_utils, repo_changes

    repo_path = args.repopath

    if args.commit is not None:
        repo_changes.all_commits(repo_path, [args.commit])
        print("\nExtracting Refs...")
        build_diff_lists(repo_path + "/changes/", args.commit, args.directory)
    else:
        print("\nExtracting commit history...")
        repo_changes.all_commits(repo_path)
        print("\nExtracting Refs...")
        build_diff_lists(repo_path + "/changes/", args.directory)


def validate(args):
    validations = pd.read_csv(args.path)
    validations["correct"] = validations["correct"].apply(lambda x: 'true' if x == 1 else 'false')
    validations = validations.groupby(['commit']).agg(lambda x: ','.join(x)).reset_index()
    validations["project"] = validations["project"].apply(lambda x: x.split(",")[0])
    validations = validations.to_dict("records")

    from repomanager import repo_utils, repo_changes

    for validation in validations:
        if validation["commit"] == "bf9c26bb128d50ff8369c3bc7fbfc63d066d1ea8" or not "false" in validation["correct"]:
            continue

        repo = validation["project"].split("_")
        print(
            "-----------------------------------------------------------------------------------------------------------")
        print("Cloning %s/%s" % (repo[0], repo[1]))
        repo_utils.clone_repo(repo[0], repo[1])

        while not path.exists("./Repos/" + repo[1]):
            time.sleep(1)

        path_to_repo = "./Repos/" + repo[1]
        repo_changes.all_commits(path_to_repo, [validation["commit"]])

        while not path.exists("./Repos/" + repo[1] + "/changes/" + validation["commit"] + ".csv"):
            time.sleep(1)

        print("Validation of %s: %s" % (validation["type"], validation["correct"]))

        changes_path = "./Repos/" + repo[1] + "/changes/"
        build_diff_lists(changes_path, validation["commit"])


def populate(row, rev_a, rev_b):
    path = row["Path"]
    rav_a_tree = to_tree(eval(row["oldFileContent"]))
    rev_b_tree = to_tree(eval(row["currentFileContent"]))
    rev_a.extract_code_elements(rav_a_tree, path)
    rev_b.extract_code_elements(rev_b_tree, path)


def build_diff_lists_args(args):
    build_diff_lists(args.path, args.commit)
