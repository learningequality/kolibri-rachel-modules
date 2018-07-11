#!/usr/bin/env python
import glob
import hashlib
import MySQLdb
import os
import requests
import sqlite3
import subprocess
import tempfile
import yaml

from datauri import DataURI
from shutil import copy2

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError:
        pass

def du(path):
    """disk usage in kilobytes"""
    return subprocess.check_output(['du','-sk', path]).split()[0].decode('utf-8')

def filecount(path):
    """number of files (recursively)"""
    return len(subprocess.check_output(['find', path, '-type', 'f']).strip().split("\n"))

os.environ["KOLIBRI_RUN_MODE"] = "rachel-module-builder"

if __name__ == "__main__":

    LOCAL_CONTENT_SOURCE_DIR = os.getenv("KOLIBRI_LOCAL_CONTENT_SOURCE_DIR", None)
    CHANNEL_ID = os.getenv("KOLIBRI_CHANNEL_ID", None)
    SOURCE_DIR = os.path.dirname(os.path.realpath(__file__))
    SOURCE_FILE_DIR = os.path.join(SOURCE_DIR, "files")
    TARGET_MODULE_DIR = os.path.join(SOURCE_DIR, os.getenv("KOLIBRI_TARGET_MODULE_DIR", "/var/modules"))

    if not os.path.isdir(TARGET_MODULE_DIR):
        raise Exception("KOLIBRI_TARGET_MODULE_DIR is set to {}, which isn't a directory...".format(TARGET_MODULE_DIR))

    with open(os.path.join(SOURCE_DIR, "channels.yml")) as f:
        ALL_CHANNEL_DATA = yaml.load(f)

    if CHANNEL_ID is None:
        raise Exception("Environment variable KOLIBRI_CHANNEL_ID must be set.")

    if CHANNEL_ID in ["*", "all"]:
        channel_ids = ALL_CHANNEL_DATA.keys()
    else:
        if CHANNEL_ID not in ALL_CHANNEL_DATA:
            raise Exception("KOLIBRI_CHANNEL_ID is set to {}, which is not defined in channels.yml".format(CHANNEL_ID))
        channel_ids = [CHANNEL_ID]

    for channel_id in channel_ids:

        channel_data = ALL_CHANNEL_DATA[channel_id]

        assert channel_data.get("language", "")
        assert channel_data.get("slug")

        # calculate the module name and directory, and create the module directory if needed
        module_name = "{language}-kolibri-channel-{slug}".format(**channel_data)
        module_dir = os.path.join(TARGET_MODULE_DIR, module_name)
        mkdir_p(module_dir)
        channel_database_path = os.path.join(module_dir, "content", "databases", channel_id + ".sqlite3")

        # set a temporary home directory for the module
        os.environ["KOLIBRI_HOME"] = os.path.join(SOURCE_DIR, "tmphomes", module_name)
        mkdir_p(os.environ["KOLIBRI_HOME"])
        primary_database_path = os.path.join(os.environ["KOLIBRI_HOME"], "db.sqlite3")
        copy2(os.path.join(SOURCE_DIR, "db.sqlite3"), primary_database_path)

        # set the content destination to the folder inside the module
        os.environ["KOLIBRI_CONTENT_DIR"] = os.path.join(module_dir, "content")

        # determine whether we need to import the channel again
        if os.path.isfile(channel_database_path):

            # get the version in the downloaded database file
            conn = sqlite3.connect(channel_database_path)
            c = conn.cursor()
            module_ver = c.execute("SELECT version FROM content_channelmetadata;").fetchone()[0]
            conn.close()

            # get the version in the cached primary database
            conn = sqlite3.connect(primary_database_path)
            c = conn.cursor()
            ver_results = c.execute("SELECT version FROM content_channelmetadata WHERE id = '{}';".format(channel_id)).fetchone()
            primary_ver = ver_results[0] if ver_results else -1
            conn.close()

            # fetch the version number on Studio
            chdata = requests.get("https://studio.learningequality.org/api/public/v1/channels/lookup/" + channel_id).json()[0]
            remote_ver = chdata.get("version")

            channel_update_needed = (module_ver != remote_ver) or (primary_ver != remote_ver)

        else:

            channel_update_needed = True

        # download the latest channel metadata, if needed
        if channel_update_needed:
            subprocess.Popen(["kolibri", "manage", "importchannel", "network", channel_id]).wait()

        # import content files from a location on disk, if available?
        if LOCAL_CONTENT_SOURCE_DIR:
            subprocess.Popen(["kolibri", "manage", "importcontent", "disk", channel_id, LOCAL_CONTENT_SOURCE_DIR]).wait()

        # download any new content files
        subprocess.Popen(["kolibri", "manage", "importcontent", "network", channel_id]).wait()

        # read the channel info from the database
        conn = sqlite3.connect(channel_database_path)
        c = conn.cursor()
        channel_version, name, description, thumbnail = c.execute("SELECT version, name, description, thumbnail FROM content_channelmetadata;").fetchone()
        license = c.execute("SELECT license_name FROM content_contentnode GROUP BY license_name ORDER BY -count(license_name);").fetchone()[0] or ""
        if license.startswith("CC"):
            license = "({} 4.0)".format(license)
        else:
            license = None
        conn.close()

        # construct the version from the channel_version combined with a hash of the files we'll be copying in, so it'll update if either changes
        for filename in glob.glob(os.path.join(SOURCE_FILE_DIR, "*")):
            data = ""
            with open(filename, 'rb') as inputfile:
                data += inputfile.read()
            filehashes = hashlib.md5(data).hexdigest()[:6]
        version = "{}-{}".format(channel_version, filehashes)

        # remove the existing files in the top level of the module
        for filename in os.listdir(module_dir):
            filepath = os.path.join(module_dir, filename)
            if not os.path.isdir(filepath):
                os.remove(filepath)

        # output a rachel-index.php file, plus index.htmlf symlink
        with open(os.path.join(module_dir, "rachel-index.php"), "w") as f:
            f.write('<!-- version="{version}" -->'.format(version=version))
        os.symlink("rachel-index.php", os.path.join(module_dir, "index.htmlf"))

        # copy in the files from files/
        for filename in os.listdir(SOURCE_FILE_DIR):
            srcpath = os.path.join(SOURCE_FILE_DIR, filename)
            dstpath = os.path.join(module_dir, filename)
            copy2(srcpath, dstpath)

        # write the channel thumbnail into the module directory
        if thumbnail:
            uri = DataURI(thumbnail)
            extension = uri.mimetype.split("/")[-1]
            thumb_filename = "thumbnail." + extension
            with open(os.path.join(module_dir, thumb_filename), "w") as f:
                f.write(uri.data)
        else:
            thumb_filename = ""

        # update the database with the module metadata
        try:
            data = {
                "title": name + u" - Kolibri",
                "description": description,
                "moddir": module_name,
                "lang": channel_data.get("language"),
                "source_url": "", # TODO (if we had a Kolibri page showing channel info, could link there)
                "ksize": du(module_dir),
                "file_count": filecount(module_dir),
                "type": "kolibri",
                "cc_license": license,
                # "prereq_id": , # TODO (depend on multi-kolibri-upgrade?)
                # "prereq_note": ,
                "logofilename": thumb_filename,
                "version": version,
            }
            keys = "({})".format(", ".join(data.keys()))
            values = "({})".format(", ".join("%s" for val in data.values()))
            update = ", ".join("{key}=VALUES({key})".format(key=key) for key in data.keys())
            sql = "INSERT INTO modules {} VALUES {} ON DUPLICATE KEY UPDATE {};".format(keys, values, update)
            db = MySQLdb.connect("localhost", "root", "", "rachelmods", charset="utf8mb4", use_unicode=True)
            cursor = db.cursor()
            cursor.execute(sql, tuple(data.values()))
            db.close()
        except MySQLdb.OperationalError as e:
            print("ERROR: Unable to update module in database: {}".format(e))

