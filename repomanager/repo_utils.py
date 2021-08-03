import os
import git
from git import Repo
from os import path


def clone_repo(username, repo_name):
    git_url = 'https://github.com/' + username + '/' + repo_name + '.git'
    repo_path = os.path.abspath("./Repos/" + repo_name)
    if path.exists(repo_path):
        print("Repo Already Cloned.")
        return repo_path
    try:
        print("Cloning Repo...")

        repo = Repo.clone_from(git_url, repo_path, branch='main')
        return repo_path
    except git.exc.GitCommandError as e:
        repo = Repo.clone_from(git_url, repo_path, branch='master')
        return repo_path


def clone_repo_args(args):
    clone_repo(args.username, args.reponame)
