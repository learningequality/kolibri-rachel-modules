import errno    
import os

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError:
        pass

# calculate the src (<module>/content) and dst (/root/.kolibri/content) content directories
kolibri_home = "/root/.kolibri"
dst_content_dir = os.path.join(kolibri_home, "content")
mod_dir = os.path.dirname(os.path.realpath(__file__))
src_content_dir = os.path.join(mod_dir, "content")

# remove destination content directory, but *only if it's a symlink* (due to legacy approach)
if os.path.islink(dst_content_dir):
    os.unlink(dst_content_dir)

print("Kolibri symlink process: Removed old content dir symlink if it existed")

# create /root/.kolibri/content if it doesn't exist
mkdir_p(dst_content_dir)

# recurse through the destination content directory and delete any broken symlinks
for subdir, _, files in os.walk(dst_content_dir):
    for filename in files:
        filepath = os.path.join(subdir, filename)
        if not os.path.exists(filepath):
            os.unlink(filepath)

print("Kolibri symlink process: Removed bad symlinks")

# recurse through the source content subdirectories, and for each directory:
#   - create corresponding directory in /root/.kolibri/content/ if it doesn't exist
#   - create symlinks to each of the files in the directory
os.chdir(src_content_dir)
for subdir, _, files in os.walk("."):
    src_dir = os.path.realpath(os.path.join(src_content_dir, subdir))
    dst_dir = os.path.realpath(os.path.join(dst_content_dir, subdir))
    mkdir_p(dst_dir)
    for filename in files:
        src_file = os.path.join(src_dir, filename)
        dst_file = os.path.join(dst_dir, filename)
        if not os.path.exists(dst_file):
            os.symlink(src_file, dst_file)

print("Kolibri symlink process: Created new symlinks")
