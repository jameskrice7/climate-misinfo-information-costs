"""Watchdog daemon: keeps vLLM + classifier alive for the multi-day run.

Polls every 60s. If either has died, restarts it (vLLM first if down, then
classifier). Logs to logs/watchdog.log. Idempotent — running multiple times
is harmless but unnecessary.
"""
import os, sys, time, subprocess, urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)

VLLM_PID = "vllm.pid"
CLASS_PID = "classifier.pid"
VLLM_URL = "http://127.0.0.1:8000/v1/models"
LOG = "logs/watchdog.log"
PIDFILE = "watchdog.pid"
POLL = 60
WINDOW = os.environ.get("WINDOW", "2000")
CONCURRENCY = os.environ.get("CONCURRENCY", "128")


def alive(pidfile):
    try:
        with open(pidfile) as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def vllm_ready():
    try:
        with urllib.request.urlopen(VLLM_URL, timeout=5) as r:
            return b'"qwen"' in r.read()
    except Exception:
        return False


def restart_vllm():
    # ensure any straggler is gone, then launch fresh daemon
    subprocess.run(["pkill", "-9", "-f", "VLLM::"], stderr=subprocess.DEVNULL)
    subprocess.run(["pkill", "-9", "-f", "openai\\.api_server"], stderr=subprocess.DEVNULL)
    time.sleep(8)
    subprocess.run(["python3", "launch_vllm.py"], check=True)
    log(f"vLLM restarted")


def restart_classifier():
    subprocess.run(["pkill", "-9", "-f", "classify_industry"], stderr=subprocess.DEVNULL)
    time.sleep(2)
    env = os.environ.copy()
    env["WINDOW"] = WINDOW
    env["CONCURRENCY"] = CONCURRENCY
    subprocess.run(["python3", "launch_classifier.py"], env=env, check=True)
    log(f"classifier restarted")


def log(msg):
    with open(LOG, "a") as f:
        f.write(f"[{time.strftime('%F %T')}] {msg}\n")


def daemonize():
    if os.fork() != 0: os._exit(0)
    os.setsid()
    if os.fork() != 0: os._exit(0)
    fd_in = os.open("/dev/null", os.O_RDONLY)
    fd_out = os.open(LOG, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    os.dup2(fd_in, 0); os.dup2(fd_out, 1); os.dup2(fd_out, 2)
    os.close(fd_in); os.close(fd_out)
    with open(PIDFILE, "w") as f:
        f.write(str(os.getpid()))


def main():
    daemonize()
    log("watchdog start")
    # If a vLLM pidfile exists but it's not ready, give it grace before restart
    grace_until = 0
    while True:
        try:
            if not vllm_ready():
                if grace_until == 0:
                    grace_until = time.time() + 600  # 10 min grace for startup
                if time.time() > grace_until:
                    log("vLLM not ready, restarting")
                    restart_vllm()
                    grace_until = time.time() + 600
            else:
                grace_until = 0
                if not alive(CLASS_PID):
                    log("classifier dead, restarting")
                    restart_classifier()
        except Exception as e:
            log(f"watchdog exception: {type(e).__name__}: {e}")
        time.sleep(POLL)


if __name__ == "__main__":
    main()
