"""
Launches the app via waitress as a process fully detached from Jenkins.

Uses Windows-specific process creation flags so the new process breaks
away from the job object that Jenkins uses to track (and kill) child
processes when a pipeline step finishes. This replaces the earlier
schtasks/wmic approaches, which were fragile (permissions, quoting).
"""
import os
import subprocess
import sys

DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200
CREATE_BREAKAWAY_FROM_JOB = 0x01000000

workspace = os.environ.get("WORKSPACE", os.getcwd())
port = os.environ.get("APP_PORT", "5000")
exe = os.path.join(workspace, "venv", "Scripts", "waitress-serve.exe")
log_path = os.path.join(workspace, "waitress.log")

if not os.path.isfile(exe):
    print(f"ERROR: not found: {exe}")
    sys.exit(1)

log_file = open(log_path, "a")

subprocess.Popen(
    [exe, "--host=0.0.0.0", "--port=" + port, "app:app"],
    cwd=workspace,
    stdout=log_file,
    stderr=subprocess.STDOUT,
    creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_BREAKAWAY_FROM_JOB,
    close_fds=True,
)

print("Deploy process launched, log at " + log_path)
