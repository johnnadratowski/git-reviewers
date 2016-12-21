#! /bin/bash

which zip > /dev/null || {
	echo "Unable to find 'zip' command necessary for install" 1>&2
}

__folder="$(date +%s)-git-reviewers"

cd /tmp/

git clone https://github.com/johnnadratowski/git-reviewers.git $__folder || {
	echo "Unable to clone repository for install" 1>&2
}

