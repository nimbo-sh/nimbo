import os
from os.path import join
from shutil import copy


def copy_assets(assets):
    curr_folder_path = os.path.dirname(os.path.abspath(__file__))
    assets_path = join(curr_folder_path, "assets")
    dst = os.getcwd()
     
    if "key" in assets:
        copy(join(assets_path, "employee-instance-key.pem"), dst)
    if "config" in assets:
        copy(join(assets_path, "nimbo-config.yml"), dst)
    if "env" in assets:
        copy(join(assets_path, "env.yml"), dst)
