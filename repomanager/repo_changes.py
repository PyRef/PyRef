import ast
import os
import astunparse
import pandas as pd
from git import Repo


# get the the changes in the latest commits and store them in a dataframe
def last_commit_changes(repo_path):
    modified_files = []
    repo = Repo(repo_path)
    for item in repo.head.commit.diff('HEAD~1').iter_change_type('M'):  # TODO: for now only modified files
        path = item.a_path
        if path.endswith('.py'):
            old_file_content = ast.dump(ast.parse(repo.git.show(f'HEAD~1:{path}')))
            current_file_content = ast.dump(ast.parse(repo.git.show(f'HEAD:{path}')))
            modified_files.append(
                {"Path": path, "oldFileContent": old_file_content, "currentFileContent": current_file_content})
    df = pd.DataFrame(modified_files)
    df.to_csv("changes.csv", index=False)
    return df


def all_commits(repo_path, specific_commits=None):
    repo = Repo(repo_path)

    path_to_create = repo_path + "/changes/"

    try:
        os.mkdir(path_to_create)
    except OSError:
        print("Commit history already extracted, updating data.")

    commits = []
    for commit in repo.iter_commits():
        if specific_commits is not None:
            if str(commit) in specific_commits:
                commits.append(commit)
        else:
            commits.append(commit)
    for count, commit in enumerate(commits):
        modified_files = []
        if len(commit.parents) == 0 or len(commit.parents) > 1:
            continue
        for item in commit.diff(commit.parents[0]).iter_change_type('M'):
            path = item.a_path
            if path.endswith('.py'):
                try:
                    old_file_content = ast.dump(ast.parse(repo.git.show('%s:%s' % (commit.parents[0].hexsha,
                                                                                   item.a_path))),
                                                include_attributes=True)
                    current_file_content = ast.dump(ast.parse(repo.git.show('%s:%s' % (commit.hexsha,
                                                                                       item.a_path))),
                                                    include_attributes=True)
                except Exception as e:
                    continue
                modified_files.append(
                    {"Path": path, "oldFileContent": old_file_content, "currentFileContent": current_file_content})

                df = pd.DataFrame(modified_files)
                df.to_csv(repo_path + "/changes/" + str(commit) + ".csv", index=False)


def repo_changes_args(args):
    if args.lastcommit:
        last_commit_changes(args.path)
    if args.allcommits:
        all_commits(args.path)
