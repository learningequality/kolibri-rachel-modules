#!/bin/bash

# change to the module directory
cd "$(dirname "$0")"

# stop the Kolibri server so we can upgrade and configure the database
service kolibri stop

# upgrade Kolibri to the latest version
DEBIAN_FRONTEND=noninteractive dpkg -i kolibri.deb --force-confnew

# ensure Kolibri knows that we'll be running as root
echo -n "root" > /etc/kolibri/username

# stop Kolibri again, as upgrading it may have restarted it
service kolibri stop

# check whether the database contains the bad facility (that was shared across all devices) and hasn't had any signups
# if so, we "deprovision" the database (remove the facility and user data, but leave the content)
DATASET_ID=$(echo "SELECT id FROM kolibriauth_facilitydataset;" | sqlite3 /root/.kolibri/db.sqlite3 | head -n 1)
USER_COUNT=$(echo "SELECT id FROM kolibriauth_facilityuser;" | sqlite3 /root/.kolibri/db.sqlite3 | wc -l)
if [[ "$DATASET_ID" == "2637c9e5c23ed23603dbdced841f8a11" && "$USER_COUNT" == "1" ]]
then
  echo "Database contains bad facility. Will now deprovision."
  cp -n /root/.kolibri/db.sqlite3 /root/.kolibri/db.sqlite3.bak
  yes yes | kolibri manage deprovision
else
  echo "Database does not contain bad facility. No need to do anything."
fi

# start Kolibri back up again
service kolibri start
