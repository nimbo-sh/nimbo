import click
import boto3

from .core import access, utils, storage, launch, config_utils


def get_session_and_config(required_fields, fields_to_check):
    config = config_utils.load_config()

    config = config_utils.fill_defaults(config)
    config_utils.ConfigVerifier(config).verify(required_fields, fields_to_check)

    session = boto3.Session(profile_name=config["aws_profile"], region_name=config["region_name"])

    # Add user-id to config
    config["user_id"] = session.client("sts").get_caller_identity()["UserId"]

    return session, config


def get_session_and_config_full_check():
    return get_session_and_config("all", "all")


def get_session_and_config_instance_key():
    return get_session_and_config(["aws_profile", "region_name", "instance_key"], ["instance_key"])


def get_session_and_config_minimal():
    return get_session_and_config(["aws_profile", "region_name"], [])


@click.group()
def cli():
    pass


@cli.command()
def generate_config():
    config_utils.generate_config()


@cli.command()
@click.argument("job_cmd")
def run(job_cmd):
    session, config = get_session_and_config_full_check()
    launch.run_job(session, config, job_cmd)


@cli.command()
def launch():
    session, config = get_session_and_config_full_check()
    launch.run_job(session, config, "_nimbo_launch")


@cli.command()
def launch_and_setup():
    session, config = get_session_and_config_full_check()
    launch.run_job(session, config, "_nimbo_launch_and_setup")


@cli.command()
def test_access():
    session, config = get_session_and_config_full_check()
    launch.run_access_test(session, config)


@cli.command()
@click.argument("instance_id")
def ssh(instance_id):
    session, config = get_session_and_config_instance_key()
    utils.ssh(session, config, instance_id)


@cli.command()
def list_gpu_prices():
    session, config = get_session_and_config_minimal()
    utils.list_gpu_prices(session)


@cli.command()
def list_spot_gpu_prices():
    session, config = get_session_and_config_minimal()
    utils.list_spot_gpu_prices(session)


@cli.command()
def list_active():
    session, config = get_session_and_config_minimal()
    utils.show_active_instances(session, config)


@cli.command()
def list_stopped():
    session, config = get_session_and_config_minimal()
    utils.show_stopped_instances(session, config)


@cli.command()
@click.argument("instance_id")
def check_instance(instance_id):
    session, config = get_session_and_config_minimal()
    utils.check_instance(session, instance_id)


@cli.command()
@click.argument("instance_id")
def stop_instance(instance_id):
    session, config = get_session_and_config_minimal()
    utils.stop_instance(session, instance_id)


@cli.command()
@click.argument("instance_id")
def delete_instance(instance_id):
    session, config = get_session_and_config_minimal()
    utils.delete_instance(session, instance_id)


@cli.command()
def delete_all_instances():
    session, config = get_session_and_config_minimal()
    utils.delete_all_instances(session, config)


@cli.command()
@click.argument("bucket_name")
def create_bucket(bucket_name):
    session, config = get_session_and_config_minimal()
    storage.create_bucket(session, bucket_name)


@cli.command()
@click.argument("folder", type=click.Choice(["datasets", "results"]), required=True)
def push(folder):
    session, config = get_session_and_config_minimal()
    storage.push(session, config, folder)


@cli.command()
@click.argument("folder", type=click.Choice(["datasets", "results"]), required=True)
def pull(folder):
    session, config = get_session_and_config_minimal()
    storage.pull(session, config, folder)


@cli.command()
@click.argument("path")
def ls(path):
    session, config = get_session_and_config_minimal()
    storage.ls(session, config, path)


@cli.command()
@click.argument("security_group")
def allow_current_device(security_group):
    session, config = get_session_and_config_minimal()
    access.allow_inbound_current_device(session, security_group)


@cli.command()
def list_instance_profiles():
    session, config = get_session_and_config_minimal()
    access.list_instance_profiles(session)


@cli.command()
@click.argument("role_name")
def create_instance_profile(role_name):
    session, config = get_session_and_config_minimal()
    access.create_instance_profile(session, role_name)


@cli.command()
def create_instance_profile_and_role():
    session, config = get_session_and_config_minimal()
    access.create_instance_profile_and_role(session)
