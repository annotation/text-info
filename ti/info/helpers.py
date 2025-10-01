import re

from ..kit.generic import AttrDict
from ..kit.helpers import console
from ..kit.files import fileExists, readJson, readYaml, stripExt, fileOpen, dirExists


FOLDER = "folder"
FILE = "file"
LINE = "line"
LN = "ln"
PAGE = "page"
REGION = "region"
DOC = "doc"
CHAPTER = "chapter"
CHUNK = "chunk"


SECTION_MODELS = dict(
    I=dict(
        levels=(list, [FOLDER, FILE, CHUNK]),
        drillDownDivs=(bool, True),
        backMatter=(str, "backmatter"),
    ),
    II=dict(
        levels=(list, [CHAPTER, CHUNK]),
        element=(str, "head"),
        attributes=(dict, {}),
    ),
    III=dict(
        levels=(list, [FILE, CHAPTER, CHUNK]),
        element=(str, "head"),
        attributes=(dict, {}),
    ),
)
"""Models for sections.

A section is a part of the corpus that is defined by a set of files,
or by elements within a single TEI source file.

A model
"""


SECTION_MODEL_DEFAULT = "I"
"""Default model for sections.
"""


TOKEN_RE = re.compile(r"""\w+|\W""")
NUMBER_RE = re.compile(
    r"""
    ^
    [0-9]+
    (?:
        [.,]
        [0-9]+
    )*
    $
""",
    re.X,
)

W_BEFORE = re.compile(r"""^\s+""")
W_AFTER = re.compile(r"""\s+$""")


def repTokens(tokens):
    text = []
    for t, space in tokens:
        text.append(f"‹{t}›{space}")
    return "".join(text)


def checkSectionModel(thisModel, verbose):
    modelDefault = SECTION_MODEL_DEFAULT
    modelSpecs = SECTION_MODELS

    if thisModel is None:
        model = modelDefault

        if verbose == 1:
            console(f"WARNING: No section model specified. Assuming model {model}.")

        properties = {k: v[1] for (k, v) in modelSpecs[model].items()}
        return dict(model=model, properties=properties)

    if type(thisModel) is str:
        if thisModel in modelSpecs:
            thisModel = dict(model=thisModel)
        else:
            console(f"ERROR: unknown section model: {thisModel}")
            return False

    elif type(thisModel) is not dict:
        console(f"ERROR: section model must be a dict. You passed a {type(thisModel)}")
        return False

    model = thisModel.get("model", None)

    if model is None:
        model = modelDefault
        if verbose == 1:
            console(f"WARNING: No section model specified. Assuming model {model}.")
        thisModel["model"] = model

    if model not in modelSpecs:
        console(f"WARNING: unknown section model: {thisModel}")
        return False

    if verbose >= 0:
        console(f"section model is {model}")

    properties = {k: v for (k, v) in thisModel.items() if k != "model"}
    modelProperties = modelSpecs[model]

    good = True
    delKeys = []

    for k, v in properties.items():
        if k not in modelProperties:
            console(f"WARNING: ignoring unknown section model property {k}={v}")
            delKeys.append(k)
        elif type(v) is not modelProperties[k][0]:
            console(
                f"ERROR: section property {k} should have type {modelProperties[k][0]}"
                f" but {v} has type {type(v)}"
            )
            good = False
    if good:
        for k in delKeys:
            del properties[k]

    for k, v in modelProperties.items():
        if k not in properties:
            if verbose == 1:
                console(
                    f"WARNING: section model property {k} not specified, "
                    f"taking default {v[1]}"
                )
            properties[k] = v[1]

    if not good:
        return False

    return dict(model=model, properties=properties)


def getPageInfo(pageInfoDir, zoneBased, manifestLevel):
    if pageInfoDir is None:
        return {}

    pageInfoFile = f"{pageInfoDir}/pageseq.json"
    facsFile = f"{pageInfoDir}/facs.yml"

    pages = None

    if fileExists(pageInfoFile):
        console(f"Using page info file {pageInfoFile}")
        pages = readJson(asFile=pageInfoFile, plain=True)
    elif fileExists(facsFile):
        console(f"Using facs file info file {facsFile}")
        pagesProto = readYaml(asFile=facsFile, plain=True, preferTuples=False)
        pages = {}

        if zoneBased:
            facsMappingFile = f"{pageInfoDir}/facsMapping.yml"

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
    else:
        console("No page-facsimile relating information found", error=True)

    if pages is None:
        console("Could not assemble page sequence info", error=True)
        result = {}
    else:
        result = dict(pages=pages)

    return result


def getImageSizes(scanRefDir, doCovers, silent):
    sizeInfo = {}

    for kind in ("covers", "pages") if doCovers else ("pages",):
        sizeFile = f"{scanRefDir}/sizes_{kind}.tsv"

        thisSizeInfo = {}
        sizeInfo[kind] = thisSizeInfo

        maxW, maxH = 0, 0

        n = 0

        totW, totH = 0, 0

        ws, hs = [], []

        if not fileExists(sizeFile):
            console(f"Size file not found: {sizeFile}", error=True)
            continue

        with fileOpen(sizeFile) as rh:
            next(rh)
            for line in rh:
                fields = line.rstrip("\n").split("\t")
                p = fields[0]
                (w, h) = (int(x) for x in fields[1:3])
                thisSizeInfo[p] = (w, h)
                ws.append(w)
                hs.append(h)
                n += 1
                totW += w
                totH += h

                if w > maxW:
                    maxW = w
                if h > maxH:
                    maxH = h

        avW = int(round(totW / n))
        avH = int(round(totH / n))

        devW = int(round(sum(abs(w - avW) for w in ws) / n))
        devH = int(round(sum(abs(h - avH) for h in hs) / n))

        if not silent:
            console(f"Maximum dimensions: W = {maxW:>4} H = {maxH:>4}")
            console(f"Average dimensions: W = {avW:>4} H = {avH:>4}")
            console(f"Average deviation:  W = {devW:>4} H = {devH:>4}")

    return sizeInfo


def getImageLocations(app, prod, silent):
    repoLocation = app.repoLocation
    scanDir = f"{repoLocation}/scans"
    thumbDir = f"{repoLocation}/{app.context.provenanceSpec['graphicsRelative']}"
    scanRefDir = thumbDir if prod == "dev" else scanDir
    coversDir = f"{scanRefDir}/covers"

    if dirExists(coversDir):
        if not silent:
            console(f"Found covers in directory: {coversDir}")

        doCovers = True
    else:
        if not silent:
            console(f"No cover directory: {coversDir}")

        doCovers = False

    return AttrDict(
        repoLocation=repoLocation,
        scanDir=scanDir,
        thumbDir=thumbDir,
        scanRefDir=scanRefDir,
        coversDir=coversDir,
        doCovers=doCovers,
    )
