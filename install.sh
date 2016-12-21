#! /bin/bash

folder="$(date +%s)-git-reviewers"
output_path=${1:-/usr/bin}

touch $output_path/$folder && rm $output_path/$folder || {
	echo "You do not have write access to the output path: $output_path" 1>&2
	exit 1
}

which zip > /dev/null || {
	echo "Unable to find 'zip' command necessary for install" 1>&2
	exit 2
}


cd /tmp/

git clone https://github.com/johnnadratowski/git-reviewers.git $folder || {
	echo "Unable to clone repository for install" 1>&2
	exit 3
}

cd $folder

zip -r ../$folder.zip ./reviewers.py ./__main__.py ./python_lib/ || {
	echo "An error occurred creating git-reviewers executable" 1>&2
	exit 4
}

cd ..

echo '#!/usr/bin/env python' | cat - $folder.zip > $output_path/git-reviewers || {
	echo "An error occurred writing out executable to path" 1>&2
	exit 5
}

chmod +x $output_path/git-reviewers || {
	echo "Couldn't set permissions of output executable" 1>&2
	exit 6
}

