#!/usr/bin/env python3
import os
import subprocess
import sys
import time

project = os.path.expanduser("~/OptimusAI_V41_LIVE")
starter = "import os\nimport subprocess\nimport sys\nimport time\ntime.sleep(4)\nsubprocess.Popen([sys.executable, 'scripts/termux_command_bridge_agent.py'], cwd=os.path.expanduser('~/OptimusAI_V41_LIVE'), start_new_session=True)\n"
subprocess.Popen([sys.executable, "-c", starter], cwd=project, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
os.kill(os.getppid(), 15)
