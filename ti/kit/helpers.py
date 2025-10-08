import os
import sys
import time
import re
from subprocess import run as run_cmd, CalledProcessError
from datetime import datetime as dt, timezone, UTC
import unicodedata


from .files import readYaml, unexpanduser as ux


TZ_RE = re.compile(r"""(?:Z|(?:[+-][0-9:]+))$""")
LETTER = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")

SEP_RE = re.compile(r"[\n\t ,]+")
STRIP_RE = re.compile(r"(?:^[\n\t ,]+)|(?:[\n\t ,]+$)", re.S)
VAR_RE = re.compile(r"\{([^}]+?)(:[^}]*)?\}")
MSG_LINE_RE = re.compile(r"^( *[0-9]+) (.*)$")
NUM_ALFA_RE = re.compile(r"^([0-9]*)([^0-9]*)(.*)$")
WHITE_RE = re.compile(r"""\s+""")
TO_ASCII_DEF = dict(
    ñ="n",
    ø="o",
    ç="c",
)
"""Undecomposable UNICODE characters mapped to their related ASCII characters."""


TO_ASCII = {}

for u, a in TO_ASCII_DEF.items():
    TO_ASCII[u] = a
    TO_ASCII[u.upper()] = a.upper()


LETTER = set("abcdefghijklmnopqrstuvwxyz()-")
VALID = set("_0123456789") | LETTER
SEQ_RE = re.compile(r"""^(.*)\(([0-9]+)\)$""", re.S)


def normalize(text):
    """Produce a normalized version of a string.

    Parameters
    ----------
    text: string
        The input text

    Returns
    -------
    string
        The lower-cased, whitespace normalized version of the input.
    """
    return WHITE_RE.sub(" ", text.strip()).lower()


def toAscii(text):
    """Transforms a text with diacritical marks into a plain ASCII text.

    Characters with diacritics are replaced by their base character.
    Some characters with diacritics are considered by UNICODE to be undecomposable
    characters, such as `ø` and `ñ`.
    We use a table (`TO_ASCII_DEF`) to map these on their related ASCII characters.

    We replace all consecutive whitespace by `_`, en we replace all non-alphanumeric
    characters except `()` by `x`.

    Parameters
    ----------
    text: string
        The text to be translated

    Returns
    -------
    string
        The translated text.
    """
    text = WHITE_RE.sub("_", text.strip()).lower()
    text = "".join(
        TO_ASCII.get(c, c)
        for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )
    text = "".join(c if c in VALID else "x" for c in text)
    return text


def makeAsciiUnique(text, among):
    """Transforms a text into plain ASCII and makes it unique among alternatives.

    Paramaters
    ----------
    text: string
        The text to be translated

    among: set of string
        The strings among which the result should be unique.
        It is assumed that these strings are themselves the results of `toAscii`.
    """

    candidate = toAscii(text)

    if candidate not in among:
        return candidate

    match = SEQ_RE.match(candidate)
    (base, seq) = match.group(1, 2) if match else (candidate, None)

    if seq is not None:
        seq = int(seq)

    oSeqs = set()

    for other in sorted(among):
        match = SEQ_RE.match(other)
        (oBase, oSeq) = match.group(1, 2) if match else (other, None)

        if oBase == base:
            oSeqs.add(None if oSeq is None else int(oSeq))

    if len(oSeqs):
        if seq in oSeqs:
            newSeqRep = f"({max((oSeq for oSeq in oSeqs if oSeq is not None), default=0) + 1})"
        else:
            newSeqRep = "" if seq is None else f"({seq})"
    else:
        newSeqRep = "(1)"
    return f"{base}{newSeqRep}"


def utcnow():
    """The current moment in time in the UTC time zone.

    Returns
    -------
    datetime
        An aware datetime object (in the sense of: having the timezone included
        in its value.
    """
    return dt.now(timezone.utc)


def isonow():
    """The current moment in time as an ISO 8601 string value.

    Details:

    *   the precision is up to the second;
    *   the separator between the date part and the timpe part is `T`;
    *   the timezone is UTC, marked as `Z` directly after the time part.

    Returns
    -------
    string
        E.g. `2024-11-13T10:53:15Z`
    """
    return TZ_RE.sub("Z", utcnow().isoformat(timespec="seconds", sep="T"))


def pseudoisonow():
    """The current moment in time as a isolike string value.

    It is like `isonow()`, but the time separators (`:`) are
    replaced by `-`, so that the string can be included in urls.

    Returns
    -------
    string
        E.g. `2024-11-13T10-53-15Z`
    """
    return isonow().replace(":", "-")


def getDelta(days, refDate, iso=True):
    if refDate is None:
        # undefined dates count as not recent
        return 0

    delta = utcnow() - (
        dt.fromisoformat(refDate) if iso else dt.fromtimestamp(refDate, tz=UTC)
    )
    deltaDays = delta.days + delta.seconds / 86400

    return deltaDays


def lessAgo(days, refDate, iso=True):
    return 0 <= getDelta(days, refDate, iso=iso) < days


def versionSort(x):
    parts = []

    for p in x.split("."):
        match = NUM_ALFA_RE.match(p)
        (num, alfa, rest) = match.group(1, 2, 3)
        parts.append((int(num) if num else 0, alfa, rest))

    return tuple(parts)


def plainify(value):
    """Make sure that the value is either a string or a list of strings.

    If it is a dict, turn it into a list of stringified key-value pairs.
    """
    if value is None:
        return ""

    tp = type(value)

    if tp is list:
        return [plainify(v) for v in value]

    if tp is dict:
        return [f"{k}: {plainify(v)}" for (k, v) in value.items()]

    return str(value)


def ucFirst(x):
    if not x:
        return ""

    return x[0].upper() + x[1:]


def prettify(x):
    return " ".join(ucFirst(w) for w in x.split("_"))


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


def console(*msg, error=False, newline=True, sleep=None):
    msg = " ".join(m if type(m) is str else repr(m) for m in msg)
    msg = "" if not msg else ux(msg)
    msg = msg[1:] if msg.startswith("\n") else msg
    msg = msg[0:-1] if msg.endswith("\n") else msg
    target = sys.stderr if error else sys.stdout
    nl = "\n" if newline else ""
    target.write(f"{msg}{nl}")
    target.flush()

    if sleep:
        time.sleep(sleep)


def consoleT01(msg, error=False, newline=True):
    console(msg, error=error, newline=newline, sleep=0.1)


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
