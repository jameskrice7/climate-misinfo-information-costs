"""Double-fork launcher: starts the vLLM server as a session-detached daemon
so it survives parent shell death. Writes the daemon PID to vllm.pid."""
import os, sys, time

LOG = "logs/vllm.log"
PIDFILE = "vllm.pid"
CMD = ["./serve_vllm.sh"]

def daemonize():
    if os.fork() != 0:
        os._exit(0)             # parent of intermediate exits
    os.setsid()
    if os.fork() != 0:
        os._exit(0)             # intermediate exits; child orphaned
    # now in the daemon
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    sys.stdout.flush(); sys.stderr.flush()
    fd_in = os.open("/dev/null", os.O_RDONLY)
    fd_out = os.open(LOG, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    os.dup2(fd_in, 0); os.dup2(fd_out, 1); os.dup2(fd_out, 2)
    os.close(fd_in); os.close(fd_out)
    with open(PIDFILE, "w") as f:
        f.write(str(os.getpid()))
    os.execvp(CMD[0], CMD)

if __name__ == "__main__":
    daemonize()
