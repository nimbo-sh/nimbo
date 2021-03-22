import os
import pathlib

NIMBO = str(pathlib.Path(__file__).parent.parent.absolute())
CWD = os.getcwd()

print(NIMBO)
print(CWD)
