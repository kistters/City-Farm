import os
import shutil


def write_to_file(path, filename, contents):
    full_path = os.path.join(path, filename)
    if not os.path.exists(path):
        os.makedirs(path)

    with open(full_path, 'w') as file:
        file.write(contents)


def move_file(file_path, target_directory):
    if not os.path.exists(target_directory):
        os.makedirs(target_directory)

    shutil.move(file_path, target_directory)
