import functools

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


command = functools.partial(cli.command, cls=NimboCommand)


@command(help_section=HelpSection.INSTANCE)
@click.argument("job_cmd")
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredCase.JOB)
@utils.handle_errors
def run(job_cmd, dry_run):
    """Run JOB_CMD on an instance.

    JOB_CMD is any command you would run locally.
    E.g. \"python runner.py --epochs=10\".\n
    The command must be between quotes.
    """
    Cloud.run(job_cmd, dry_run)


@command(
    help_section=HelpSection.INSTANCE,
    short_help="Launch Jupiter with your code, data, and environment",
)
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredCase.JOB)
@utils.handle_errors
def notebook(dry_run):
    """
    Launch Jupyter Lab on an instance with your code, data and environment.

    Make sure to run 'nimbo sync-notebooks <instance_id>' frequently to sync
    the notebook to your local directory, as the remote notebooks will be lost
    once the instance is terminated.
    """
    Cloud.run("_nimbo_notebook", dry_run)


@command(
    help_section=HelpSection.INSTANCE,
    short_help="Launch an instance with minimal setup.",
)
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredCase.JOB)
@utils.handle_errors
def launch(dry_run):
    """
    Launch an instance according to your Nimbo config with minimal setup.

    The launched instance does not include your code, data, or environment.
    """
    Cloud.run("_nimbo_launch", dry_run)


@command(help_section=HelpSection.INSTANCE)
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredCase.JOB)
@utils.handle_errors
def launch_and_setup(dry_run):
    """
    Launch an instance with your code, data and environment.

    The launched instance does not run any job.
    """
    Cloud.run("_nimbo_launch_and_setup", dry_run)


@command(help_section=HelpSection.INSTANCE)
@click.argument("instance_id")
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredCase.INSTANCE)
@utils.handle_errors
def ssh(instance_id, dry_run):
    """SSH into an instance by INSTANCE_ID."""
    Cloud.ssh(instance_id, dry_run)


@command(help_section=HelpSection.INSTANCE)
@click.argument("instance_id")
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredCase.MINIMAL)
@utils.handle_errors
def get_status(instance_id, dry_run):
    """Get the status of an instance by INSTANCE_ID."""
    print(Cloud.get_status(instance_id, dry_run))


@command(help_section=HelpSection.INSTANCE)
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredCase.MINIMAL)
@utils.handle_errors
def ls_active(dry_run):
    """List all your active instances."""
    Cloud.ls_active_instances(dry_run)


@command(help_section=HelpSection.INSTANCE)
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredCase.MINIMAL)
@utils.handle_errors
def ls_stopped(dry_run):
    """List all your stopped instances."""
    Cloud.ls_stopped_instances(dry_run)


@command(help_section=HelpSection.INSTANCE)
@click.argument("instance_id")
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredCase.MINIMAL)
@utils.handle_errors
def rm_instance(instance_id, dry_run):
    """Terminate an instance by INSTANCE_ID."""
    Cloud.delete_instance(instance_id, dry_run)


@command(help_section=HelpSection.INSTANCE)
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredCase.MINIMAL)
@utils.handle_errors
def rm_all_instances(dry_run):
    """Terminate all your instances."""
    click.confirm(
        "This will delete all your running instances.\n" "Do you want to continue?",
        abort=True,
    )
    Cloud.delete_all_instances(dry_run)


@command(help_section=HelpSection.INSTANCE)
@click.argument("instance_id")
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredCase.MINIMAL)
@utils.handle_errors
def stop_instance(instance_id, dry_run):
    """Stop an instance by INSTANCE_ID."""
    Cloud.stop_instance(instance_id, dry_run)


@command(help_section=HelpSection.INSTANCE)
@click.argument("instance_id")
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredCase.MINIMAL)
@utils.handle_errors
def resume_instance(instance_id, dry_run):
    """Resume a stopped instance by INSTANCE_ID."""
    Cloud.resume_instance(instance_id, dry_run)


@command(
    help_section=HelpSection.INSTANCE,
    short_help="Add your IP to instance firewall ingress allow list.",
)
@click.argument("security_group")
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredCase.MINIMAL)
@utils.handle_errors
def add_current_ip(security_group, dry_run):
    """Add the IP of the current machine to the allowed inbound rules of GROUP.

    GROUP is the security group to which the inbound rule will be added.
    """
    Cloud.allow_ingress_current_ip(security_group, dry_run)


@command(help_section=HelpSection.STORAGE)
@click.argument("bucket_name")
@utils.assert_required_config(RequiredCase.MINIMAL)
@utils.handle_errors
def mk_bucket(bucket_name):
    """
    Create bucket BUCKET_NAME in S3.

    BUCKET_NAME is the name of the bucket to create, 's3://BUCKET_NAME'.
    BUCKET_NAME must be unique within the region the bucket is being created in.
    """
    Cloud.mk_bucket(bucket_name)


@command(help_section=HelpSection.STORAGE)
@click.argument("bucket_name")
@click.argument("prefix", required=False)
@utils.assert_required_config(RequiredCase.MINIMAL)
@utils.handle_errors
def ls_bucket(bucket_name, prefix):
    """
    List S3 objects in BUCKET_NAME with optional PREFIX.

    BUCKET_NAME is the name of the bucket to list, 's3://BUCKET_NAME'.
    PREFIX is a path relative to the BUCKET_NAME. In the case of
    's3://bucket-name/my/files/path', PREFIX could be 'my/files'.
    """
    Cloud.ls_bucket(bucket_name, prefix if prefix else "")


@command(help_section=HelpSection.STORAGE)
@utils.assert_required_config(RequiredCase.MINIMAL)
@utils.handle_errors
def ls_buckets():
    """ List S3 buckets owned by you. """
    Cloud.ls_buckets()


@command(help_section=HelpSection.STORAGE)
@click.argument(
    "directory", type=click.Choice(["datasets", "results"]), required=True
)
@click.option(
    "--delete",
    is_flag=True,
    help="""
      Delete files that exist in S3, but not the local DIRECTORY.
    """,
)
@utils.assert_required_config(RequiredCase.STORAGE)
@utils.handle_errors
def push(directory, delete):
    """Push your local DIRECTORY to S3."""

    if delete:
        click.confirm(
            "This will delete any files that exist in the remote "
            "directory but do not exist in the local directory.\n"
            "Do you want to continue?",
            abort=True,
        )
    Cloud.push(directory, delete)


@command(help_section=HelpSection.STORAGE)
@click.argument(
    "directory", type=click.Choice(["datasets", "results", "logs"]), required=True
)
@click.option(
    "--delete",
    is_flag=True,
    help="""
      Delete files that exist in the local DIRECTORY, but do not exist in S3.
    """,
)
@utils.assert_required_config(RequiredCase.STORAGE)
@utils.handle_errors
def pull(directory, delete):
    """Pull DIRECTORY from S3."""

    if delete:
        click.confirm(
            "This will delete any files that exist in the local "
            "directory but do not exist in the remote directory.\n"
            "Do you want to continue?",
            abort=True,
        )
    Cloud.pull(directory, delete)


@command(help_section=HelpSection.STORAGE)
@click.argument("instance_id")
@utils.assert_required_config(RequiredCase.INSTANCE)
@utils.handle_errors
def sync_notebooks(instance_id):
    """
    Pull ipynb files from INSTANCE_ID to your local directory.

    Make sure to run 'nimbo sync-notebooks <instance_id>' to sync the notebook
    to your local directory, as the remote notebooks will be lost once the instance
    is terminated.
    """
    Cloud.sync_notebooks(instance_id)


@command(help_section=HelpSection.UTILS)
@utils.assert_required_config(RequiredCase.NONE)
@utils.handle_errors
def generate_config():
    """Create a base nimbo-config.yml in the current directory.

    Remember to change any fields to your own values.
    """
    utils.generate_config()


@command(help_section=HelpSection.UTILS)
@utils.assert_required_config(RequiredCase.MINIMAL)
@utils.handle_errors
def mk_instance_key():
    """Create and download an instance key to the current directory."""
    Cloud.mk_instance_key()


@command(help_section=HelpSection.UTILS)
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredCase.INSTANCE, RequiredCase.STORAGE)
@utils.handle_errors
def test_access(dry_run):
    """Run a mock job to test your config."""
    Cloud.run_access_test(dry_run)


@command(help_section=HelpSection.UTILS)
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredCase.MINIMAL)
@utils.handle_errors
def ls_prices(dry_run):
    """List the prices, types, and specs of GPU instances."""
    Cloud.ls_gpu_prices(dry_run)


@command(help_section=HelpSection.UTILS)
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredCase.MINIMAL)
@utils.handle_errors
def ls_spot_prices(dry_run):
    """List the prices, types, and specs of GPU spot instances."""
    Cloud.ls_spot_gpu_prices(dry_run)


@command(help_section=HelpSection.UTILS)
@click.argument("qty", type=int, required=True)
@click.argument("timescale", type=click.Choice(["days", "months"]), required=True)
@click.option("--dry-run", is_flag=True)
@utils.assert_required_config(RequiredCase.MINIMAL)
@utils.handle_errors
def spending(qty, timescale, dry_run):
    """Show daily/monthly spending summary. Costs without credits or refunds applied.

    QTY is the number of days/months you want to see, starting from the current date.\n
    For example:\n
        'nimbo spending 10 days' shows daily spending of the last 10 days\n
        'nimbo spending 3 months' shows the monthly spending of the last 3 months
    """
    Cloud.spending(qty, timescale, dry_run)


@command(help_section=HelpSection.ADMIN)
@click.argument("profile")
@click.option(
    "--no-s3-access", help="Create your own S3 access role separately.", is_flag=True
)
@utils.assert_required_config(RequiredCase.NONE)
@utils.handle_errors
def admin_setup(profile, no_s3_access):
    """
    Setup Nimbo access role for your organisation.

    Creates a user group and instance role that gives users in your AWS account the
    necessary permissions to use Nimbo. Once `admin-setup` is done, you can run
    `add-user` to allow a specific user to use the user group and role.

    PROFILE is the profile name of your root/admin account from ~/.aws/credentials
    """
    Cloud.setup(profile, no_s3_access)


@command(help_section=HelpSection.ADMIN)
@click.argument("profile")
@click.argument("username")
@utils.assert_required_config(RequiredCase.NONE)
@utils.handle_errors
def add_user(profile, username):
    """Adds user USERNAME to the user group NimboUserGroup.

    You must have run 'nimbo admin-setup' before adding users.

    PROFILE is the profile name of your root/admin account from ~/.aws/credentials
    """
    Cloud.add_user(profile, username)
