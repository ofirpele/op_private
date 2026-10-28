# from default_imports import *

import os
import sys


def is_running_on_docker():
    return os.environ.get("RUNS_ON_DOCKER") == "true"


if is_running_on_docker():
    import ofirpele_utils as o

    o.OUTPUT_FOLDER = os.path.normcase(r"/output/")
    o.CONFIG_FOLDER = os.path.normcase(r"/config/")
    o.DATA_FOLDER = os.path.normcase(r"/data/")
else:
    sys.path.insert(1, os.path.join(sys.path[0], ".."))
    import ofirpele_utils as o

    o.OUTPUT_FOLDER = os.path.normcase(r"../output/")
    o.CONFIG_FOLDER = os.path.normcase(r"../config/")
    o.DATA_FOLDER = os.path.normcase(r"../data/")

o.MY_EMAIL = "TODO@TODO"

o.redirect_stdout_stderr_by_REDIRECT_OUTPUT_enviorment()


# import hjson
