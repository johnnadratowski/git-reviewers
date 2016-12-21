# git-reviewers

**Tested on 2.7.12 and 3.5.2 but probably will work with >=2.5**

The premise of this tool is simple: Tell you who should review your PR.

When working on a large team or in a large company, sometimes its difficult to
tell who you should add as a reviewer to a pull request... especially when
your PR spans multiple files/modules.  Everyone can’t be monitoring for new
PRs all the time, especially across many codebases.

The theory behind this is that if you’re changing a line of code in the vicinity
of what someone has touched, maybe they should be notified of the PR for review.
It accomplishes this by using the `git blame` of the lines around the diff of
a branch.

## Installation

You can easily install the utility by running the following command:

```bash
```

Alternatively, you can clone the repo and run `install.sh` manually.

## Usage

```
# This will tell you the potential reviewers of the branch, orderd by most prolific against master
git reviewers -b master

# If you omit -b, it will default first to a `develop` (a la git flow) branch, 
# then to `master` if no `develop` branch exists
git reviewers

# If you only want to see suggested reviewers for certain files:
git reviewers app/test/testfoo.py app/test/testbar.py


