#!/bin/bash

# change to the module directory
cd "$(dirname "$0")"

# since content will be temporarily unavilable, and we'll be using the database, safest to stop Kolibri during this process
service kolibri stop

# create the symlinks to connect the content in this module into the main content directory
python establish_content_symlinks.py

# if versions have changed on existing channels in the database, delete as needed to trigger a re-import
for database in content/databases/*.sqlite3; do
    channelid=$(echo "SELECT id FROM content_channelmetadata;" | sqlite3 $database)
    echo "Checking whether channel $channelid has changed..."
    newchannelversion=$(echo "SELECT version FROM content_channelmetadata;" | sqlite3 $database)
    oldchannelversion=$(echo "SELECT version FROM content_channelmetadata WHERE id = '$channelid';" | sqlite3 /root/.kolibri/db.sqlite3)
    if [ "$newchannelversion" != "$oldchannelversion" ]; then
        echo "\tAttempting upgrade to channel version $newchannelversion..."

        echo "
try:
    from kolibri.core.content.utils.channel_import import *
    from kolibri.core.content.utils.annotation import *
except ImportError:
    from kolibri.content.utils.channel_import import *
    from kolibri.content.utils.annotation import *

channel_id = '$channelid'

import_manager = initialize_import_manager(channel_id)
import_manager.import_channel_data()
import_manager.end()

set_availability(channel_id)
        " | kolibri shell

    fi
done

# start things back up again
service kolibri start
