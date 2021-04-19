import click

from nimbo.core import access, execute, storage, utils
from nimbo.core.session import *
from nimbo.core.telemetry import record_event


@click.group(context_settings=dict(max_content_width=150))
def cli():
    pass


@cli.command()
def generate_config():
    """Creates a base nimbo-config.yml in your current directory.

    Remember to change any fields to your own values.
    """
    config_utils.generate_config()


@cli.command()
@click.argument("job_cmd")
@click.option("--dry-run", is_flag=True)
def run(job_cmd, dry_run):
    """Runs the JOB_CMD command on an EC2 instance.

    JOB_CMD is any command you would run locally.\n
    E.g. \"python runner.py --epochs=10\".\n
    The command must be between quotes.
    """

    session, config = get_session_and_config_full_check()
    record_event("run", config)
    execute.run_job(session, config, job_cmd, dry_run)


@cli.command()
@click.option("--dry-run", is_flag=True)
def launch(dry_run):
    """Launches an EC2 instance according to your nimbo-config, without doing any further setup."""
    session, config = get_session_and_config_full_check()
    execute.run_job(session, config, "_nimbo_launch", dry_run)


@cli.command()
@click.option("--dry-run", is_flag=True)
def launch_and_setup(dry_run):
    """Launches an EC2 instance with your code, data and environment, without running any job."""
    session, config = get_session_and_config_full_check()
    execute.run_job(session, config, "_nimbo_launch_and_setup", dry_run)


@cli.command()
@click.option("--dry-run", is_flag=True)
def test_access(dry_run):
    """Runs a mock job to test your config file, permissions, and credentials."""
    session, config = get_session_and_config_instance_key()
    execute.run_access_test(session, config, dry_run)


@cli.command()
@click.argument("instance_id")
@click.option("--dry-run", is_flag=True)
def ssh(instance_id, dry_run):
    """SSH into an instance by INSTANCE_ID."""
    session, config = get_session_and_config_instance_key()
    utils.ssh(session, config, instance_id, dry_run)


@cli.command()
@click.option("--dry-run", is_flag=True)
def list_gpu_prices(dry_run):
    """Lists the prices, types, and specs of GPU instances."""
    session, config = get_session_and_config_minimal()
    utils.list_gpu_prices(session, dry_run)


@cli.command()
@click.option("--dry-run", is_flag=True)
def list_spot_gpu_prices(dry_run):
    """Lists the prices, types, and specs of GPU spot instances."""
    session, config = get_session_and_config_minimal()
    utils.list_spot_gpu_prices(session, dry_run)


@cli.command()
@click.option("--dry-run", is_flag=True)
def list_active(dry_run):
    """Lists all your active instances."""
    session, config = get_session_and_config_minimal()
    utils.show_active_instances(session, config, dry_run)


@cli.command()
@click.option("--dry-run", is_flag=True)
def list_stopped(dry_run):
    """Lists all your stopped instances."""
    session, config = get_session_and_config_minimal()
    utils.show_stopped_instances(session, config, dry_run)


@cli.command()
@click.argument("instance_id")
@click.option("--dry-run", is_flag=True)
def check_instance_status(instance_id, dry_run):
    """Checks the status of an instance by INSTANCE_ID."""
    session, config = get_session_and_config_minimal()
    utils.check_instance_status(session, config, instance_id, dry_run)


@cli.command()
@click.argument("instance_id")
@click.option("--dry-run", is_flag=True)
def stop_instance(instance_id, dry_run):
    """Stops an instance by INSTANCE_ID."""
    session, config = get_session_and_config_minimal()
    utils.stop_instance(session, instance_id, dry_run)


@cli.command()
@click.argument("instance_id")
@click.option("--dry-run", is_flag=True)
def delete_instance(instance_id, dry_run):
    """Terminates an instance by INSTANCE_ID."""
    session, config = get_session_and_config_minimal()
    utils.delete_instance(session, instance_id, dry_run)


@cli.command()
@click.option("--dry-run", is_flag=True)
def delete_all_instances(dry_run):
    """Terminates all your instances."""
    click.confirm(
        "This will delete all your running instances.\n" "Do you want to continue?",
        abort=True,
    )
    session, config = get_session_and_config_minimal()
    utils.delete_all_instances(session, config, dry_run)


@cli.command()
@click.argument("bucket_name")
@click.option("--dry-run", is_flag=True)
def create_bucket(bucket_name, dry_run):
    """Create a bucket BUCKET_NAME in S3.

    BUCKET_NAME is the name of the bucket to create, s3://BUCKET_NAME
    """
    session, config = get_session_and_config_minimal()
    storage.create_bucket(session, bucket_name, dry_run)


@cli.command()
@click.argument(
    "folder", type=click.Choice(["datasets", "results", "logs"]), required=True
)
@click.option(
    "--delete",
    is_flag=True,
    help="Deletes any files that exist in the local folder but don't exist in the remote folder.",
)
def push(folder, delete):
    """Push your local datasets/results folder onto S3."""
    if delete:
        click.confirm(
            "This will delete any files that exist in the remote folder but do not exist in the local folder.\n" "Do you want to continue?",
            abort=True,
        )
    session, config = get_session_and_config_storage()
    storage.push(session, config, folder, delete)


@cli.command()
@click.argument(
    "folder", type=click.Choice(["datasets", "results", "logs"]), required=True
)
@click.option(
    "--delete",
    is_flag=True,
    help="Deletes any files that exist in the local folder but don't exist in the remote folder.",
)
def pull(folder, delete):
    """Pull the S3 datasets/results folder into your local computer."""
    if delete:
        click.confirm(
            "This will delete any files that exist in the local folder but do not exist in the remote folder.\n" "Do you want to continue?",
            abort=True,
        )
    session, config = get_session_and_config_storage()
    storage.pull(session, config, folder, delete)


@cli.command()
@click.argument("path")
def ls(path):
    """List the s3 objects in PATH.

    PATH is an s3 path of the form s3://bucket-name/my/files/path.
    """
    session, config = get_session_and_config_minimal()
    storage.ls(session, config, path)


@cli.command()
@click.argument("security_group")
@click.option("--dry-run", is_flag=True)
def allow_current_ip(security_group, dry_run):
    """Adds the IP of the current machine to the allowed inbound rules of GROUP.

    GROUP is the security group to which the inbound rule will be added.
    """
    session, config = get_session_and_config_minimal()
    access.allow_inbound_current_ip(session, security_group, dry_run)


@cli.command()
@click.option("--dry-run", is_flag=True)
def list_instance_profiles(dry_run):
    """Lists the instance profiles available in your account."""
    session, config = get_session_and_config_minimal()
    access.list_instance_profiles(session, dry_run)


@cli.command()
@click.argument("role_name")
@click.option("--dry-run", is_flag=True)
def create_instance_profile(role_name, dry_run):
    """Creates an instance profile called NimboInstanceProfile with role ROLE_NAME.

    ROLE_NAME is the role to associate with the instance profile.
    """

    session, config = get_session_and_config_minimal()
    access.create_instance_profile(session, role_name, dry_run)


@cli.command()
@click.option("--dry-run", is_flag=True)
def create_instance_profile_and_role(dry_run):
    """Creates an instance profile called NimboInstanceProfile and the associated role.

    The role created has full EC2 and S3 access.\n
    Only recommended for individual accounts with root access.
    """
    session, config = get_session_and_config_minimal()
    access.create_instance_profile_and_role(session, dry_run)
