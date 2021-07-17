import os

import click

from nimbo import assert_required_config, set_config, cloud_context, IS_TEST_ENV
from nimbo.core.click_extensions import (
    HelpSection,
    NimboCommand,
    NimboGroup,
    pprint_errors,
)
from nimbo.core import utils
from nimbo.core.config import RequiredCase, make_config

_CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"], max_content_width=90)
_CONFIG_PATH_OVERRIDE = (
    os.environ["NIMBO_CONFIG"] if "NIMBO_CONFIG" in os.environ else "nimbo-config.yml"
)


@click.group(cls=NimboGroup, context_settings=_CONTEXT_SETTINGS)
@click.option(
    "-c",
    "--config",
    type=click.Path(),
    default=_CONFIG_PATH_OVERRIDE,
    show_default=True,
)
def cli(config):
    """
    Run compute jobs on AWS as if you were running them locally.

    Visit https://docs.nimbo.sh for more help.
    """

    if not IS_TEST_ENV:
        global _CONFIG_PATH_OVERRIDE
        _CONFIG_PATH_OVERRIDE = config

        set_config(config_factory=make_config, config_path=config)


@cli.command(cls=NimboCommand, help_section=HelpSection.INSTANCE)
@click.argument("job_cmd")
@click.option("--dry-run", is_flag=True)
@assert_required_config(RequiredCase.JOB)
@pprint_errors
@cloud_context
def run(cloud, job_cmd, dry_run):
    """Run JOB_CMD on an instance.

    JOB_CMD is any command you would run locally.
    E.g. \"python runner.py --epochs=10\".\n
    The command must be between quotes.
    """
    cloud.run(job_cmd, dry_run)


@cli.command(
    cls=NimboCommand,
    help_section=HelpSection.INSTANCE,
    short_help="Launch Jupiter with your code, data, and environment",
)
@click.option("--dry-run", is_flag=True)
@assert_required_config(RequiredCase.JOB)
@pprint_errors
@cloud_context
def notebook(cloud, dry_run):
    """
    Launch Jupyter Lab on an instance with your code, data and environment.

    Make sure to run 'nimbo sync-notebooks <instance_id>' frequently to sync
    the notebook to your local folder, as the remote notebooks will be lost
    once the instance is terminated.
    """
    cloud.run("_nimbo_notebook", dry_run)


@cli.command(
    cls=NimboCommand,
    help_section=HelpSection.INSTANCE,
    short_help="Launch an instance with minimal setup.",
)
@click.option("--dry-run", is_flag=True)
@assert_required_config(RequiredCase.JOB)
@pprint_errors
@cloud_context
def launch(cloud, dry_run):
    """
    Launch an instance according to your Nimbo config with minimal setup.

    The launched instance does not include your code, data, or environment.
    """
    cloud.run("_nimbo_launch", dry_run)


@cli.command(cls=NimboCommand, help_section=HelpSection.INSTANCE)
@click.option("--dry-run", is_flag=True)
@assert_required_config(RequiredCase.JOB)
@pprint_errors
@cloud_context
def launch_and_setup(cloud, dry_run):
    """
    Launch an instance with your code, data and environment.

    The launched instance does not run any job.
    """
    cloud.run("_nimbo_launch_and_setup", dry_run)


@cli.command(cls=NimboCommand, help_section=HelpSection.INSTANCE)
@click.argument("instance_id")
@click.option("--dry-run", is_flag=True)
@assert_required_config(RequiredCase.INSTANCE)
@pprint_errors
@cloud_context
def ssh(cloud, instance_id, dry_run):
    """SSH into an instance by INSTANCE_ID."""
    cloud.ssh(instance_id, dry_run)


@cli.command(cls=NimboCommand, help_section=HelpSection.INSTANCE)
@click.argument("instance_id")
@click.option("--dry-run", is_flag=True)
@assert_required_config(RequiredCase.MINIMAL)
@pprint_errors
@cloud_context
def get_status(cloud, instance_id, dry_run):
    """Get the status of an instance by INSTANCE_ID."""
    print(cloud.get_status(instance_id, dry_run))


@cli.command(cls=NimboCommand, help_section=HelpSection.INSTANCE)
@click.option("--dry-run", is_flag=True)
@assert_required_config(RequiredCase.MINIMAL)
@pprint_errors
@cloud_context
def ls_active(cloud, dry_run):
    """List all your active instances."""
    cloud.ls_active_instances(dry_run)


@cli.command(cls=NimboCommand, help_section=HelpSection.INSTANCE)
@click.option("--dry-run", is_flag=True)
@assert_required_config(RequiredCase.MINIMAL)
@pprint_errors
@cloud_context
def ls_stopped(cloud, dry_run):
    """List all your stopped instances."""
    cloud.ls_stopped_instances(dry_run)


@cli.command(cls=NimboCommand, help_section=HelpSection.INSTANCE)
@click.argument("instance_id")
@click.option("--dry-run", is_flag=True)
@assert_required_config(RequiredCase.MINIMAL)
@pprint_errors
@cloud_context
def rm_instance(cloud, instance_id, dry_run):
    """Terminate an instance by INSTANCE_ID."""
    cloud.delete_instance(instance_id, dry_run)


@cli.command(cls=NimboCommand, help_section=HelpSection.INSTANCE)
@click.option("--dry-run", is_flag=True)
@assert_required_config(RequiredCase.MINIMAL)
@pprint_errors
@cloud_context
def rm_all_instances(cloud, dry_run):
    """Terminate all your instances."""
    click.confirm(
        "This will delete all your running instances.\n" "Do you want to continue?",
        abort=True,
    )
    cloud.delete_all_instances(dry_run)


@cli.command(cls=NimboCommand, help_section=HelpSection.INSTANCE)
@click.argument("instance_id")
@click.option("--dry-run", is_flag=True)
@assert_required_config(RequiredCase.MINIMAL)
@pprint_errors
@cloud_context
def stop_instance(cloud, instance_id, dry_run):
    """Stop an instance by INSTANCE_ID."""
    cloud.stop_instance(instance_id, dry_run)


@cli.command(cls=NimboCommand, help_section=HelpSection.INSTANCE)
@click.argument("instance_id")
@click.option("--dry-run", is_flag=True)
@assert_required_config(RequiredCase.MINIMAL)
@pprint_errors
@cloud_context
def resume_instance(cloud, instance_id, dry_run):
    """Resume a stopped instance by INSTANCE_ID."""
    cloud.resume_instance(instance_id, dry_run)


@cli.command(
    cls=NimboCommand,
    help_section=HelpSection.INSTANCE,
    short_help="Add your IP to instance firewall ingress allow list.",
)
@click.argument("security_group")
@click.option("--dry-run", is_flag=True)
@assert_required_config(RequiredCase.MINIMAL)
@pprint_errors
@cloud_context
def add_current_ip(cloud, security_group, dry_run):
    """Add the IP of the current machine to the allowed inbound rules of GROUP.

    GROUP is the security group to which the inbound rule will be added.
    """
    cloud.allow_ingress_current_ip(security_group, dry_run)


@cli.command(cls=NimboCommand, help_section=HelpSection.STORAGE)
@click.argument("bucket_name")
@click.option("--dry-run", is_flag=True)
@assert_required_config(RequiredCase.MINIMAL)
@pprint_errors
@cloud_context
def mk_bucket(cloud, bucket_name, dry_run):
    """
    Create the bucket BUCKET_NAME in S3.

    BUCKET_NAME is the name of the bucket to create, s3://BUCKET_NAME
    """
    cloud.mk_bucket(bucket_name, dry_run)


@cli.command(cls=NimboCommand, help_section=HelpSection.STORAGE)
@click.argument("path")
@assert_required_config(RequiredCase.MINIMAL)
@pprint_errors
@cloud_context
def ls_bucket(cloud, path):
    """List S3 objects in PATH.

    PATH is an S3 path of the form s3://bucket-name/my/files/path.
    """
    cloud.ls_bucket(path)


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
@assert_required_config(RequiredCase.STORAGE)
@pprint_errors
@cloud_context
def push(cloud, folder, delete):
    """Push your local datasets/results folder onto S3."""

    if delete:
        click.confirm(
            "This will delete any files that exist in the remote "
            "folder but do not exist in the local folder.\n"
            "Do you want to continue?",
            abort=True,
        )
    cloud.push(folder, delete)


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
@assert_required_config(RequiredCase.STORAGE)
@pprint_errors
@cloud_context
def pull(cloud, folder, delete):
    """Pull datasets/results folder into your computer from S3."""

    if delete:
        click.confirm(
            "This will delete any files that exist in the local "
            "folder but do not exist in the remote folder.\n"
            "Do you want to continue?",
            abort=True,
        )
    cloud.pull(folder, delete)


@cli.command(cls=NimboCommand, help_section=HelpSection.STORAGE)
@click.argument("instance_id")
@assert_required_config(RequiredCase.INSTANCE)
@pprint_errors
@cloud_context
def sync_notebooks(cloud, instance_id):
    """
    Pull ipynb files from INSTANCE_ID to your local folder.

    Make sure to run 'nimbo sync-notebooks <instance_id>' to sync the notebook
    to your local folder, as the remote notebooks will be lost once the instance
    is terminated.
    """
    cloud.sync_notebooks(instance_id)


@cli.command(cls=NimboCommand, help_section=HelpSection.UTILS)
@assert_required_config(RequiredCase.NONE)
@pprint_errors
def generate_config():
    """Create a base configuration file in the current directory.

    Remember to change any fields to your own values.
    """
    utils.generate_config(_CONFIG_PATH_OVERRIDE)


@cli.command(cls=NimboCommand, help_section=HelpSection.UTILS)
@assert_required_config(RequiredCase.MINIMAL)
@pprint_errors
@cloud_context
def mk_instance_key(cloud):
    """Create and download an instance key to the current directory."""
    cloud.mk_instance_key()


@cli.command(cls=NimboCommand, help_section=HelpSection.UTILS)
@click.option("--dry-run", is_flag=True)
@assert_required_config(RequiredCase.INSTANCE, RequiredCase.STORAGE)
@pprint_errors
@cloud_context
def test_access(cloud, dry_run):
    """Run a mock job to test your config."""
    cloud.run_access_test(dry_run)


@cli.command(cls=NimboCommand, help_section=HelpSection.UTILS)
@click.option("--dry-run", is_flag=True)
@assert_required_config(RequiredCase.MINIMAL)
@pprint_errors
@cloud_context
def ls_prices(cloud, dry_run):
    """List the prices, types, and specs of GPU instances."""
    cloud.ls_gpu_prices(dry_run)


@cli.command(cls=NimboCommand, help_section=HelpSection.UTILS)
@click.option("--dry-run", is_flag=True)
@assert_required_config(RequiredCase.MINIMAL)
@pprint_errors
@cloud_context
def ls_spot_prices(cloud, dry_run):
    """List the prices, types, and specs of GPU spot instances."""
    cloud.ls_spot_gpu_prices(dry_run)


@cli.command(cls=NimboCommand, help_section=HelpSection.UTILS)
@click.argument("qty", type=int, required=True)
@click.argument("timescale", type=click.Choice(["days", "months"]), required=True)
@click.option("--dry-run", is_flag=True)
@assert_required_config(RequiredCase.MINIMAL)
@pprint_errors
@cloud_context
def spending(cloud, qty, timescale, dry_run):
    """Show daily/monthly spending summary. Costs without credits or refunds applied.

    QTY is the number of days/months you want to see, starting from the current date.\n
    For example:\n
        'nimbo spending 10 days' shows daily spending of the last 10 days\n
        'nimbo spending 3 months' shows the monthly spending of the last 3 months
    """
    cloud.spending(qty, timescale, dry_run)


@cli.command(cls=NimboCommand, help_section=HelpSection.ADMIN)
@click.argument("profile")
@click.option(
    "--no-s3-access", help="Create your own S3 access role separately.", is_flag=True
)
@assert_required_config(RequiredCase.NONE)
@pprint_errors
@cloud_context
def admin_setup(cloud, profile, no_s3_access):
    """
    Setup Nimbo access role for your organisation.

    Creates a user group and instance role that gives users in your AWS account the
    necessary permissions to use Nimbo. Once `admin-setup` is done, you can run
    `add-user` to allow a specific user to use the user group and role.

    PROFILE is the profile name of your root/admin account from ~/.aws/credentials
    """
    cloud.setup(profile, no_s3_access)


@cli.command(cls=NimboCommand, help_section=HelpSection.ADMIN)
@click.argument("profile")
@click.argument("username")
@assert_required_config(RequiredCase.NONE)
@pprint_errors
@cloud_context
def add_user(cloud, profile, username):
    """Adds user USERNAME to the user group NimboUserGroup.

    You must have run 'nimbo admin-setup' before adding users.

    PROFILE is the profile name of your root/admin account from ~/.aws/credentials
    """
    cloud.add_user(profile, username)
