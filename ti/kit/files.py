import os
import json
import yaml

from shutil import rmtree, copytree, copy

from .generic import deepAttrDict


def str_presenter(dumper, data):
    """configures yaml for dumping multiline strings
    Ref: https://stackoverflow.com/questions/8640959
    """
    if data.count("\n") > 0:  # check for multiline string
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")

    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


yaml.add_representer(str, str_presenter)
yaml.representer.SafeRepresenter.add_representer(str, str_presenter)


def fileOpen(*args, **kwargs):
    """Wrapper around `open()`, making sure `encoding="utf8" is passed.

    This function calls `open()` with the same arguments, but if the optional
    argument `encoding` is missing and the mode argument does not contain a `b`
    (binary file), then `encoding="utf8"` is supplied.
    """

    if "encoding" in kwargs or ("mode" in kwargs and "b" in kwargs["mode"]):
        return open(*args, **kwargs)
    return open(*args, **kwargs, encoding="utf8")


def normpath(path):
    if path is None:
        return None
    norm = os.path.normpath(path)
    return "/".join(norm.split(os.path.sep))


_homeDir = normpath(os.path.expanduser("~"))


scanDir = os.scandir
walkDir = os.walk
splitExt = os.path.splitext
mTime = os.path.getmtime


def abspath(path):
    return normpath(os.path.abspath(path))


def expanduser(path):
    nPath = normpath(path)
    if nPath.startswith("~"):
        return f"{_homeDir}{nPath[1:]}"

    return nPath


def unexpanduser(path):
    nPath = normpath(path)
    # if nPath.startswith(_homeDir):
    #    return f"~{nPath[len(_homeDir):]}"

    return nPath.replace(_homeDir, "~")


def expandDir(obj, dirName):
    if dirName.startswith("~"):
        dirName = dirName.replace("~", obj.homeDir, 1)
    elif dirName.startswith(".."):
        dirName = dirName.replace("..", obj.parentDir, 1)
    elif dirName.startswith("."):
        dirName = dirName.replace(".", obj.curDir, 1)
    return normpath(dirName)


def prefixSlash(path):
    """Prefix a / before a path if it is non-empty and not already starts with it."""
    return f"/{path}" if path and not path.startswith("/") else path


def dirEmpty(target):
    target = normpath(target)
    return not os.path.exists(target) or not os.listdir(target)


def clearTree(path):
    """Remove all files from a directory, recursively, but leave subdirectories.

    Reason: we want to inspect output in an editor.
    But if we remove the directories, the editor looses its current directory
    all the time.

    Parameters
    ----------
    path:
        The directory in question. A leading `~` will be expanded to the user's
        home directory.
    """

    subdirs = []
    path = expanduser(path)

    with os.scandir(path) as dh:
        for i, entry in enumerate(dh):
            name = entry.name
            if name.startswith("."):
                continue
            if entry.is_file():
                os.remove(f"{path}/{name}")
            elif entry.is_dir():
                subdirs.append(name)

    for subdir in subdirs:
        clearTree(f"{path}/{subdir}")


def initTree(path, fresh=False, gentle=False):
    """Make sure a directory exists, optionally clean it.

    Parameters
    ----------
    path:
        The directory in question. A leading `~` will be expanded to the user's
        home directory.

        If the directory does not exist, it will be created.

    fresh: boolean, optional False
        If True, existing contents will be removed, more or less gently.

    gentle: boolean, optional False
        When existing content is removed, only files are recursively removed, not
        subdirectories.
    """

    path = expanduser(path)
    exists = os.path.exists(path)
    if fresh:
        if exists:
            if gentle:
                clearTree(path)
            else:
                rmtree(path)

    if not exists or fresh:
        os.makedirs(path, exist_ok=True)


def dirNm(path):
    """Get the directory part of a file name."""
    return os.path.dirname(path)


def fileNm(path):
    """Get the file part of a file name."""
    return os.path.basename(path)


def extNm(path):
    """Get the extension part of a file name.

    The dot is not included.
    If there is no extension, the empty string is returned.
    """
    parts = fileNm(path).rsplit(".", 1)
    return "" if len(parts) == 0 else parts[-1]


def stripExt(path):
    """Strip the extension of a file name, if there is one."""
    (d, f) = (dirNm(path), fileNm(path))
    sep = "/" if d else ""
    return f"{d}{sep}{f.rsplit('.', 1)[0]}"


def replaceExt(path, newExt):
    """Replace the extension of a path by another one. Specify it without dot."""
    (main, ext) = os.path.splitext(path)
    return f"{main}.{newExt}"


def splitPath(path):
    """Split a file name in a directory part and a file part."""
    return os.path.split(path)


def isFile(path):
    """Whether path exists and is a file."""
    return os.path.isfile(path)


def isDir(path):
    """Whether path exists and is a directory."""
    return os.path.isdir(path)


def fileMake(path, force=False):
    """Create a new empty file.

    If necessary, create intermediate subdirectories.
    If the file already exists, do nothing, unless `force` is True.
    If the file exists as a directory, do nothing

    Parameters
    ----------
    path: string
        The path to the new file
    force: boolean, optional False
        If `False`, nothing is done if the file already exists.
        Otherwise, an existing file is truncated.
    """
    if not dirExists(path) and (force or not fileExists(path)):
        parentDir = dirNm(path)
        dirMake(parentDir)

        with fileOpen(path, "w"):
            pass


def fileExists(path):
    """Whether a path exists as file on the file system."""
    return os.path.isfile(path)


def fileRemove(path):
    """Removes a file if it exists as file."""
    if fileExists(path):
        os.remove(path)


def fileCopy(pathSrc, pathDst):
    """Copies a file if it exists as file.

    Wipes the destination file, if it exists.
    """
    if pathSrc == pathDst:
        return

    if fileExists(pathSrc):
        fileRemove(pathDst)
        copy(pathSrc, pathDst)


def fileMove(pathSrc, pathDst):
    """Moves a file if it exists as file.

    Wipes the destination file, if it exists.
    """
    if fileExists(pathSrc):
        fileRemove(pathDst)
    os.rename(pathSrc, pathDst)


def dirExists(path):
    """Whether a path exists as directory on the file system."""
    return (
        False
        if path is None
        else True if path == "" else os.path.isdir(path) if path else True
    )


def dirRemove(path):
    """Removes a directory if it exists as directory."""
    if dirExists(path):
        rmtree(path)


def dirMove(pathSrc, pathDst):
    """Moves a directory if it exists as directory.

    Refuses the operation in the target exists.
    """
    if not dirExists(pathSrc) or dirExists(pathDst):
        return False
    os.rename(pathSrc, pathDst)
    return True


def dirCopy(pathSrc, pathDst, noclobber=False):
    """Copies a directory if it exists as directory.

    Wipes the destination directory, if it exists.
    """
    if dirExists(pathSrc):
        if dirExists(pathDst):
            if noclobber:
                return False
        dirRemove(pathDst)
        copytree(pathSrc, pathDst)
        return True
    else:
        return False


def dirMake(path):
    """Creates a directory if it does not already exist as directory."""
    if not dirExists(path):
        os.makedirs(path, exist_ok=True)


def dirContents(path):
    """Gets the contents of a directory.

    Only the direct entries in the directory (not recursively), and only real files
    and folders.

    The list of files and folders will be returned separately.
    There is no attempt to sort the files.

    Parameters
    ----------
    path: string
        The path to the directory on the file system.

    Returns
    -------
    tuple of tuple
        The subdirectories and the files.
    """
    if not dirExists(path):
        return ((), ())

    files = []
    dirs = []

    for entry in os.listdir(path):
        if os.path.isfile(f"{path}/{entry}"):
            files.append(entry)
        elif os.path.isdir(f"{path}/{entry}"):
            dirs.append(entry)

    return (tuple(files), tuple(dirs))


def dirAllFiles(path, ignore=None):
    """Gets all the files found by `path`.

    The result is just `[path]` if `path` is a file, otherwise the list of files under
    `path`, recursively.

    The files are sorted alphabetically by path name.

    Parameters
    ----------
    path: string
        The path to the file or directory on the file system.
    ignore: set
        Names of directories that must be skipped

    Returns
    -------
    tuple of string
        The names of the files under `path`, starting with `path`, followed
        by the bit relative to `path`.
    """
    if fileExists(path):
        return [path]

    if not dirExists(path):
        return []

    files = []

    if not ignore:
        ignore = set()

    for entry in os.listdir(path):
        name = f"{path}/{entry}"

        if os.path.isfile(name):
            files.append(name)
        elif os.path.isdir(name):
            if entry in ignore:
                continue
            files.extend(dirAllFiles(name, ignore=ignore))

    return tuple(sorted(files))


def getCwd():
    """Get current directory.

    Returns
    -------
    string
        The current directory.
    """
    return os.getcwd()


def chDir(directory):
    """Change to other directory.

    Parameters
    ----------
    directory: string
        The directory to change to.
    """
    return os.chdir(directory)


def readJson(text=None, plain=False, asFile=None, preferTuples=False):
    """Read a JSON file or string.

    The input data is either a text string or a file name or a file handle.
    Exactly one of the optional parameters `text` and `asFile` should be `None`.

    Parameters
    ----------
    text: string, optional None
        The input text if it is a string.
    asFile: string | object, optional None
        The input text if it is a file.
        If the value of `asFile` is a string, it is taken as a file name to read.
        Otherwise, it is taken as a file handle from which data can be read.
    plain: boolean, optional False
        If True, it return a dictionary, otherwise it wraps the data structure
        recursively in an AttrDict.
    preferTuples: boolean, optional False
        If the resulting data structure is to be wrapped in an AttrDict,
        we will represent lists as tuples.

    Returns
    -------
    object
        The resulting data structure.
    """
    if asFile is None:
        cfg = json.loads(text)
    else:
        if type(asFile) is str:
            if fileExists(asFile):
                with fileOpen(asFile) as fh:
                    cfg = json.load(fh)
            else:
                cfg = {}
        else:
            # in this case asFile should be a file handle
            cfg = json.load(asFile)

    return cfg if plain else deepAttrDict(cfg, preferTuples=preferTuples)


def writeJson(data, asFile=None, **kwargs):
    """Write data as JSON.

    The output is either delivered as string or written to a file.

    Parameters
    ----------
    data: object
        The input data.
    asFile: string | object, optional None
        The output destination.
        If `None`, the output text is delivered as the function result.
        If the value of `asFile` is a string, it is taken as a file name to write to.
        Otherwise, it is taken as a file handle to which text can be written.
    kwargs: dict, optional {}
        Additional paramters for the underlying json.dump method.
        By default, we use `indent=1, ensure_ascii=False`.

    Returns
    -------
    str | void
        If asFile is not None, the function returns None and the result is written
        to a file. Otherwise, the result string is returned.
    """
    if "indent" not in kwargs:
        kwargs["indent"] = 1
    if "ensure_ascii" not in kwargs:
        kwargs["ensure_ascii"] = False

    if type(asFile) is str:
        with fileOpen(asFile, "w") as fh:
            json.dump(data, fh, **kwargs)
    else:
        dumped = json.dumps(data, **kwargs)

        if asFile is None:
            return dumped

        asFile.write(dumped)


def readYaml(text=None, plain=False, asFile=None, preferTuples=True, preferLists=True):
    """Read a YAML file or string.

    The input data is either a text string or a file name or a file handle.
    Exactly one of the optional parameters `text` and `asFile` should be `None`.

    Parameters
    ----------
    text: string, optional None
        The input text if it is a string.
    asFile: string | object, optional None
        The input text if it is a file.
        If the value of `asFile` is a string, it is taken as a file name to read.
        Otherwise, it is taken as a file handle from which data can be read.
    plain: boolean, optional False
        If True, it return a dictionary, otherwise it wraps the data structure
        recursively in an AttrDict.
    preferTuples: boolean, optional False
        If the resulting data structure is to be wrapped in an AttrDict,
        we will represent lists as tuples.

    Returns
    -------
    object
        The resulting data structure.
    """
    kwargs = dict(Loader=yaml.FullLoader)

    if asFile is None:
        cfg = yaml.load(text, **kwargs)
    else:
        if fileExists(asFile):
            with fileOpen(asFile) as fh:
                cfg = yaml.load(fh, **kwargs)
        else:
            cfg = {}

    return cfg if plain else deepAttrDict(cfg, preferTuples=preferTuples)


def writeYaml(data, asFile=None, sorted=False):
    """Write data as YAML.

    The output is either delivered as string or written to a file.

    Parameters
    ----------
    data: object
        The input data.
    asFile: string | object, optional None
        The output destination.
        If `None`, the output text is delivered as the function result.
        If the value of `asFile` is a string, it is taken as a file name to write to.
        Otherwise, it is taken as a file handle to which text can be written.
    sorted: boolean, optional False
        If True, when writing out a dictionary, its keys will be sorted.

    Returns
    -------
    str | void
        If asFile is not None, the function returns None and the result is written
        to a file. Otherwise, the result string is returned.
    """
    kwargs = dict(allow_unicode=True, sort_keys=sorted)

    if type(asFile) is str:
        with fileOpen(asFile, mode="w") as fh:
            yaml.dump(data, fh, **kwargs)
    else:
        dumped = yaml.dump(data, **kwargs)

        if asFile is None:
            return dumped

        asFile.write(dumped)
