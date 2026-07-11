import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "apps", "live_typewriter"))

from ibm_typewriter import main as run_app


if __name__ == '__main__':
    run_app()
