import os
import pathlib

NIMBO = str(pathlib.Path(__file__).parent.parent.absolute())
CWD = os.getcwd()
CONFIG = os.path.join(CWD, "nimbo-config.yml")