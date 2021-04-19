import boto3

from nimbo.core import config_utils


def paid_required(func):
    def wrapper(*args, **kwargs):
        session = args[0]
        user_arn = session.client("sts").get_caller_identity()["Arn"]
        has_paid = False

        if has_paid:
            return func(*args, **kw)
        else:
            raise PermissionError(
                "This is a paid feature. Please buy or renew your commercial license."
            )

    return wrapper


def get_session_and_config(required_fields, fields_to_check):
    config = config_utils.load_config()

    config_utils.fill_defaults(config)
    config_utils.ConfigVerifier(config).verify(required_fields, fields_to_check)
    config_utils.remove_trailing_backslashes(config)

    session = boto3.Session(
        profile_name=config["aws_profile"], region_name=config["region_name"]
    )
    config["user_id"] = session.client("sts").get_caller_identity()["Arn"]

    return session, config


def get_session_and_config_full_check():
    return get_session_and_config("all", "all")


def get_session_and_config_instance_key():
    return get_session_and_config(
        ["aws_profile", "region_name", "instance_key"], ["instance_key"]
    )


def get_session_and_config_storage():
    check_list = [
        "s3_datasets_path",
        "s3_results_path",
        "local_datasets_path",
        "local_results_path",
    ]
    return get_session_and_config(["aws_profile", "region_name"] + check_list, [])


def get_session_and_config_minimal():
    return get_session_and_config(["aws_profile", "region_name"], [])
