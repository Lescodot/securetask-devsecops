# This file intentionally contains insecure subprocess usage for Semgrep testing.

import subprocess

user_input = "example"

subprocess.run(user_input, shell=True)

subprocess.call(user_input, shell=True)
