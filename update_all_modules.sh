#!/bin/bash

source /usr/share/virtualenvwrapper/virtualenvwrapper.sh
deactivate 2> /dev/null

pushd "$(dirname "$0")"

# make sure we're running the latest code
git pull

# make sure the deps are installed, and we're in the virtualenv
mkvirtualenv kolibri-rachel-modules
pip install -r requirements.txt

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
pushd zz-kolibri-upgrade
cp * /var/modules/zz-kolibri-upgrade
wget -O /var/modules/zz-kolibri-upgrade/kolibri.deb https://learningequality.org/r/kolibri-deb-latest
version=$(dpkg-deb -I /var/modules/zz-kolibri-upgrade/kolibri.deb | egrep "[0-9]+\.[0-9]+\.[0-9]+-[0-9]*ubuntu[0-9]*" -o | head -n 1)
version="${version}-`md5sum * 2> /dev/null | md5sum | cut -c1-6`" # include a hash of the scripts to ensure we trigger an upgrade if those change too
echo '<!-- version="'$version'" -->' > /var/modules/zz-kolibri-upgrade/rachel-index.php
ln -s rachel-index.php /var/modules/zz-kolibri-upgrade/index.htmlf
echo "UPDATE modules SET version='$version' WHERE moddir = 'zz-kolibri-upgrade';" | mysql rachelmods -u root
popd

# build all the content channel modules
pushd kolibri-channel-module-template
KOLIBRI_CHANNEL_ID=* ./build_rachel_module.py
popd

deactivate
popd