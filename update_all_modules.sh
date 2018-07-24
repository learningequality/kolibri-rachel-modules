#!/bin/bash

source /usr/share/virtualenvwrapper/virtualenvwrapper.sh
deactivate 2> /dev/null

pushd "$(dirname "$0")"

# make sure we're running the latest code
git pull

# make sure the deps are installed, and we're in the virtualenv
mkvirtualenv kolibri-rachel-modules
pip install -r requirements.txt

# build all the content channel modules
pushd kolibri-channel-module-template
KOLIBRI_CHANNEL_ID=* ./build_rachel_module.py
popd

# update the index modules
pushd en-kolibri-index
version=$(egrep "v[0-9]+\.[0-9]+" rachel-index.php -o)
cp * /var/modules/en-kolibri-index
cp * /var/modules/en-kolibri
ln -s rachel-index.php /var/modules/en-kolibri-index/index.htmlf
ln -s rachel-index.php /var/modules/en-kolibri/index.htmlf
echo "UPDATE modules SET version='$version', logofilename='kolibri-logo.svg' WHERE moddir = 'en-kolibri-index' OR moddir = 'en-kolibri';" | mysql rachelmods -u root
popd

# update the upgrade module
pushd multi-kolibri-upgrade
cp * /var/modules/multi-kolibri-upgrade
ln -s rachel-index.php /var/modules/multi-kolibri-upgrade/index.htmlf
version=$(curl "https://launchpad.net/~learningequality/+archive/ubuntu/kolibri" 2> /dev/null | egrep "[0-9]+\.[0-9]+\.[0-9]+-[0-9]*ubuntu[0-9]*" -o | head -n 1)
version="$version (`md5sum * 2> /dev/null | md5sum | cut -c1-6`)" # include a hash of the scripts to ensure we trigger an upgrade if those change too
echo '<!-- version="'$version'" -->' > /var/modules/multi-kolibri-upgrade/rachel-index.php
echo "UPDATE modules SET version='$version' WHERE moddir = 'multi-kolibri-upgrade';" | mysql rachelmods -u root
popd

# update the local upgrade module
pushd multi-kolibri-upgrade-local
cp * /var/modules/multi-kolibri-upgrade-local
ln -s rachel-index.php /var/modules/multi-kolibri-upgrade-local/index.htmlf
wget -O /var/modules/multi-kolibri-upgrade-local/kolibri.deb https://learningequality.org/r/kolibri-deb-latest
version=$(dpkg-deb -I /var/modules/multi-kolibri-upgrade-local/kolibri.deb | egrep "[0-9]+\.[0-9]+\.[0-9]+-[0-9]*ubuntu[0-9]*" -o | head -n 1)
version="$version (`md5sum * 2> /dev/null | md5sum | cut -c1-6`)" # include a hash of the scripts to ensure we trigger an upgrade if those change too
echo '<!-- version="'$version'" -->' > /var/modules/multi-kolibri-upgrade-local/rachel-index.php
echo "UPDATE modules SET version='$version' WHERE moddir = 'multi-kolibri-upgrade-local';" | mysql rachelmods -u root
popd

deactivate
popd