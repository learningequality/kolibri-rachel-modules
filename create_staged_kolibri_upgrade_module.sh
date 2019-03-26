#!/bin/bash

source /usr/share/virtualenvwrapper/virtualenvwrapper.sh
deactivate 2> /dev/null

pushd "$(dirname "$0")"

# make sure we're running the latest code
git pull

# make sure the deps are installed, and we're in the virtualenv
mkvirtualenv kolibri-rachel-modules
pip install -r requirements.txt

# update the upgrade module
pushd zz-kolibri-upgrade
cp * /var/staging_mods/zz-kolibri-upgrade
wget -O /var/staging_mods/zz-kolibri-upgrade/kolibri.deb https://learningequality.org/r/kolibri-deb-latest
version=$(dpkg-deb -I /var/staging_mods/zz-kolibri-upgrade/kolibri.deb | egrep "[0-9]+\.[0-9]+\.[0-9]+-[0-9]*ubuntu[0-9]*" -o | head -n 1)
version="${version}-`md5sum * 2> /dev/null | md5sum | cut -c1-6`" # include a hash of the scripts to ensure we trigger an upgrade if those change too
echo '<!-- version="'$version'" -->' > /var/staging_mods/zz-kolibri-upgrade/rachel-index.php
ln -s rachel-index.php /var/staging_mods/zz-kolibri-upgrade/index.htmlf
popd

deactivate
popd