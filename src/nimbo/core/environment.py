import os


def is_test_environment():
    return "NIMBO_ENV" in os.environ and os.environ["NIMBO_ENV"] == "test"
