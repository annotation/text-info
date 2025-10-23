import os
import io
import re
from zipfile import ZipFile
from shutil import rmtree
import requests
import ssl

from gitlab import Gitlab, GitlabGetError

from .helpers import console as consoleKit
from .files import chDir, getCwd, dirRemove

VERSION_DIGIT_RE = re.compile(r"^([0-9]+).*")
SHELL_VAR_RE = re.compile(r"[^A-Z0-9_]")
CHECK_FILE = "/__checkout__.txt"


def initTree(path, fresh=False, gentle=False):
    exists = os.path.exists(path)

    if fresh and exists:
        rmtree(path)

    if not exists or fresh:
        os.makedirs(path, exist_ok=True)


def GLPERS(backend):
    return f"GL_{SHELL_VAR_RE.sub('_', backend.upper())}_PERS"


def readSha(folder):
    path = f"{folder}/{CHECK_FILE}"
    commit = None

    if os.path.isfile(path):
        with open(path) as f:
            for line in f:
                text = line.strip()

                if text:
                    commit = text
                    break

    return commit


def writeSha(folder, commit):
    path = f"{folder}/{CHECK_FILE}"

    if not os.path.isdir(folder):
        os.makedirs(folder, exist_ok=True)

    with open(path, mode="w") as f:
        f.write(f"{commit}\n")


def fetchRepo(
    backend, org, repo, folder, destDir, force=False, verbose=False, indent=""
):
    """Get latest version of a subfolder of a GitLab repo.

    Before downloading the data, the commit hash of the online data and the
    local copy will be compared. If they are equal, the download will
    not happen, except when the `force` parameter is nonzero.

    After download, the commit hash will be written to the downloaded folder.

    If the folder is deep into the repo, say `/a/b/c/folder`,
    the zip file returned by GitLab will have paths `/a/b/c/folder/`... .

    The extraction will remove `/a/b/c` from these paths.
    After the extraction, a file __checkout__.txt containing the commit hash
    will be placed in the `destDir/folder` directory.

    Parameters
    ----------
    backend: string
        The name of an on-premiss gitlab server, e.g. gitlab.huc.knaw.nl
    org: string
        Organization or group on gitlab
    repo: string
        Repository within organization or group
    folder: string
        Subdirectory within repo
    destDir: string
        Local directory where the downloaded data should land
    force: boolean, optional False
        Whether to force downloading data if the local copy matches the online copy
        by sha-hash.

        If `False`: no re-download will take place. Otherwise the folder
        will be downloaded again.

        If `True`, the folder will be downloaded again, but the local copy will
        not be wiped on beforehand, so new files will overwrite existing files,
        but if the local copy contains additional material, it will be left in place.
    verbose: boolean, optional False
        If True, informational messages will be issued, otherwise only error messages
        will be issued.
    indent: string, optional ""
        Precede each console message with this string (usually a bunch of spaces)

    Returns
    -------
    bool | void
        A boolean indicating Whether the operation was successful.
        However, if the repo exists, but the subfolder does not exist in the repo,
        and the requests succeeds, but yields empty data, `None` is returned.
    """

    def console(*msg, error=False, newline=True):
        consoleKit(*msg, error=error, newline=newline, indent=indent)

    conn = None

    bUrl = f"https://{backend}"
    onlineSrc = f"{bUrl}/{org}/{repo}"
    person = os.environ.get(GLPERS(backend), None)

    if person:
        conn = Gitlab(bUrl, private_token=person, keep_base_url=True)
    else:
        conn = Gitlab(bUrl)

    backendVersion = conn.version()

    if (
        not backendVersion
        or backendVersion[0] == "unknown"
        or backendVersion[-1] == "unknown"
    ):
        conn = None
        console(f"cannot connect to GitLab instance {bUrl}\n", error=True)
        return False

    if verbose:
        console(f"connected to {bUrl}")

    repoOnline = None

    try:
        repoOnline = conn.projects.get(f"{org}/{repo}")
    except Exception as e:
        console(f"connecting failed to online {onlineSrc}", error=True)

        if type(e) is GitlabGetError:
            console(f"{bUrl} says: {e}", error=True)
        else:
            console(f"error with {bUrl}: {e}", error=True)

        return False

    if verbose:
        console(f"connected to {onlineSrc}")

    commit = None

    try:
        cs = repoOnline.commits.list(all=True)

        if not len(cs):
            console(f"no commit in {onlineSrc}", error=True)
        else:
            cs = sorted(cs, key=lambda x: x.created_at)

            if len(cs):
                commit = cs[-1]
    except Exception as e:
        console(str(e), error=True)

    if commit is None:
        console(f"cannot find commits in {onlineSrc}", error=True)
        return False

    sha = commit.id

    if verbose:
        console(f"{sha} = latest commit online")

    destDir = os.path.expanduser(destDir)
    (folderHead, folderTail) = folder.rsplit("/", 1) if "/" in folder else ("", folder)

    folderLocal = f"{destDir}/{folderTail}"
    existingSha = readSha(folderLocal)

    if verbose:
        console(f"{existingSha} = commit of local copy")

    localOk = existingSha == sha
    removeLocal = False

    if localOk:
        if verbose:
            console("Offline copy already up to date")

        if not force:
            return True
        else:
            console("Will download again over local copy")
    else:
        if verbose:
            console("Offline copy not up to date, will download new copy")

        removeLocal = True

    try:
        if verbose:
            console(f"Downloading {onlineSrc}/{folder} ... ", newline=False)

        response = conn.http_get(
            f"/projects/{repoOnline.id}/repository/archive.zip",
            query_data=dict(path=folder),
            raw=True,
        )
        zf = response.content
    except Exception as e:
        if verbose:
            console("failed", error=True)

        console(str(e), error=True)
        return False

    if verbose:
        console("done")

    if len(zf) == 0:
        console("Download is empty")
        return None

    initTree(folderLocal, fresh=removeLocal)

    if verbose:
        console(f"Extracting data to {folderLocal} ... ", newline=False)

    try:
        zf = io.BytesIO(zf)
        z = ZipFile(zf)

        folderHeadSlash = f"{folderHead}/" if folderHead else ""
        gitlabSlugRe = re.compile(f"^{repo}(?:-(?:master|main))?-[^/]*/")

        for zInfo in z.infolist():
            fileName = zInfo.filename

            if fileName.endswith("/"):
                continue

            fileName = gitlabSlugRe.sub("", fileName) or "/"
            fileName = fileName.removeprefix(folderHeadSlash)
            zInfo.filename = fileName
            z.extract(zInfo, path=destDir)

        writeSha(folderLocal, sha)

    except Exception as e:
        if verbose:
            console("failed", error=True)

        console(str(e), error=True)
        return False

    if verbose:
        console("done")

    return True


def downloadZip(
    org, repo, release, file, dest, force=False, fresh=False, verbose=False
):
    """Download a zip file from a release on github and unpack it.

    Parameters
    ----------
    org: string
        Organization on GitHub
    repo: string
        Repository within organization
    release: string
        The release version of the data to be downloaded.
    file: string
        The filename of the release attachment to fetch, without extension.
        The extension must be `.zip`
    dest: string
        The destination directory under which the contents of the zip is extracted.
    force: boolean, optional False
        Whether to force downloading data if the local copy matches the online copy
        by release version.

        If `False`: no re-download will take place. Otherwise the folder
        will be downloaded again.

        If `True`, the folder will be downloaded again, but the local copy will
        not be wiped on beforehand, so new files will overwrite existing files,
        but if the local copy contains additional material, it will be left in place.
    fresh: boolean, optional False
        Whether to clean the destination directory before extracting
    verbose: boolean, optional False
        If True, informational messages will be issued, otherwise only error messages
        will be issued.

    Returns
    -------
    boolean
        Whether the download and extraction was successful
    """
    url = f"https://github.com/{org}/{repo}/releases/download/{release}/{file}.zip"

    ssl._create_default_https_context = ssl._create_unverified_context
    console = consoleKit
    existingRelease = readSha(dest)

    if existingRelease == release and not force and not fresh:
        if verbose:
            console(f"Data already present: {release}/{file}.zip")
        return True

    cwd = getCwd()

    status = dict(downloaded=False, extracted=False)
    good = False

    try:
        r = requests.get(url, allow_redirects=True)
        if not r.ok:
            console(f"{r.reason}\n\tcould not download {url}", error=True)
        else:
            zf = r.content
            if verbose:
                console(f"{release}/{file}.zip downloaded having {len(zf)} bytes")

            status["downloaded"] = True
            zf = io.BytesIO(zf)
            z = ZipFile(zf)
            initTree(dest, fresh=fresh)
            chDir(dest)
            z.extractall()
            status["extracted"] = True
            dirRemove("__MACOSX")
            chDir(cwd)
            writeSha(dest, release)
            good = True
    except Exception as e:
        if not status["downloaded"]:
            console(f"{str(e)}\n\tcould not download {url}", error=True)
        elif not status["extracted"]:
            console(f"{str(e)}\n\tcould not extract to {dest}", error=True)
        else:
            console(f"{str(e)} could not complete the operation", error=True)

        good = False
        chDir(cwd)

    return good
