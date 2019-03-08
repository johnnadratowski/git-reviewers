import argparse
from os.path import abspath

from git_reviewers.reviewers import get_git_branches, get_reviewers


def run():
    parser = argparse.ArgumentParser(description="Get the suggested reviewers for a commit")
    parser.add_argument('--branch', '-b',
                        required=False,
                        help="Check for a PR against a specific branch")
    parser.add_argument('--contributor', '-c',
                        required=False,
                        help="View lines of code for a specific contributor")
    parser.add_argument('--output', '-o',
                        required=False,
                        default="default",
                        help="The output format: default|raw.  Raw dumps json in-memory data structures for debugging and"
                        "consumption by other applications.")
    parser.add_argument('files', metavar='file', type=str, nargs='*',
                        help='Only show reviewers for certain files. If none specified, shows reviewers for all files')
    args = parser.parse_args()


    if args.branch:
        branch = args.branch
    elif 'develop' in get_git_branches():
        branch = 'develop'
    else:
        branch = 'master'

    if args.files:
        args.files = [abspath(path) for path in args.files]

    get_reviewers(args.contributor, branch, args.files, args.output)
