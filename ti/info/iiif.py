import collections

from ..kit.files import (
    writeJson,
    fileOpen,
    fileExists,
    fileCopy,
    initTree,
    dirContents,
    dirRemove,
    dirMake,
    dirNm,
    readYaml,
    stripExt,
    abspath,
)
from ..kit.generic import AttrDict
from ..kit.helpers import console, readCfg
from .helpers import PAGES

DS_STORE = ".DS_Store"

FILE_NOT_FOUND = "filenotfound"
FILE_NOT_FOUND_SIZES = (480, 640)


def fillinIIIF(data, **kwargs):
    tpd = type(data)

    if tpd is str:
        for k, v in kwargs.items():
            pattern = "{" + k + "}"

            if type(v) is int and data == pattern:
                data = v
                break
            else:
                data = data.replace(pattern, str(v))

        return data

    if tpd is list:
        return [fillinIIIF(item, **kwargs) for item in data]

    if tpd is dict:
        return {k: fillinIIIF(v, **kwargs) for (k, v) in data.items()}

    return data


def parseIIIF(settings, selector, **kwargs):
    """Parse the iiif yml file and deliver a filled in section.

    The iiif.yml file contains constants which are used to define IIIF things
    via templates.

    The top-level section `templates` contains fragments from which manifests can be
    constructed.

    This function prepares the constants and then uses them to assemble  the section
    in the yaml file based on the parameter `selector`.

    The constants are given as a list of dictionaries, where each value in such a
    dictionary may use constants defined in previous dictionaries.

    Parameters
    ----------
    selector: string
        Which top-level section we are going to grab out of the iiif.yml file.
        This can be any section in the yaml file, except `constants`.
    kwargs: dict
        Additional optional parameters to pass as key value pairs to
        the iiif config file. These values will be filled in for place holders
        of the form `[`*arg*`]`.

    Returns
    -------
    void or tuple
        If the constants do not resolve, or non-existing constants or arguments
        are being refererred to, None is returned.

        Otherwise, a tuple is returned with two members:

        *   an dict consisting of the resolved constants
        *   an AttrDict with resolved key value pairs from that section.
    """

    errors = []

    def resolveConstants():
        source = settings.get("constants", [])

        constants = {}

        for i, batch in enumerate(source):
            for k, v in batch.items():
                if type(v) is str:
                    for c, w in constants.items():
                        v = v.replace(f"«{c}»", str(w))
                    if "«" in v or "»" in v:
                        errors.append(
                            f"constant batch {i + 1}: value for {k} not resolved: {v}"
                        )

                constants[k] = v

        return constants

    def substituteConstants(data, constants, kwargs):
        tpd = type(data)

        if tpd is str:
            for k, v in constants.items():
                pattern = f"«{k}»"

                if type(v) is int and data == pattern:
                    data = v
                    break
                else:
                    data = data.replace(pattern, str(v))

            if type(data) is str:
                for k, v in kwargs.items():
                    pattern = f"[[{k}]]"

                    if type(v) is int and data == pattern:
                        data = v
                        break
                    else:
                        data = data.replace(pattern, str(v))

                if "«" in data or "»" in data or "[[" in data or "]]" in data:
                    errors.append(f"value not completely resolved: {data}")

            return data

        if tpd is list:
            return [substituteConstants(item, constants, kwargs) for item in data]

        if tpd is dict:
            return {
                k: substituteConstants(v, constants, kwargs) for (k, v) in data.items()
            }

        return data

    constants = resolveConstants()

    if len(errors):
        for e in errors:
            console(e)
        return None

    return (
        constants,
        AttrDict(
            {
                x: substituteConstants(xText, constants, kwargs)
                for (x, xText) in settings.get(selector, {}).items()
            }
        ),
    )


class IIIF:
    def __init__(
        self,
        infoDir,
        scanInfoDir,
        configPath,
        verbose=0,
    ):
        """Class for generating IIIF manifests.

        Parameters
        ----------
        infoDir: string
            Directory where the files with page information are, typically containing
            the result of an inventory by `ti.info.tei`
        scanInfoDir: string
            Directory where the files with scan information are, typically containing
            the sizes, colorspaces en rotations of the scans.
        configPath: string
            The configuration file that directs the shape of the manifests.
        verbose: integer, optional -1
            Produce no (-1), some (0) or many (1) progress and reporting messages

        """
        self.infoDir = infoDir
        self.scanInfoDir = scanInfoDir
        self.configPath = configPath
        self.verbose = verbose
        self.error = False

        (ok, settings) = readCfg(configPath, "iiif", verbose=verbose, plain=True)

        if verbose != -1:
            console(f"Source information taken from {infoDir}")

        if not ok:
            self.error = True
            return

        self.settings = settings
        myDir = dirNm(abspath(__file__))
        self.myDir = myDir

    def manifests(self, manifestDir, verbose=None, **kwargs):
        """Generate manifests.

        Parameters
        ----------
        manifestDir: string
            Manifests and logo will be generated in this directory.
        verbose: integer, optional None
            Produce no (-1), some (0) or many (1) progress and reporting messages
            If `None`, the value will be taken from the corresponding object member.
        kwargs: dict
            Additional optional parameters to pass as key value pairs to
            the iiif config file. These values will be filled in for place holders
            of the form `[`*arg*`]`.
        """

        if self.error:
            return

        if verbose is None:
            verbose = self.verbose

        self.manifestDir = manifestDir

        infoDir = self.infoDir
        settings = self.settings

        fileInfoFile = f"{infoDir}/files.yml"

        if not fileExists(fileInfoFile):
            console(f"File with folder/file info not found: {fileInfoFile}", error=True)
            self.error = True
            return

        files = readYaml(asFile=fileInfoFile, plain=True)
        excludedFolders = {
            k for k, v in settings.get("excludedFolders", {}).items() if v
        }
        if type(files) is not list:
            console(f"The file info in {fileInfoFile} should be a list", error=True)
            self.error = True
            return

        errors = []

        for item in files:
            if type(item) is not list or len(item) != 2:
                errors.append(f"Folder {repr(item)} : not a pair")
                continue

            (folder, fls) = item

            if type(fls) is not list:
                errors.append(f"Folder {folder} : {repr(fls)} is not a list")
                continue

            for file in fls:
                if type(file) is not str:
                    errors.append(f"Folder {folder}: {repr(file)} is not a string")

        if len(errors):
            for error in errors:
                console(error, error=True)

            self.errors = True
            return

        iFiles = [
            (fold, [f.removesuffix(".xml") for f in fl])
            for (fold, fl) in files
            if fold not in excludedFolders
        ]
        nFolders = len(iFiles)
        nFiles = sum(len(x[1]) for x in iFiles)

        self.files = iFiles
        files = self.files

        manifestLevel = settings.get("manifestLevel", "folder")
        self.manifestLevel = manifestLevel
        (self.constants, self.templates) = parseIIIF(settings, "templates", **kwargs)

        if verbose > -1:
            console("Parameters passed to manifest generation:")

            for k, v in sorted(kwargs.items()):
                console(f"\t{k:<10} = {v}")

            if verbose == 1:
                console("Values for the constants of the manifest generation:")

                for k, v in sorted(self.constants.items()):
                    console(f"\t{k:<10} = {v}")

            excludedFoldersStr = ", ".join(sorted(excludedFolders))
            console(f"Manifestlevel = {manifestLevel}")
            console(f"Excluded {manifestLevel} items: = {excludedFoldersStr}")

            console(f"{nFolders} folders and {nFiles} files, not counting exclusions")

        self.getSizes()
        self.getRotations()
        self.getPageSeq()
        pages = self.pages
        properPages = pages.get("pages", {})
        mLevelFolders = manifestLevel == "folder"

        if verbose > -1:
            console("Folders:")

        for item in files:
            folder = item if mLevelFolders else item[0]

            n = len(properPages[folder]) if folder in properPages else 0
            m = (
                None
                if mLevelFolders
                else (
                    sum(len(x) for x in properPages[folder].values())
                    if folder in properPages
                    else 0
                )
            )

            nP = n if mLevelFolders else m
            nF = m if mLevelFolders else n

            pageRep = f"{nP:>4} pages"
            fileRep = "" if nF is None else f"{nF:>4} files and "

            if folder not in properPages:
                console(
                    f"\t{folder:<10} with {fileRep}{pageRep} (not excluded in config)",
                    error=True,
                )
                self.error = True
                continue

            if verbose > -1:
                console(f"\t{folder:<10} with {fileRep}{pageRep}")

        manifestDir = self.manifestDir
        manifestLevel = self.manifestLevel
        infoDir = self.infoDir

        settings = self.settings

        initTree(manifestDir, fresh=True)

        missingFiles = {}
        self.missingFiles = missingFiles

        p = 0
        i = 0
        m = 0

        if manifestLevel == "folder":
            for folder in files:
                (thisP, thisI) = self.genPages("pages", folder=folder)
                p += thisP
                i += thisI

                if thisI:
                    m += 1
        else:
            for folder, fls in files:
                folderDir = f"{manifestDir}/{folder}"
                initTree(folderDir, fresh=True, gentle=False)

                folderI = 0

                for file in fls:
                    (thisP, thisI) = self.genPages("pages", folder=folder, file=file)
                    p += thisP
                    i += thisI

                    if thisI:
                        m += 1

                    folderI += thisI

                if folderI == 0:
                    dirRemove(folderDir)

        if len(missingFiles):
            console("Missing image files:", error=True)

        with fileOpen(f"{infoDir}/facsMissing.tsv", "w") as fh:
            fh.write("kind\tfile\tpage\tn\n")
            nMissing = 0

            for kind, fls in missingFiles.items():
                console(f"\t{kind}:", error=True)

                for file, pages in fls.items():
                    console(f"\t\t{file}:", error=True)

                    for page, n in pages.items():
                        console(f"\t\t\t{n:>3} x {page}", error=True)
                        nMissing += n

                        fh.write(f"{kind}\t{file}\t{page}\t{n}\n")

            console(f"\ttotal occurrences of a missing file: {nMissing}")

        if verbose > -1:
            console(
                f"{m} IIIF manifests with {i} items "
                f"for {p} pages generated in {manifestDir}"
            )

    def getRotations(self):
        if self.error:
            return

        verbose = self.verbose
        scanInfoDir = self.scanInfoDir
        prefix = "rotation_"
        suffix = ".tsv"

        rotateInfo = {}
        self.rotateInfo = rotateInfo

        n = 0
        nPages = 0

        for f in dirContents(scanInfoDir)[0]:
            if not f.startswith(prefix) or not f.endswith(suffix):
                continue

            kind = f.removeprefix(prefix).removesuffix(suffix).split("_", 1)[-1]

            if kind != PAGES:
                continue

            with fileOpen(f"{scanInfoDir}/{f}") as rh:
                next(rh)
                for line in rh:
                    fields = line.rstrip("\n").split("\t")
                    p = fields[0]
                    rot = int(fields[1])
                    rotateInfo.setdefault(kind, {})[p] = rot
                    n += 1

                    if rot != 0:
                        nPages += 1

        if n == 0:
            if verbose > -1:
                console(f"No rotation files found in {scanInfoDir}")
                return

        if verbose > -1:
            console(f"{nPages} pages have nonzero rotations")

    def getSizes(self):
        if self.error:
            return

        verbose = self.verbose
        scanInfoDir = self.scanInfoDir
        prefix = "sizes_"
        suffix = ".tsv"

        sizeInfo = {}
        self.sizeInfo = sizeInfo

        maxW, maxH = 0, 0
        totW, totH = 0, 0
        n = 0
        ws, hs = [], []

        for f in dirContents(scanInfoDir)[0]:
            if not f.startswith(prefix) or not f.endswith(suffix):
                continue

            kind = f.removeprefix(prefix).removesuffix(suffix).split("_", 1)[-1]

            if kind != PAGES:
                continue

            with fileOpen(f"{scanInfoDir}/{f}") as rh:
                next(rh)
                for line in rh:
                    fields = line.rstrip("\n").split("\t")
                    p = fields[0]
                    (w, h) = (int(x) for x in fields[1:3])
                    sizeInfo.setdefault(kind, {})[p] = (w, h)
                    ws.append(w)
                    hs.append(h)
                    n += 1
                    totW += w
                    totH += h

                    if w > maxW:
                        maxW = w
                    if h > maxH:
                        maxH = h

        if n == 0:
            console(f"No sizes files found in {scanInfoDir}", error=True)
            return

        avW = int(round(totW / n))
        avH = int(round(totH / n))

        devW = int(round(sum(abs(w - avW) for w in ws) / n))
        devH = int(round(sum(abs(h - avH) for h in hs) / n))

        if verbose > -1:
            console(f"Maximum dimensions: W = {maxW:>4} H = {maxH:>4}")
            console(f"Average dimensions: W = {avW:>4} H = {avH:>4}")
            console(f"Average deviation:  W = {devW:>4} H = {devH:>4}")

    def getPageSeq(self):
        if self.error:
            return

        manifestLevel = self.manifestLevel
        zoneBased = self.settings.get("zoneBased", False)

        verbose = self.verbose
        infoDir = self.infoDir
        facsFile = f"{infoDir}/facs.yml"

        if not fileExists(facsFile):
            console("No page-facsimile relating information found", error=True)
            return

        pagesProto = readYaml(asFile=facsFile, plain=True, preferTuples=False)

        if verbose > -1:
            console(f"Using facs file info file {facsFile}")

        pages = {}

        if zoneBased:
            facsMappingFile = f"{infoDir}/facsMapping.yml"

            if fileExists(facsMappingFile):
                console(f"Using facs mapping file {facsMappingFile}")
                facsMapping = readYaml(
                    asFile=facsMappingFile, plain=True, preferTuples=False
                )

                for path, ps in pagesProto.items():
                    pathComps = path.split("/")
                    folder = pathComps[0]

                    if manifestLevel == "file":
                        file = stripExt(pathComps[1])

                    mapping = facsMapping.get(path, {})
                    mappedPs = [mapping.get(p, p) for p in ps]
                    pagesDest = pages.setdefault(
                        folder, [] if manifestLevel == "folder" else {}
                    )

                    if manifestLevel == "folder":
                        pagesDest.extend(mappedPs)
                    else:
                        pagesDest.setdefault(file, []).extend(mappedPs)
            else:
                console(f"No facs mapping file {facsMappingFile}", error=True)
        else:
            for path, ps in pagesProto.items():
                (folder, file) = path.split("/")
                file = stripExt(file)
                pagesDest = pages.setdefault(
                    folder, [] if manifestLevel == "folder" else {}
                )
                pages.setdefault(folder, []).extend(ps)

                if manifestLevel == "folder":
                    pagesDest.extend(ps)
                else:
                    pagesDest.setdefault(file, []).extend(ps)

        if pages is None:
            console("Could not assemble page sequence info", error=True)
        else:
            result = dict(pages=pages)

        self.pages = result

    def genPages(self, kind, folder=None, file=None):
        if self.error:
            return (0, 0)

        constants = self.constants
        settings = self.settings
        scanInfoDir = self.scanInfoDir
        missingFiles = self.missingFiles
        manifestLevel = self.manifestLevel
        zoneBased = settings.get("zoneBased", False)
        templates = self.templates
        sizeInfo = self.sizeInfo.get(kind, {})
        rotateInfo = self.rotateInfo.get(kind, {})
        ext = constants.get("ext", "jpg")

        things = self.pages[kind]
        theseThings = things if folder is None else things.get(folder, None)

        if manifestLevel == "folder":
            thesePages = theseThings or []
        else:
            thesePages = (
                theseThings if file is None else (theseThings or {}).get(file, [])
            )

        pageItem = templates.pageItem

        itemsSeen = set()
        items = []
        nPages = 0

        for p in thesePages:
            nPages += 1

            if zoneBased:
                if type(p) is str:
                    (p, region) = (p, "full")
                elif len(p) == 0:
                    (p, region) = ("NA", "full")
                elif len(p) == 1:
                    (p, region) = (p[0], "full")
                else:
                    (p, region) = p[0:2]
            else:
                region = "full"

            scanPresent = p in sizeInfo

            if scanPresent:
                w, h = sizeInfo.get(p, (0, 0))
                rot = 0 if rotateInfo is None else rotateInfo.get(p, 0)
            else:
                missingFiles.setdefault(kind, {}).setdefault(
                    file, collections.Counter()
                )[p] += 1
                p = FILE_NOT_FOUND
                w, h = FILE_NOT_FOUND_SIZES
                rot = 0

            key = (p, w, h, rot)

            if key in itemsSeen:
                continue

            itemsSeen.add(key)

            if not scanPresent:
                myDir = self.myDir
                fof = f"{FILE_NOT_FOUND}.{ext}"
                fofInPath = f"{myDir}/fof/{fof}"
                fofOutDir = f"{scanInfoDir}/{kind}"
                fofOutPath = f"{fofOutDir}/{fof}"

                if not fileExists(fofOutPath):
                    dirMake(fofOutDir)
                    fileCopy(fofInPath, fofOutPath)

            item = {}

            for k, v in pageItem.items():
                v = fillinIIIF(
                    v,
                    folder=folder,
                    file=file,
                    page=p,
                    region=region,
                    width=w,
                    height=h,
                    rot=rot,
                )
                item[k] = v

            items.append(item)

        pageSequence = templates.pageSequence
        manifestDir = self.manifestDir

        data = {}

        for k, v in pageSequence.items():
            v = fillinIIIF(v, folder=folder, file=file)
            data[k] = v

        data["items"] = items

        nItems = len(items)

        if nItems:
            writeJson(
                data,
                asFile=(
                    f"{manifestDir}/{folder}.json"
                    if manifestLevel == "folder"
                    else f"{manifestDir}/{folder}/{file}.json"
                ),
            )
        return (nPages, nItems)
