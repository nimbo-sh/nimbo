import os
from os.path import join
from shutil import copy
import yaml


def copy_assets(assets):
    curr_folder_path = os.path.dirname(os.path.abspath(__file__))
    assets_path = join(curr_folder_path, "assets")
    dst = os.getcwd()
     
    if "key" in assets:
        key_names = [p for p in os.listdir(assets_path) if p[-4:] == ".pem"]
        for key_name in key_names:
            copy(join(assets_path, key_name), dst)
    if "config" in assets:
        copy(join(assets_path, "nimbo-config.yml"), dst)
    if "env" in assets:
        copy(join(assets_path, "env.yml"), dst)


def write_fake_file(path, text):
    with open(path, 'w') as f:
        f.write(text)


def set_yaml_value(file, key, value):
    with open(file, "r") as f:
        config = yaml.safe_load(f)

    config[key] = value

    with open(file, "w") as f:
        yaml.dump(config, f)
