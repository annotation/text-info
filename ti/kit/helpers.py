import os
import sys
import re
from subprocess import run as run_cmd, CalledProcessError
from datetime import datetime as dt, timezone


from .files import readYaml, unexpanduser as ux


LETTER = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")

SEP_RE = re.compile(r"[\n\t ,]+")
STRIP_RE = re.compile(r"(?:^[\n\t ,]+)|(?:[\n\t ,]+$)", re.S)
VAR_RE = re.compile(r"\{([^}]+?)(:[^}]*)?\}")
MSG_LINE_RE = re.compile(r"^( *[0-9]+) (.*)$")
NUM_ALFA_RE = re.compile(r"^([0-9]*)([^0-9]*)(.*)$")


def utcnow():
    return dt.now(timezone.utc)


def versionSort(x):
    parts = []

    for p in x.split("."):
        match = NUM_ALFA_RE.match(p)
        (num, alfa, rest) = match.group(1, 2, 3)
        parts.append((int(num) if num else 0, alfa, rest))

    return tuple(parts)


def var(envVar):
    """Retrieves the value of an environment variable.

    Parameters
    ----------
    envVar: string
        The name of the environment variable.

    Returns
    -------
    string or void
        The value of the environment variable if it exists, otherwise `None`.
    """
    return os.environ.get(envVar, None)


def console(*msg, error=False, newline=True):
    msg = " ".join(m if type(m) is str else repr(m) for m in msg)
    msg = "" if not msg else ux(msg)
    msg = msg[1:] if msg.startswith("\n") else msg
    msg = msg[0:-1] if msg.endswith("\n") else msg
    target = sys.stderr if error else sys.stdout
    nl = "\n" if newline else ""
    target.write(f"{msg}{nl}")
    target.flush()


def run(cmdline, workDir=None):
    """Runs a shell command and returns all relevant info.

    The function runs a command-line in a shell, and returns
    whether the command was successful, and also what the output was, separately for
    standard error and standard output.

    Parameters
    ----------
    cmdline: string
        The command-line to execute.
    workDir: string, optional None
        The working directory where the command should be executed.
        If `None` the current directory is used.
    """
    try:
        result = run_cmd(
            cmdline,
            shell=True,
            cwd=workDir,
            check=True,
            capture_output=True,
        )
        stdOut = result.stdout.decode("utf8").strip()
        stdErr = result.stderr.decode("utf8").strip()
        returnCode = 0
        good = True

    except CalledProcessError as e:
        stdOut = e.stdout.decode("utf8").strip()
        stdErr = e.stderr.decode("utf8").strip()
        returnCode = e.returncode
        good = False

    return (good, returnCode, stdOut, stdErr)


def readCfg(settingsFile, label, verbose=0, **kwargs):
    settings = readYaml(asFile=settingsFile, **kwargs)

    if settings:
        if verbose == 1:
            console(f"{label} settings read from {settingsFile}")
        good = True
    else:
        console(f"No {label} settings found, looked for {settingsFile}", error=True)
        good = False

    return (good, settings)
