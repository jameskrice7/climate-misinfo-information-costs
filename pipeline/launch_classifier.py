"""Daemonize the (post x industry) classifier so it survives shell sessions.

It is resumable: on restart, completed shards in out/post_industry/ are skipped.
"""
import os, sys

LOG = "logs/classifier.log"
PIDFILE = "classifier.pid"
CMD = [".venv_tools/bin/python", "classify_industry.py"]

def daemonize():
    if os.fork() != 0:
        os._exit(0)
    os.setsid()
    if os.fork() != 0:
        os._exit(0)
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    sys.stdout.flush(); sys.stderr.flush()
    fd_in = os.open("/dev/null", os.O_RDONLY)
    fd_out = os.open(LOG, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    os.dup2(fd_in, 0); os.dup2(fd_out, 1); os.dup2(fd_out, 2)
    os.close(fd_in); os.close(fd_out)
    with open(PIDFILE, "w") as f:
        f.write(str(os.getpid()))
    os.execvp(CMD[0], CMD)

if __name__ == "__main__":
    daemonize()
