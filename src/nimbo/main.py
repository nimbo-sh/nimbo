import os
import sys
import yaml
import click
import boto3

from .core import config_utils
from .core.paths import NIMBO, CWD, CONFIG


class SessionAndConfig(object):
    def __init__(self):
        # Load yaml config file
        assert os.path.isfile(CONFIG), \
            f"Nimbo configuration file '{CONFIG}' not found.\n" \
            "You can run 'nimbo generate-config' for guided config file creation."

        with open(CONFIG, "r") as f:
            config = yaml.load(f, Loader=yaml.FullLoader)

        config = config_utils.fill_defaults(config)
        # config_utils.verify_correctness(config)
        print()

        session = boto3.Session(profile_name=config["aws_profile"], region_name=config["region_name"])

        # Add user-id to config
        config["user_id"] = session.client("sts").get_caller_identity()["UserId"]


pass_session_config = click.make_pass_decorator(SessionAndConfig, ensure=True)


@click.group()
def cli():
    click.echo("Running")


@cli.command()
def generate_config():
    config_utils.generate_config()


@cli.command()
@pass_session_config
@click.argument("job_cmd")
def run(sc, job_cmd):
    print(sc.session)
    print(sc.config)
    launch.run_job(sc.session, sc.config, job_cmd)


@cli.command()
@pass_session_config
def launch(sc):
    launch.run_job(sc.session, sc.config, "_nimbo_launch")


@cli.command()
@pass_session_config
def launch_and_setup(sc):
    launch.run_job(sc.session, sc.config, "_nimbo_launch_and_setup")


@cli.command()
@pass_session_config
def test_access(sc):
    launch.run_access_test(sc.session, sc.config)


@cli.command()
@pass_session_config
def ssh(sc):
    utils.ssh(sc.session, sc.config, args[1])


@cli.command()
@pass_session_config
def list_gpu_prices(sc):
    utils.list_gpu_prices(sc.session)


@cli.command()
@pass_session_config
def list_spot_gpu_prices(sc):
    utils.list_spot_gpu_prices(sc.session)


@cli.command()
@pass_session_config
def list_active(sc):
    utils.show_active_instances(sc.session, sc.config)


@cli.command()
@pass_session_config
def list_stopped(sc):
    utils.show_stopped_instances(sc.session, sc.config)


@cli.command()
@pass_session_config
@click.argument("instance_id")
def check_instance(sc, instance_id):
    utils.check_instance(sc.session, instance_id)


@cli.command()
@pass_session_config
@click.argument("instance_id")
def stop_instance(sc, instance_id):
    utils.stop_instance(sc.session, instance_id)


@cli.command()
@pass_session_config
@click.argument("instance_id")
def delete_instance(sc, instance_id):
    utils.delete_instance(sc.session, instance_id)


@cli.command()
@pass_session_config
def delete_all_instances(sc):
    utils.delete_all_instances(sc.session, sc.config)


@cli.command()
@pass_session_config
@click.argument("bucket_name")
def create_bucket(sc, bucket_name):
    storage.create_bucket(sc.session, bucket_name)


@cli.command()
@pass_session_config
@click.argument("folder", type=click.Choice(["datasets", "results"]), required=True)
def push(sc, folder):
    storage.push(sc.session, sc.config, folder)


@cli.command()
@pass_session_config
@click.argument("folder", type=click.Choice(["datasets", "results"]), required=True)
def pull(sc, folder):
    storage.pull(sc.session, sc.config, folder)


@cli.command()
@pass_session_config
@click.argument("path")
def pull(sc, path):
    storage.ls(sc.session, sc.config, path)


@cli.command()
@pass_session_config
@click.argument("security_group")
def allow_current_device(sc, security_group):
    access.allow_inbound_current_device(sc.session, security_group)


@cli.command()
@pass_session_config
def list_instance_profiles(sc):
    access.list_instance_profiles(sc.session)


@cli.command()
@pass_session_config
@click.argument("role_name")
def create_instance_profile(sc, role_name):
    access.create_instance_profile(sc.session, role_name)


@cli.command()
@pass_session_config
def create_instance_profile_and_role(sc):
    access.create_instance_profile_and_role(sc.session)
