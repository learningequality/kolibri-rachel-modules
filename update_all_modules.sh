#!/bin/bash

pushd "$(dirname "$0")"

# make sure we're running the latest code
git pull

# make sure the deps are installed, and we're in the virtualenv
mkvirtualenv kolibri-rachel-modules
pip install -r requirements.txt

# build all the content channel modules
pushd _lang_-kolibri-channel-_slug_
KOLIBRI_CHANNEL_ID=* ./build_rachel_module.py
popd

# update the index modules
pushd en-kolibri-index
version=$(egrep "v[0-9]+\.[0-9]+" rachel-index.php -o)
cp * /var/modules/en-kolibri-index
cp * /var/modules/en-kolibri
echo "UPDATE modules SET version='$version' WHERE moddir = 'en-kolibri-index' OR moddir = 'en-kolibri';" | mysql rachelmods -u root
popd

# update the upgrade module
pushd multi-kolibri-upgrade
cp * /var/modules/multi-kolibri-upgrade
version=$(curl "https://launchpad.net/~learningequality/+archive/ubuntu/kolibri" 2> /dev/null | egrep "[0-9]+\.[0-9]+\.[0-9]+-[0-9]*ubuntu[0-9]*" -o | head -n 1)
echo '<!-- version="'$version'" -->' > rachel-index.php
echo "UPDATE modules SET version='$version' WHERE moddir = 'multi-kolibri-upgrade';" | mysql rachelmods -u root
popd

deactivate
popd