import os

from .ami.catalog import AMI_MAP

VALID_FIELDS = [
    "local_results_path", "local_datasets_path",
    "s3_results_path",  "s3_datasets_path",
    "aws_profile", "region_name", "instance_type",
    "spot", "spot_duration",
    "image", "disk_size", "conda_env",
    "run_in_background", "delete_when_done", "delete_on_error",
    "security_group", "instance_key"
]


def verify_correctness(config):

    # Set of elements that are in config.keys() but not in VALID_FIELDS
    invalid_fields = set(config.keys()).difference(set(VALID_FIELDS))
    assert len(invalid_fields) == 0, f"Invalid nimbo-config.yml fields: {list(invalid_fields)}"

    if config["image"][:4] != "ami-":
        assert config["image"] in AMI_MAP, \
            "The image requested doesn't exist. " \
            "Please check this link for a list of supported images."

    assert "instance_key" in config
    instance_key_name = config["instance_key"]
    assert os.path.isfile(instance_key_name + ".pem"), \
        f"The instance key file '{instance_key_name}' wasn't found in the current directory."

    assert "conda_env" in config
    assert os.path.isfile(config["conda_env"]), \
        "Conda env file '{}' not found in the current folder.".format(config["conda_env"])


def fill_defaults(config):
    config_defaults = {
        "spot": False,
        "spot_duration": 0,
        "image": "ubuntu18-cuda10.2-cudnn7.6-conda4.9.2",
        "disk_size": 128,
        "run_in_background": False,
        "delete_when_done": True,
        "delete_on_error": True,
        "security_group": "default"
    }

    config_defaults.update(config)
    return config_defaults


def generate_config():
    config = """# Data paths
local_datasets_path: data/datasets
local_results_path: data/results
s3_datasets_path: s3://my-bucket/my-project/data/datasets
s3_results_path: s3://my-bucket/my-project/data/results

# Device, environment and regions
aws_profile: default
region_name: eu-west-1
instance_type: p2.xlarge
spot: no
#spot_duration: 60

image: ubuntu18-drivers460
disk_size: 128
conda_env: your-conda-file.yml

# Job options
run_in_background: no
delete_when_done: yes 
delete_on_error: yes

# Permissions and credentials
security_group: default
instance_key: your-ec2-key-pair  # without .pem """

    with open("nimbo-config.yml", "w") as f:
        f.write(config)

    print("Boilerplate config written to nimbo-config.yml.")
