#!/bin/bash

# set the path, to avoid "dpkg: error: PATH is not set" error
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games

# change to the module directory
cd "$(dirname "$0")"

# reload the daemons to avoid "Warning: kolibri.service changed on disk" message
systemctl daemon-reload

# stop the Kolibri server so we can upgrade and configure the database
service kolibri stop

# upgrade Kolibri to the latest version
DEBIAN_FRONTEND=noninteractive dpkg --force-confnew -i kolibri.deb

# ensure Kolibri knows that we'll be running as root
echo -n "root" > /etc/kolibri/username

# ensure there is an entry for mounting /.data before the services, so they don't need customization
grep -E -q '^/dev/sda1' /etc/fstab || echo '/dev/sda1 /.data ext4 defaults 0 0' >> /etc/fstab

# switch Kolibri to run on port 9091, so nginx can proxy to it
sed -i '/^KOLIBRI_LISTEN_PORT=/ s/9090/9091/' /etc/kolibri/daemon.conf

# set up nginx config
cp kolibri_nginx_config /etc/nginx/sites-enabled/kolibri

# stop Kolibri again, as upgrading it may have restarted it
service kolibri stop

# check whether the database contains the bad facility (that was shared across all devices) and hasn't had any signups
# if so, we "deprovision" the database (remove the facility and user data, but leave the content)
DATASET_ID=$(echo "SELECT id FROM kolibriauth_facilitydataset;" | sqlite3 /root/.kolibri/db.sqlite3 | head -n 1)
USER_COUNT=$(echo "SELECT id FROM kolibriauth_facilityuser;" | sqlite3 /root/.kolibri/db.sqlite3 | wc -l)
if [[ "$DATASET_ID" == "7f85d2537b70968e56db641a07364200" && "$USER_COUNT" == "1" ]]
then
  echo "Database contains bad facility. Will now deprovision."
  cp -n /root/.kolibri/db.sqlite3 /root/.kolibri/db.sqlite3.bak
  yes yes | kolibri manage deprovision
else
  echo "Database does not contain bad facility. No need to do anything."
fi

# reload Nginx config and start Kolibri back up again
service nginx reload
service kolibri start
