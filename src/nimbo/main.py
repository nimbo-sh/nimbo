import click

from nimbo.core import access, execute, storage, utils
from nimbo.core.globals import RequiredConfigCase


@click.group(context_settings=dict(max_content_width=150))
def cli():
    pass


@cli.command()
@utils.assert_required_config(RequiredConfigCase.NONE)
@utils.handle_errors
def generate_config():
    """Creates a base nimbo-config.yml in your current directory.

    Remember to change any fields to your own values.
    """
    utils.generate_config()


@cli.command()
@click.argument("job_cmd")
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredConfigCase.JOB)
@utils.handle_errors
def run(job_cmd, dry_run):
    """Runs the JOB_CMD command on an EC2 instance.

    JOB_CMD is any command you would run locally.\n
    E.g. \"python runner.py --epochs=10\".\n
    The command must be between quotes. 
    """
    execute.run_job(job_cmd, dry_run)


@cli.command()
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredConfigCase.JOB)
@utils.handle_errors
def launch(dry_run):
    """Launches an EC2 instance according to your nimbo-config, without doing any further setup."""
    execute.run_job("_nimbo_launch", dry_run)


@cli.command()
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredConfigCase.JOB)
@utils.handle_errors
def launch_and_setup(dry_run):
    """Launches an EC2 instance with your code, data and environment, without running any job."""
    execute.run_job("_nimbo_launch_and_setup", dry_run)


@cli.command()
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredConfigCase.INSTANCE)
@utils.handle_errors
def test_access(dry_run):
    """Runs a mock job to test your config file, permissions, and credentials."""
    execute.run_access_test(dry_run)


@cli.command()
@click.argument("instance_id")
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredConfigCase.INSTANCE)
@utils.handle_errors
def ssh(instance_id, dry_run):
    """SSH into an instance by INSTANCE_ID."""
    utils.ssh(instance_id, dry_run)


@cli.command()
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredConfigCase.MINIMAL)
@utils.handle_errors
def list_gpu_prices(dry_run):
    """Lists the prices, types, and specs of GPU instances."""
    utils.list_gpu_prices(dry_run)


@cli.command()
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredConfigCase.MINIMAL)
@utils.handle_errors
def list_spot_gpu_prices(dry_run):
    """Lists the prices, types, and specs of GPU spot instances."""
    utils.list_spot_gpu_prices(dry_run)


@cli.command()
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredConfigCase.MINIMAL)
@utils.handle_errors
def list_active(dry_run):
    """Lists all your active instances."""
    utils.show_active_instances(dry_run)


@cli.command()
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredConfigCase.MINIMAL)
@utils.handle_errors
def list_stopped(dry_run):
    """Lists all your stopped instances."""
    utils.show_stopped_instances(dry_run)


@cli.command()
@click.argument("instance_id")
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredConfigCase.MINIMAL)
@utils.handle_errors
def check_instance_status(instance_id, dry_run):
    """Checks the status of an instance by INSTANCE_ID."""
    utils.check_instance_status(instance_id, dry_run)


@cli.command()
@click.argument("instance_id")
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredConfigCase.MINIMAL)
@utils.handle_errors
def stop_instance(instance_id, dry_run):
    """Stops an instance by INSTANCE_ID."""
    utils.stop_instance(instance_id, dry_run)


@cli.command()
@click.argument("instance_id")
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredConfigCase.MINIMAL)
@utils.handle_errors
def delete_instance(instance_id, dry_run):
    """Terminates an instance by INSTANCE_ID."""
    utils.delete_instance(instance_id, dry_run)


@cli.command()
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredConfigCase.MINIMAL)
@utils.handle_errors
def delete_all_instances(dry_run):
    """Terminates all your instances."""
    click.confirm(
        "This will delete all your running instances.\n" "Do you want to continue?",
        abort=True,
    )
    utils.delete_all_instances(dry_run)


@cli.command()
@click.argument("bucket_name")
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredConfigCase.MINIMAL)
@utils.handle_errors
def create_bucket(bucket_name, dry_run):
    """Create a bucket BUCKET_NAME in S3.

    BUCKET_NAME is the name of the bucket to create, s3://BUCKET_NAME
    """
    storage.create_bucket(bucket_name, dry_run)


@cli.command()
@click.argument(
    "folder", type=click.Choice(["datasets", "results", "logs"]), required=True
)
@click.option(
    "--delete",
    is_flag=True,
    help="Deletes any files that exist in the local folder but don't exist in the remote folder.",
)
@utils.assert_required_config(RequiredConfigCase.STORAGE)
@utils.handle_errors
def push(folder, delete):
    """Push your local datasets/results folder onto S3."""
    storage.push(folder, delete)


@cli.command()
@click.argument(
    "folder", type=click.Choice(["datasets", "results", "logs"]), required=True
)
@click.option(
    "--delete",
    is_flag=True,
    help="Deletes any files that exist in the local folder but don't exist in the remote folder.",
)
@utils.assert_required_config(RequiredConfigCase.STORAGE)
@utils.handle_errors
def pull(folder, delete):
    """Pull the S3 datasets/results folder into your local computer."""
    storage.pull(folder, delete)


@cli.command()
@click.argument("path")
@utils.assert_required_config(RequiredConfigCase.MINIMAL)
@utils.handle_errors
def ls(path):
    """List the s3 objects in PATH.

    PATH is an s3 path of the form s3://bucket-name/my/files/path.
    """
    storage.ls(path)


@cli.command()
@click.argument("security_group")
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredConfigCase.MINIMAL)
@utils.handle_errors
def allow_current_ip(security_group, dry_run):
    """Adds the IP of the current machine to the allowed inbound rules of GROUP.

    GROUP is the security group to which the inbound rule will be added.
    """
    access.allow_inbound_current_ip(security_group, dry_run)


@cli.command()
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredConfigCase.MINIMAL)
@utils.handle_errors
def list_instance_profiles(dry_run):
    """Lists the instance profiles available in your account."""
    access.list_instance_profiles(dry_run)


@cli.command()
@click.argument("role_name")
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredConfigCase.MINIMAL)
@utils.handle_errors
def create_instance_profile(role_name, dry_run):
    """Creates an instance profile called NimboInstanceProfile with role ROLE_NAME.

    ROLE_NAME is the role to associate with the instance profile.
    """
    access.create_instance_profile(role_name, dry_run)


@cli.command()
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredConfigCase.MINIMAL)
@utils.handle_errors
def create_instance_profile_and_role(dry_run):
    """Creates an instance profile called NimboInstanceProfile and the associated role.

    The role created has full EC2 and S3 access.\n
    Only recommended for individual accounts with root access.
    """
    access.create_instance_profile_and_role(dry_run)
