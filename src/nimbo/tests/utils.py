import os
from os.path import join
from shutil import copy


def copy_assets(assets):
    curr_folder_path = os.path.dirname(os.path.abspath(__file__))
    assets_path = join(curr_folder_path, "assets")
    dst = os.getcwd()
     
    if "key" in assets:
        key_name = [p for p in os.listdir(assets_path) if p[-4:] == ".pem"][0]
        copy(join(assets_path, key_name), dst)
    if "config" in assets:
        copy(join(assets_path, "nimbo-config.yml"), dst)
    if "env" in assets:
        copy(join(assets_path, "env.yml"), dst)
