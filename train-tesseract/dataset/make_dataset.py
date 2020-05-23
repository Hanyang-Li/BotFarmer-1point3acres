import os
import shutil
from zipfile import ZipFile

BLACKLIST = ['.DS_Store']
SOURCE = 'raw'
TARGET = 'ground-truth'

def remove(paths):
    for parent, dirs, files in os.walk('.'):
        for directory in [d for d in paths if d in dirs]:
            shutil.rmtree(directory)
        for file in [f for f in paths if f in files]:
            os.remove(file)

# Initialize work place
# Clear temporary directories and files
remove([SOURCE, TARGET, TARGET + '.zip'])
# Make new directories
os.mkdir(TARGET)
with ZipFile(SOURCE + '.zip', 'r') as zip_obj:
    zip_obj.extractall()

# Make dataset
# Save the data files to target directory
chars = [c for c in os.listdir(SOURCE) if c not in BLACKLIST]
for c in chars:
    label = c.rstrip('_')
    images = [i for i in os.listdir(os.path.join(SOURCE, c)) if i not in BLACKLIST]
    for i in range(len(images)):
        suffix = '_' if label.islower() else ''
        name = label + suffix + '-' + str(i).zfill(len(str(len(images))))
        shutil.copy(os.path.join(SOURCE, c, images[i]), os.path.join(TARGET, name + '.png'))
        with open(os.path.join(TARGET, name + '.gt.txt'), 'w') as file:
            file.write(label)
# Zip target directory
with ZipFile(TARGET + '.zip', 'w') as zip_obj:
    pre_len = len(os.path.dirname(TARGET))
    for parent, dirs, files in os.walk(TARGET):
        for file in files:
            path = os.path.join(parent, file)
            arcname = path[pre_len:].strip(os.path.sep)
            zip_obj.write(path, arcname)

# Remove temporary directories
remove([SOURCE, TARGET])