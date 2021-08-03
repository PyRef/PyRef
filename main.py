import argparse
import sys


def repo_changes_access(args):
    from repomanager import repo_changes
    repo_changes.repo_changes_args(args)


def clone_repo_access(args):
    from repomanager import repo_utils
    repo_utils.clone_repo_args(args)


def build_diff_lists_access(args):
    from preprocessing import diff_list
    diff_list.build_diff_lists_args(args)


def validate_results(args):
    from preprocessing import diff_list
    diff_list.validate(args)


def extract_refs(args):
    from preprocessing import diff_list
    diff_list.extract_refs(args)


parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers()

clone_repo = subparsers.add_parser('repoClone', help='clone repo')
clone_repo.add_argument('-u', '--username', required=True, help='repo owner')
clone_repo.add_argument('-r', '--reponame', required=True, help='repo name')
clone_repo.set_defaults(func=clone_repo_access)

repo_changes = subparsers.add_parser('repoChanges', help='get changes in repo')
repo_changes.add_argument('-p', '--path', required=True, help='path of the repo')
repo_changes.add_argument('-l', '--lastcommit', action='store_true', help='changes between last commits')
repo_changes.add_argument('-al', '--allcommits', action='store_true', help='changes among all commits')
repo_changes.set_defaults(func=repo_changes_access)

diff_list = subparsers.add_parser('reflist', help='build the diff lists')
diff_list.add_argument('-p', '--path', required=True, help='path of the df (csv)')
diff_list.add_argument('-c', '--commit', required=False, help='specific commit hash')
diff_list.set_defaults(func=build_diff_lists_access)

validate_res = subparsers.add_parser('validate', help='validate results')
validate_res.add_argument('-p', '--path', required=True, help='path of the validation csv file')
validate_res.set_defaults(func=validate_results)

extract_ref = subparsers.add_parser('getrefs', help='validate results')
extract_ref.add_argument('-r', '--repopath', required=True, help='path to the repo')
extract_ref.add_argument('-c', '--commit', required=False, help='specific commit hash')
extract_ref.add_argument('-d', '--directory', required=False, help='specific directories', nargs='+')
extract_ref.set_defaults(func=extract_refs)


def main():
    if len(sys.argv) <= 1:
        sys.argv.append('--help')

    options = parser.parse_args()
    options.func(options)


if __name__ == '__main__':
    main()
