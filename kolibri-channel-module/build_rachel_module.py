#!/usr/bin/env python
import glob
import os
import sqlite3
import subprocess
import tempfile
import yaml

from shutil import copy2

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError:
        pass

os.environ["KOLIBRI_RUN_MODE"] = "rachel-module-builder"

if __name__ == "__main__":

    LOCAL_CONTENT_SOURCE_DIR = os.getenv("KOLIBRI_LOCAL_CONTENT_SOURCE_DIR", None)
    TARGET_MODULE_DIR = os.getenv("KOLIBRI_TARGET_MODULE_DIR", "/var/modules")
    CHANNEL_ID = os.getenv("KOLIBRI_CHANNEL_ID", None)
    SOURCE_DIR = os.path.dirname(os.path.realpath(__file__))
    SOURCE_FILE_DIR = os.path.join(SOURCE_DIR, "files")

    if not os.path.isdir(TARGET_MODULE_DIR):
        raise Exception("KOLIBRI_TARGET_MODULE_DIR is set to {}, which isn't a directory...".format(TARGET_MODULE_DIR))

    with open(os.path.join(SOURCE_DIR, "channels.yml")) as f:
        ALL_CHANNEL_DATA = yaml.load(f)

    if CHANNEL_ID is None:
        raise Exception("Environment variable KOLIBRI_CHANNEL_ID must be set.")

    if CHANNEL_ID not in ALL_CHANNEL_DATA:
        raise Exception("KOLIBRI_CHANNEL_ID is set to {}, which is not defined in channels.yml".format(CHANNEL_ID))

    channel_data = ALL_CHANNEL_DATA[CHANNEL_ID]

    assert channel_data.get("language", "")
    assert channel_data.get("slug")

    # calculate the module name and directory, and create the module directory if needed
    module_name = "{language}-kolibri-channel-{slug}".format(**channel_data)
    module_dir = os.path.join(TARGET_MODULE_DIR, module_name)
    mkdir_p(module_dir)

    # set a temporary home directory for the module
    os.environ["KOLIBRI_HOME"] = os.path.join(SOURCE_DIR, "tmphomes", module_name)
    mkdir_p(os.environ["KOLIBRI_HOME"])
    copy2(os.path.join(SOURCE_DIR, "db.sqlite3"), os.path.join(os.environ["KOLIBRI_HOME"], "db.sqlite3"))
    
    # set the content destination to the folder inside the module
    os.environ["KOLIBRI_CONTENT_DIR"] = os.path.join(module_dir, "content")

    # download the latest channel metadata
    subprocess.Popen(["kolibri", "manage", "importchannel", "network", CHANNEL_ID]).wait()

    # import content files from a location on disk, if available?
    if LOCAL_CONTENT_SOURCE_DIR:
        subprocess.Popen(["kolibri", "manage", "importcontent", "disk", CHANNEL_ID, LOCAL_CONTENT_SOURCE_DIR]).wait()

    # download any new content files
    subprocess.Popen(["kolibri", "manage", "importcontent", "network", CHANNEL_ID]).wait()

    # read the channel info from the database
    conn = sqlite3.connect(os.path.join(module_dir, "content", "databases", CHANNEL_ID + ".sqlite3"))
    c = conn.cursor()
    version, name, description = c.execute("SELECT version, name, description FROM content_channelmetadata;").fetchone()

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

    # update the database with the module metadata
    # TODO!

