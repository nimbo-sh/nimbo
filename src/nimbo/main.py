import click

from nimbo.core import utils
from nimbo.core.click_extensions import HelpSection, NimboCommand, NimboGroup
from nimbo.core.cloud_provider import Cloud
from nimbo.core.config import RequiredCase

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"], max_content_width=90)


@click.group(cls=NimboGroup, context_settings=CONTEXT_SETTINGS)
def cli():
    """
    Run compute jobs on AWS as if you were running them locally.

    Visit https://docs.nimbo.sh for more help.
    """
    pass


@cli.command(cls=NimboCommand, help_section=HelpSection.INSTANCE)
@click.argument("job_cmd")
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredCase.JOB)
@utils.handle_errors
def run(job_cmd, dry_run):
    """Runs the JOB_CMD command on an EC2 instance.

    JOB_CMD is any command you would run locally.\n
    E.g. \"python runner.py --epochs=10\".\n
    The command must be between quotes.
    """
    Cloud.run(job_cmd, dry_run)


@cli.command(cls=NimboCommand, help_section=HelpSection.INSTANCE)
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredCase.JOB)
@utils.handle_errors
def launch(dry_run):
    """
    Launches an EC2 instance according to your nimbo-config,
    without doing any further setup.
    """
    Cloud.run("_nimbo_launch", dry_run)


@cli.command(cls=NimboCommand, help_section=HelpSection.INSTANCE)
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredCase.JOB)
@utils.handle_errors
def launch_and_setup(dry_run):
    """
    Launches an EC2 instance with your code, data and environment,
    without running any job.
    """
    Cloud.run("_nimbo_launch_and_setup", dry_run)


@cli.command(cls=NimboCommand, help_section=HelpSection.INSTANCE)
@click.argument("instance_id")
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredCase.INSTANCE)
@utils.handle_errors
def ssh(instance_id, dry_run):
    """SSH into an instance by INSTANCE_ID."""
    Cloud.ssh(instance_id, dry_run)


@cli.command(cls=NimboCommand, help_section=HelpSection.INSTANCE)
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredCase.JOB)
@utils.handle_errors
def notebook(dry_run):
    """
    Launches jupyter lab on an EC2 instance with your code, data and environment.

    Make sure to run 'nimbo sync-notebooks <instance_id>' frequently to sync
    the notebook to your local folder, as the remote notebooks will be lost
    once the instance is terminated.
    """
    Cloud.run("_nimbo_notebook", dry_run)


@cli.command(cls=NimboCommand, help_section=HelpSection.INSTANCE)
@click.argument("instance_id")
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredCase.MINIMAL)
@utils.handle_errors
def get_status(instance_id, dry_run):
    """Checks the status of an instance by INSTANCE_ID."""
    print(Cloud.get_status(instance_id, dry_run))


@cli.command(cls=NimboCommand, help_section=HelpSection.INSTANCE)
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredCase.MINIMAL)
@utils.handle_errors
def ls_active(dry_run):
    """Lists all your active instances."""
    Cloud.ls_active_instances(dry_run)


@cli.command(cls=NimboCommand, help_section=HelpSection.INSTANCE)
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredCase.MINIMAL)
@utils.handle_errors
def ls_stopped(dry_run):
    """Lists all your stopped instances."""
    Cloud.ls_stopped_instances(dry_run)


@cli.command(cls=NimboCommand, help_section=HelpSection.INSTANCE)
@click.argument("instance_id")
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredCase.MINIMAL)
@utils.handle_errors
def rm_instance(instance_id, dry_run):
    """Terminates an instance by INSTANCE_ID."""
    Cloud.delete_instance(instance_id, dry_run)


@cli.command(cls=NimboCommand, help_section=HelpSection.INSTANCE)
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredCase.MINIMAL)
@utils.handle_errors
def rm_all_instances(dry_run):
    """Terminates all your instances."""
    click.confirm(
        "This will delete all your running instances.\n" "Do you want to continue?",
        abort=True,
    )
    Cloud.delete_all_instances(dry_run)


@cli.command(cls=NimboCommand, help_section=HelpSection.INSTANCE)
@click.argument("instance_id")
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredCase.MINIMAL)
@utils.handle_errors
def stop_instance(instance_id, dry_run):
    """Stops an instance by INSTANCE_ID."""
    Cloud.stop_instance(instance_id, dry_run)


@cli.command(cls=NimboCommand, help_section=HelpSection.INSTANCE)
@click.argument("security_group")
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredCase.MINIMAL)
@utils.handle_errors
def add_current_ip(security_group, dry_run):
    """Adds the IP of the current machine to the allowed inbound rules of GROUP.

    GROUP is the security group to which the inbound rule will be added.
    """
    Cloud.allow_ingress_current_ip(security_group, dry_run)


@cli.command(cls=NimboCommand, help_section=HelpSection.STORAGE)
@click.argument("bucket_name")
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredCase.MINIMAL)
@utils.handle_errors
def mk_bucket(bucket_name, dry_run):
    """
    Create a bucket BUCKET_NAME in S3.

    BUCKET_NAME is the name of the bucket to create, s3://BUCKET_NAME
    """
    Cloud.mk_bucket(bucket_name, dry_run)


@cli.command(cls=NimboCommand, help_section=HelpSection.STORAGE)
@click.argument("path")
@utils.assert_required_config(RequiredCase.MINIMAL)
@utils.handle_errors
def ls(path):
    """List the s3 objects in PATH.

    PATH is an s3 path of the form s3://bucket-name/my/files/path.
    """
    Cloud.ls(path)


@cli.command(cls=NimboCommand, help_section=HelpSection.STORAGE)
@click.argument(
    "folder", type=click.Choice(["datasets", "results", "logs"]), required=True
)
@click.option(
    "--delete",
    is_flag=True,
    help="""
      Deletes any files that exist in the local folder
      but don't exist in the remote folder.
    """,
)
@utils.assert_required_config(RequiredCase.STORAGE)
@utils.handle_errors
def push(folder, delete):
    """Push your local datasets/results folder onto S3."""

    if delete:
        click.confirm(
            "This will delete any files that exist in the remote "
            "folder but do not exist in the local folder.\n"
            "Do you want to continue?",
            abort=True,
        )
    Cloud.push(folder, delete)


@cli.command(cls=NimboCommand, help_section=HelpSection.STORAGE)
@click.argument(
    "folder", type=click.Choice(["datasets", "results", "logs"]), required=True
)
@click.option(
    "--delete",
    is_flag=True,
    help="""
      Deletes any files that exist in the local
      folder but don't exist in the remote folder.
    """,
)
@utils.assert_required_config(RequiredCase.STORAGE)
@utils.handle_errors
def pull(folder, delete):
    """Pull the S3 datasets/results folder into your local computer."""

    if delete:
        click.confirm(
            "This will delete any files that exist in the local "
            "folder but do not exist in the remote folder.\n"
            "Do you want to continue?",
            abort=True,
        )
    Cloud.pull(folder, delete)


@cli.command(cls=NimboCommand, help_section=HelpSection.STORAGE)
@click.argument("instance_id")
@utils.assert_required_config(RequiredCase.INSTANCE)
@utils.handle_errors
def sync_notebooks(instance_id):
    """
    Syncs the ipynb files from the instance INSTANCE_ID to your local folder.

    Make sure to run 'nimbo sync-notebooks <instance_id>' to sync the notebook
    to your local folder, as the remote notebooks will be lost once the instance
    is terminated.
    """
    Cloud.sync_notebooks(instance_id)


@cli.command(cls=NimboCommand, help_section=HelpSection.UTILS)
@utils.assert_required_config(RequiredCase.NONE)
@utils.handle_errors
def generate_config():
    """Creates a base nimbo-config.yml in your current directory.

    Remember to change any fields to your own values.
    """
    utils.generate_config()


@cli.command(cls=NimboCommand, help_section=HelpSection.UTILS)
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredCase.INSTANCE, RequiredCase.STORAGE)
@utils.handle_errors
def test_access(dry_run):
    """Runs a mock job to test your config file, permissions, and credentials."""
    Cloud.run_access_test(dry_run)


@cli.command(cls=NimboCommand, help_section=HelpSection.UTILS)
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredCase.MINIMAL)
@utils.handle_errors
def ls_gpu_prices(dry_run):
    """Lists the prices, types, and specs of GPU instances."""
    Cloud.ls_gpu_prices(dry_run)


@cli.command(cls=NimboCommand, help_section=HelpSection.UTILS)
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredCase.MINIMAL)
@utils.handle_errors
def ls_spot_gpu_prices(dry_run):
    """Lists the prices, types, and specs of GPU spot instances."""
    Cloud.ls_spot_gpu_prices(dry_run)


@cli.command(cls=NimboCommand, help_section=HelpSection.UTILS)
@click.argument("qty", type=int, required=True)
@click.argument("timescale", type=click.Choice(["days", "months"]), required=True)
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredCase.MINIMAL)
@utils.handle_errors
def spending(qty, timescale, dry_run):
    """Shows daily/monthly spending summary. Costs without credits or refunds applied.

    QTY is the number of days/months you want to see, starting from the current date.\n
    For example:\n
        'nimbo spending 10 days' will show daily spending of the last 10 days\n
        'nimbo spending 3 months' will show the monthly spending of the last 3 months
    """
    Cloud.spending(qty, timescale, dry_run)


@cli.command(cls=NimboCommand, help_section=HelpSection.ADMIN)
@click.argument("profile")
@click.option("--full-s3-access", is_flag=True)
@utils.assert_required_config(RequiredCase.NONE)
@utils.handle_errors
def admin_setup(profile, full_s3_access):
    Cloud.setup(profile, full_s3_access)


@cli.command(cls=NimboCommand, help_section=HelpSection.ADMIN)
@click.argument("username")
@click.argument("profile")
@utils.assert_required_config(RequiredCase.NONE)
@utils.handle_errors
def add_user(username, profile):
    """Adds user USERNAME to the user group NimboUserGroup.

    You must have run 'nimbo admin-setup' before adding users.

    PROFILE is the profile name of your root/admin account.
    """
    Cloud.add_user(username, profile)
