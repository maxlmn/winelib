"""Maintenance jobs: the scripts in app/api/tasks/, run from the Settings page.

One job at a time, in a background thread with its own database session. The page polls the job for its log.
Each task can be previewed (a dry run, nothing written) and/or run; its last run is remembered in the cache
directory so it survives restarts. A job can be stopped: it ends at its next log line.
"""
import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field

import paths

# The most lines a task's result keeps (a long preview: the summary says the rest)
MAX_ITEMS = 300

log_ = logging.getLogger(__name__)

LOG_LINES = 2000


class Stopped(Exception):
    pass


@dataclass
class Job:
    task: str
    title: str
    commit: bool
    params: dict
    started: float = field(default_factory=time.time)
    finished: float | None = None
    status: str = "running"  # running, done, failed, stopped
    lines: list = field(default_factory=list)
    result: dict | None = None
    stop: threading.Event = field(default_factory=threading.Event)

    def log(self, line):
        if self.stop.is_set():
            raise Stopped()
        self.lines.append(str(line))
        del self.lines[:-LOG_LINES]

    def public(self, with_log=True):
        # params starting with "_" (an uploaded file's text) stay in the job
        params = {k: v for k, v in self.params.items() if not k.startswith("_")}
        d = {"task": self.task, "title": self.title, "commit": self.commit, "params": params,
             "started": self.started, "finished": self.finished, "status": self.status, "result": self.result}
        if with_log:
            d["log"] = self.lines
        return d


_lock = threading.Lock()
_current: Job | None = None


def current():
    return _current


def busy():
    return _current is not None and _current.status == "running"


def _history_path():
    return os.path.join(paths.CACHE_DIR, "maintenance.json") if paths.CACHE_DIR else None


def history():
    """{task id: last job (without its log)}"""
    path = _history_path()
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError, TypeError):
        return {}


def _remember(job):
    path = _history_path()
    if not path:
        return
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        h = history()
        last = job.public(with_log=False)
        if last["result"] and len(last["result"].get("items") or []) > MAX_ITEMS:  # a long preview: the summary is enough
            last["result"] = {**last["result"], "items": last["result"]["items"][:MAX_ITEMS]}
        h[job.task] = last
        with open(path, "w", encoding="utf-8") as f:
            json.dump(h, f)
    except OSError as e:
        log_.warning("Couldn't save the maintenance history: %s", e)


def start(task, title, fn, make_session, commit, params):
    """Runs fn(session, job) in a thread. None when another job is running."""
    global _current
    with _lock:
        if busy():
            return None
        job = _current = Job(task=task, title=title, commit=commit, params=params)

    def run():
        session = make_session()
        try:
            job.result = fn(session, job) or {}
            job.status = "done"
        except Stopped:
            session.rollback()
            job.lines.append("Stopped.")
            job.status = "stopped"
        except Exception as e:
            session.rollback()
            log_.exception("Maintenance task %s failed", task)
            job.lines.append(f"❌ {type(e).__name__}: {e}")
            job.status = "failed"
        finally:
            session.close()
            job.finished = time.time()
            _remember(job)

    job.thread = threading.Thread(target=run, name=f"job-{task}", daemon=True)
    job.thread.start()
    return job
