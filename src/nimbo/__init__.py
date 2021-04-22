import sys
import re
import pydantic
import pkg_resources

from nimbo.core.environment import is_test_environment
import nimbo.core.config
import nimbo.tests.config


version = pkg_resources.get_distribution("nimbo").version


try:
    if is_test_environment():
        CONFIG = nimbo.tests.config.make_config()
    else:
        CONFIG = nimbo.core.config.make_config()

except pydantic.error_wrappers.ValidationError as e:
    error_msg = str(e)
    title_end = error_msg.index("\n", 1)
    new_title = (
        f"{len(e.errors())} validation "
        + f"error{'' if len(e.errors()) == 1 else 's'} in Nimbo config\n"
    )
    print(new_title + re.sub(r"\(type=.*\)", "", error_msg[title_end:]))
    sys.exit(1)
except FileNotFoundError as e:
    print(e)
    sys.exit(1)
