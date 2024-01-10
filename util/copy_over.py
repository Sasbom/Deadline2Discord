import shutil
import os

container_folder = os.path.abspath(f"{__file__}/..")
destination_path = None

with open(f"{container_folder}\\destination.txt") as f:
    destination_path = f.readline(-1)
    destination_path = destination_path.translate(str.maketrans('', '', ' \n\t\r'))
    destination_path = os.path.normpath(destination_path)

if not destination_path:
    exit()

source_folder = f"{__file__}/../../Deadline/events/Discord"
source_folder = os.path.abspath(source_folder)

for dirpath, dirnames, filenames in os.walk(source_folder):
    for file, to_file in ((os.path.join(dirpath,f), os.path.join(destination_path,f)) for f in filenames):        
        print(file, to_file)
        shutil.copy2(file, to_file)