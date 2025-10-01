"""
# TEI info

TI knows the TEI elements, because it will read and parse the complete
TEI schema. From this the set of complex, mixed elements is distilled.

If the TEI source conforms to a customised TEI schema, it will be detected and
the importer will read it and override the generic information of the TEI elements.

It is also possible to pass a choice of template and adaptation in a processing
instruction. This does not influence validation, but it may influence further
processing.

If the TEI consists of multiple source files, it is possible to specify different
templates and adaptations for different files.

The possible values for models, templates, and adaptations should be declared in
the configuration file.
For each model there should be a corresponding schema in the schema directory,
either an RNG or an XSD file.

# Configuration and customization

You have to pass a specific additional file to the initializer of the TEI class:

*   `path/tei.yml` in which you specify a bunch of values to
    get the conversion off the ground.

## Keys and values of the `tei.yml` file

### `models`, `templates` and `adaptations`

list, optional `[]`

Which TEI-based schemas and editem templates and adaptations are to be used.

#### `models`

For each *model* there should be an XSD or RNG file with that name in the `schema`
directory. The `tei_all` schema is known to TF, no need to specify that one.

We'll try a RelaxNG schema (`.rng`) first. If that exists, we use it for validation
with JING, and we also convert it with TRANG to an XSD schema, which we use for
analysing the schema: we want to know which elements are mixed and pure.

If there is no RelaxNG schema, we try an XSD schema (`.xsd`). If that exists,
we can do the analysis, and we will use it also for validation.

!!! note "Problems with RelaxNG validation"
    RelaxNG validation is not always reliable when performed with LXML, or any tool
    based on `libxml`, for that matter. That's why we try to avoid it. Even if we
    translate the RelaxNG schema to an XSD schema by means of TRANG, the resulting
    validation is not always reliable. So we use JING to validate the RelaxNG schema.

See also [JING-TRANG](https://code.google.com/archive/p/jing-trang/downloads).

Suppose we have a model declared like so:

```
models:
  - suriano
```

The model is typically referenced in the TEI source file like so (it calls for the
`suriano` model):

```
<?xml-model
    href="https://xmlschema.huygens.knaw.nl/suriano.rng"
    type="application/xml"
    schematypens="http://relaxng.org/ns/structure/1.0"
?>
```

The convertor matches the `href` attribute with the `suriano` model by picking the
trailing part without extension from the href attribute.

In cases where this fails, you can specify the model as a dict in the yaml file.

Suppose we have a href attribute like this, which refers to the `dracor` model:

```
<?xml-model
    href="https://dracor.org/schema.rng"
    type="application/xml"
    schematypens="http://relaxng.org/ns/structure/1.0"
?>
```

You can specify this in the yaml file as follows:

```
models:
  - dracor: https://dracor.org/schema.rng
```

#### `templates`

Which template(s) are to be used.
A template is just a keyword, associated with an XML file, that can be used to switch
to a specific kind of processing, such as `letter`, `bibliolist`, `artworklist`.

You may specify an element or processing instruction with an attribute
that triggers the template for the file in which it is found.

This will be retrieved from the file before XML parsing starts.
For example,

``` python
    templateTrigger="?editem@template"
```

will read the file and extract the value of the `template` attribute of the `editem`
processing instruction and use that as the template for this file.
If no template is found in this way, the empty template is assumed.

#### `adaptations`

Which adaptations(s) are to be used.
An adaptation is just a keyword, associated with an XML file, that can be used to switch
to a specific kind of processing.
It is meant to trigger tweaks on top of the behaviour of a template.

You may specify an element or processing instruction with an attribute
that triggers the adaptation for the file in which it is found.

This will be retrieved from the file before XML parsing starts.
For example,

``` python
    adaptationTrigger="?editem@adaptation"
```

will read the file and extract the value of the `adaptation` attribute of the `editem`
processing instruction and use that as the adaptation for this file.
If no adaptation is found in this way, the empty adaptation is assumed.

### `sectionModel`

dict, optional `{}`

In model I, there are three section levels in total.
The corpus is divided in folders (section level 1), files (section level 2),
and chunks within files. The parameter `levels` allows you to choose names for the
node types of these section levels.

In model II, there are 2 section levels in total.
The corpus consists of a single file, and section nodes will be added
for nodes at various levels, mainly outermost `<div>` and `<p>` elements and their
siblings of other element types.
The section heading for the second level is taken from elements in the neighbourhood,
whose name is given in the parameter `element`, but only if they carry some attributes,
which can be specified in the `attributes` parameter.
These elements should be immediate children of the section elements in question.

In model III, there are 3 section levels in total.
The corpus consists of a single folder with several files (section level 1),
with two levels of sections per file, as in model II.

If not passed, or an empty dict, section model I is assumed.
A section model must be specified with the parameters relevant for the
model:

``` python
dict(
    model="II",
    levels=["chapter", "chunk"],
    element="head",
    attributes=dict(rend="h3"),
)
```

or

``` python
dict(
    model="III",
    levels=["file", "part", "chunk"],
    element="head",
    attributes=dict(rend="h3"),
)
```

(model I does not require the *element* and *attribute* parameters)

or

``` python
dict(
    model="I",
    levels=["folder", "file", "chunk"],
)
```

This section model (I) accepts a few other parameters:

``` python
    backMatter="backmatter"
```

This is the name of the folder that should not be treated as an ordinary folder, but
as the folder with the sources for the back-matter, such as references, lists, indices,
bibliography, biographies, etc.

For model II, the default parameters are:

``` python
element="head"
levels=["chapter", "chunk"],
attributes={}
```

For model III, the default parameters are:

``` python
element="head"
levels=["file", "part", "chunk"],
attributes={}
```

### `zoneBased`

boolean, optional `false`

Whether the `facs` attributes in `pb` elements refer to identifiers of
`surface` or `zone` elements.
If not, the `facs` attributes refer directly to file names.

These `surface` or `zone` elements must occur inside a `facsimile` element just
after the tei header. Inside that referred element
is a `graphics` element whose attribute `facs` contains the file name of the page
scan. This file name is a path with or without leading directories but without
extension.

On the `zone` element we expect the attributes `ulx`, `uly`, `lrx`, `lry` which
specify a region on the surface by their upper left and lower right points as
percentages from the origin of the surface. The origin is the upper left corner
of a surface. We transform these numbers into IIIF region specifications:

`pct:`*ulx*`,`*uly*`,`*lrx-ulx*`,`*lry-uly*

If we end up at a `surface`, instead of a `zone`, we provide the region specifier
`full`.
See the [IIIF Image API 3](https://iiif.io/api/image/3.0/#41-region).

In either case a report file facs.yml will be generated.

There is a key for each file for each file, and then a list of all `facs`
attribute values on `pb` elements.

If `zoneBased` is true, several more files are generated:

*   `facsMapping.yml`:
    a key for each file, and then for each declared surface or
    zone id within the fascimile element in that file: the url value of the
    graphics element encountered there, followed by `«»` and then the IIIF specification
    of the region as explained above.

*   `facsProblems.yml`:
    Two top-level keys: `facsNotDeclared` and `facsNotUsed`.
    Under each of these keys we have file keys and then:

    *   in case of `facsNotDeclared`: facs-attribute values that have no entry in the
        `facsMapping`;
    *   in case of `facsNotUsed`: graphic-url values that are not referred to by any
        `pb` element.

*   `zoneErrors.yml`:
    If zones lack one of their required metrics, they are listed here, plus the
    default that has been filled in for them.

Last but not least, if `zoneBased` is True, the page nodes will get two extra features:

*   `facsfile`: the filename without extension of the page scan
*   `facsregion`: the region specifier of the page on the page scan
```

"""

import collections
import re
from textwrap import wrap

from lxml import etree

from ..kit.helpers import console, versionSort, readCfg
from ..kit.files import (
    fileOpen,
    unexpanduser as ux,
    initTree,
    dirExists,
    fileExists,
    scanDir,
    writeYaml,
)

from .helpers import checkSectionModel

from ..tools.xmlschema import Analysis


FACS_MAPPING_YML = "facsMapping.yml"

TASKS_EXCLUDED = {"apptoken", "browse"}

PROGRESS_LIMIT = 5

REFERENCING = dict(
    ptr="target",
    ref="target",
    rs="ref",
)

ZONE_ATTS = (("ulx", 0), ("uly", 0), ("lrx", 100), ("lry", 100))


def getRefs(tag, atts, xmlFile):
    refAtt = REFERENCING.get(tag, None)
    result = []

    if refAtt is not None:
        refVal = atts.get(refAtt, None)
        if refVal is not None and not refVal.startswith("http"):
            for refv in refVal.split():
                parts = refv.split("#", 1)
                if len(parts) == 1:
                    targetFile = refv
                    targetId = ""
                else:
                    (targetFile, targetId) = parts
                if targetFile == "":
                    targetFile = xmlFile
                result.append((refAtt, targetFile, targetId))
    return result


class TEI:
    def __init__(self, sourceDir, cfgFile, verbose=0):
        """Sets up information retrieval from a TEI source.

        Parameters
        ----------
        sourceDir: string
            Directory of the TEI files.
            Divided as follows:

            1.  volumes / collections of documents. The subdirectory
                `__ignore__` is ignored.
            1.  the TEI documents themselves, conforming to the TEI schema or
                some customization of it.

        cfgFile: string
            Path to the configuration file (yaml)

        verbose: integer, optional -1
            Produce no (-1), some (0) or many (1) progress and reporting messages

        !!! note "Multiple XSD files"
            When you started with a RNG file and used `ti.tools.xmlschema` to
            convert it to XSD, you may have got multiple XSD files.
            One of them has the same base name as the original RNG file,
            and you should pass that name. It will import the remaining XSD files,
            so do not throw them away.

        """
        self.sourceDir = sourceDir
        self.cfgFile = cfgFile
        self.verbose = verbose

        self.good = True
        self.severeError = False
        self.fatalError = False

        (ok, settings) = readCfg(cfgFile, "tei", verbose=verbose, plain=True)
        if not ok:
            self.good = False

        models = settings.get("models", [])
        self.models = models

        procins = settings.get("procins", False)
        self.procins = procins

        zoneBased = settings.get("zoneBased", False)

        if zoneBased:
            self.facsMapping = None

        sectionModel = settings.get("sectionModel", {})
        sectionModel = checkSectionModel(sectionModel, verbose)

        if not sectionModel:
            self.good = False
            return

        sectionProperties = sectionModel["properties"]
        self.backMatter = sectionProperties.get("backMatter", None)
        sectionModel = sectionModel["model"]
        self.sectionModel = sectionModel
        self.sectionIs23 = sectionModel in {"II", "III"}
        self.sectionIs3 = sectionModel == "III"
        self.sectionProperties = sectionProperties

        templates = settings.get("templates", [])
        self.templates = templates

        adaptations = settings.get("adaptations", [])
        self.adaptations = adaptations

        self.zoneBased = zoneBased

        if not dirExists(sourceDir):
            console("Source directory does not exist: {sourceDir}", error=True)
            self.good = False
            return

        templateTrigger = settings.get("templateTrigger", None)
        adaptationTrigger = settings.get("adaptationTrigger", None)

        if templateTrigger is None:
            self.templateAtt = None
            self.templateTag = None
        else:
            (tag, att) = templateTrigger.split("@")
            self.templateAtt = att
            self.templateTag = tag

        templateTag = self.templateTag
        templateAtt = self.templateAtt

        if adaptationTrigger is None:
            self.adaptationAtt = None
            self.adaptationTag = None
        else:
            (tag, att) = adaptationTrigger.split("@")
            self.adaptationAtt = att
            self.adaptationTag = tag

        adaptationTag = self.adaptationTag
        adaptationAtt = self.adaptationAtt

        triggers = {}
        self.triggers = triggers

        for kind, theAtt, theTag in (
            ("template", templateAtt, templateTag),
            ("adaptation", adaptationAtt, adaptationTag),
        ):
            triggerRe = None

            if theAtt is not None and theTag is not None:
                tagPat = re.escape(theTag)
                triggerRe = re.compile(
                    rf"""<{tagPat}\b[^>]*?{theAtt}=['"]([^'"]+)['"]"""
                )
            triggers[kind] = triggerRe

        if not self.good:
            return

    def inventory(self, schemaDir, reportDir, carryon=False, verbose=None):
        """Implementation of the "check" task.

        It validates the TEI.

        Then it makes an inventory of all elements and attributes in the TEI files.

        If tags are used in multiple namespaces, it will be reported.

        !!! caution "Conflation of namespaces"
            The TEI to TF conversion does construct node types and attributes
            without taking namespaces into account.
            However, the parsing process is namespace aware.

        The inventory lists all elements and attributes, and many attribute values.
        But is represents any digit with `n`, and some attributes that contain
        ids or keywords, are reduced to the value `x`.

        This information reduction helps to get a clear overview.

        It writes reports to the `reportDir`:

        *   `errors.txt`: validation errors
        *   `elements.txt`: element / attribute inventory.

        !!! note "Thoroughness of validation"
            All xml files for the same model will be validated by a single call
            to the validator. This is fast, but the
            consequence is that after a fatal error the process terminates without
            validating the remaining files. In that case, we'll redo validation
            for each file separately.

        Parameters
        ----------
        reportDir: string
            The directory where the report files will be generated

        schemaDir: string
            Directory of the RNG/XSD schema files.

            We use these files as custom TEI schemas,
            but to be sure, we still analyse the full TEI schema and
            use the schemas here as a set of overriding element definitions.

        carryon: boolean, optional False
            Whether to carryon with making an inventory if validation has failed.
            Normally, validation errors make it unlikely that further processing of
            the XML will succeed. But if the validation errors appear to be mild,
            and you want an inventory, you can pass the `True` to this parameter
            at your own risk.
        verbose: integer, optional None
            Produce no (-1), some (0) or many (1) progress and reporting messages
            If `None`, the value will be taken from the corresponding object member.
        """
        if not self.good:
            return

        if not reportDir:
            console("No report directory specified", error=True)
            self.good = False

        self.schemaDir = schemaDir

        A = Analysis(verbose=verbose)
        self.A = A
        self.readSchemas()

        procins = self.procins
        modelInfo = self.modelInfo
        modelInv = self.modelInv
        modelXsd = self.modelXsd

        sourceDir = self.sourceDir
        sectionModel = self.sectionModel
        zoneBased = self.zoneBased

        if verbose == 1:
            console(f"TEI to TF checking: {ux(sourceDir)} => {ux(reportDir)}")
        if verbose >= 0:
            console(
                f"Processing instructions are {'treated' if procins else 'ignored'}"
            )
            console("XML validation will be performed")

        kindLabels = dict(
            format="Formatting Attributes",
            keyword="Keyword Attributes",
            rest="Remaining Attributes and Elements",
        )
        getStore = lambda: collections.defaultdict(  # noqa: E731
            lambda: collections.defaultdict(collections.Counter)
        )
        analysis = {x: getStore() for x in kindLabels}
        errors = []
        tagByNs = collections.defaultdict(collections.Counter)
        refs = collections.defaultdict(lambda: collections.Counter())
        ids = collections.defaultdict(lambda: collections.Counter())

        parser = self.getParser()
        baseSchema = modelXsd[None]
        overrides = [
            override for (model, override) in modelXsd.items() if model is not None
        ]
        A.getElementInfo(baseSchema, overrides, verbose=verbose)
        elementDefs = A.elementDefs

        initTree(reportDir)

        nProcins = 0

        lbParents = collections.Counter()

        pageScans = {}

        facsMapping = {} if zoneBased else {}
        self.facsMapping = facsMapping

        facsKind = {}
        self.facsKind = {}

        facsNotDeclared = {}
        zoneRegionIncomplete = {}
        facsNoId = {}
        self.facsNoId = facsNoId

        nPagesNoFacs = 0

        inFacsimile = False
        surfaceId = None
        scanFile = None
        zoneId = None
        zoneRegion = None

        def analyse(root, analysis, xmlPath):
            FORMAT_ATTS = set(
                """
                dim
                level
                place
                rend
            """.strip().split()
            )

            KEYWORD_ATTS = set(
                """
                facs
                form
                function
                lang
                reason
                type
                unit
                who
            """.strip().split()
            )

            TRIM_ATTS = set(
                """
                id
                key
                target
                value
            """.strip().split()
            )

            NUM_RE = re.compile(r"""[0-9]""", re.S)

            def nodeInfo(xnode):
                nonlocal nProcins
                nonlocal nPagesNoFacs
                nonlocal inFacsimile
                nonlocal surfaceId
                nonlocal scanFile
                nonlocal zoneId
                nonlocal zoneRegion

                if procins and isinstance(xnode, etree._ProcessingInstruction):
                    target = xnode.target
                    tag = f"?{target}"
                    ns = ""
                    nProcins += 1
                else:
                    qName = etree.QName(xnode.tag)
                    tag = qName.localname
                    ns = qName.namespace

                atts = {etree.QName(k).localname: v for (k, v) in xnode.attrib.items()}

                tagByNs[tag][ns] += 1

                if tag == "lb":
                    parentTag = etree.QName(xnode.getparent().tag).localname
                    lbParents[parentTag] += 1
                elif tag == "pb":
                    facsv = atts.get("facs", "")

                    if zoneBased:
                        facsv = facsv.removeprefix("#")

                        if facsv:
                            (scanName, scanRegion) = facsMapping[xmlPath].get(
                                facsv, ["", "full"]
                            )

                            if not scanName:
                                facsNotDeclared[xmlPath].add(facsv)

                    if facsv:
                        pageScans[xmlPath].append(facsv)
                    else:
                        nPagesNoFacs += 1
                elif zoneBased:
                    if tag == "facsimile":
                        inFacsimile = True
                    elif inFacsimile:
                        if tag == "surface":
                            surfaceId = atts.get("id", None)
                            scanFile = None

                            if not surfaceId:
                                facsNoId[xmlPath]["surface"] += 1
                        elif tag == "zone":
                            zoneId = atts.get("id", None)

                            if zoneId:
                                zoneRegion = []

                                for a, aDefault in ZONE_ATTS:
                                    aVal = atts.get(a, None)

                                    if aVal is None:
                                        aVal = aDefault
                                        zoneRegionIncomplete.setdefault(zoneId, {})[
                                            a
                                        ] = f"None => {aDefault}"
                                    elif aVal.isdecimal():
                                        aVal = int(aVal)
                                    else:
                                        zoneRegionIncomplete.setdefault(zoneId, {})[
                                            a
                                        ] = f"{aVal} => {aDefault}"

                                    zoneRegion.append(aVal)

                                (ulx, uly, lrx, lry) = zoneRegion
                                zoneRegion = f"pct:{ulx},{uly},{lrx - ulx},{lry - uly}"

                                if scanFile:
                                    facsMapping[xmlPath][zoneId] = [
                                        scanFile,
                                        zoneRegion,
                                    ]
                                    facsKind[xmlPath][zoneId] = "zone"
                            else:
                                facsNoId[xmlPath]["zone"] += 1

                        elif tag == "graphic":
                            # can be inside zone or inside surface
                            # if inside surface, it holds for all zones without
                            # own scanFile
                            thisScanFile = atts.get("url", None)

                            if thisScanFile is not None:
                                if zoneId:
                                    facsMapping[xmlPath][zoneId] = [
                                        thisScanFile,
                                        zoneRegion,
                                    ]
                                    facsKind[xmlPath][zoneId] = "zone"
                                else:
                                    # this is a graphic outside the zones
                                    # we set the surface wide scan file
                                    # so that subsequent zones without graphic
                                    # can pick this up
                                    scanFile = thisScanFile
                                if surfaceId:
                                    facsMapping[xmlPath][surfaceId] = [scanFile, "full"]
                                    facsKind[xmlPath][surfaceId] = "surface"

                if len(atts) == 0:
                    kind = "rest"
                    analysis[kind][tag][""][""] += 1
                else:
                    idv = atts.get("id", None)

                    if idv is not None:
                        ids[xmlPath][idv] += 1

                    for refAtt, targetFile, targetId in getRefs(tag, atts, xmlPath):
                        refs[xmlPath][(targetFile, targetId)] += 1

                    for k, v in atts.items():
                        kind = (
                            "format"
                            if k in FORMAT_ATTS
                            else "keyword" if k in KEYWORD_ATTS else "rest"
                        )
                        dest = analysis[kind]

                        if kind == "rest":
                            vTrim = "X" if k in TRIM_ATTS else NUM_RE.sub("N", v)
                            dest[tag][k][vTrim] += 1
                        else:
                            words = v.strip().split()
                            for w in words:
                                dest[tag][k][w.strip()] += 1

                for child in xnode.iterchildren(
                    tag=(
                        (etree.Element, etree.ProcessingInstruction)
                        if procins
                        else etree.Element
                    )
                ):
                    nodeInfo(child)

                if zoneBased:
                    if tag == "facsimile":
                        inFacsimile = False
                    elif inFacsimile:
                        if tag == "surface":
                            surfaceId = None
                            scanFile = None
                        elif tag == "zone":
                            zoneId = None

            nodeInfo(root)

        def writeErrors():
            """Write the errors to a file."""

            errorFile = f"{reportDir}/errors.txt"

            nErrors = 0
            nFiles = 0

            with fileOpen(errorFile, mode="w") as fh:
                prevFolder = None
                prevFile = None

                for folder, file, line, col, kind, text in errors:
                    newFolder = prevFolder != folder
                    newFile = newFolder or prevFile != file

                    if newFile:
                        nFiles += 1

                    if kind in {"error", "fatal"}:
                        nErrors += 1

                    indent1 = f"{folder}\n\t" if newFolder else "\t"
                    indent2 = f"{file}\n\t\t" if newFile else "\t"
                    loc = f"{line or ''}:{col or ''}"
                    text = "\n".join(wrap(text, width=80, subsequent_indent="\t\t\t"))
                    fh.write(f"{indent1}{indent2}{loc} {kind or ''} {text}\n")
                    prevFolder = folder
                    prevFile = file

            if nErrors:
                console(
                    (
                        f"{nErrors} validation error(s) in {nFiles} file(s) "
                        f"written to {errorFile}"
                    ),
                    error=True,
                )
            else:
                if verbose >= 0:
                    console("Validation OK")

        def writeFacs():
            infoFile = f"{reportDir}/facsNoId.yml"
            writeYaml(
                {
                    f: {k: n for (k, n) in v.items() if n}
                    for (f, v) in facsNoId.items()
                    if len(v)
                },
                asFile=infoFile,
            )

            nSurfaces = sum(x["surface"] for x in facsNoId.values())
            nZones = sum(x["zone"] for x in facsNoId.values())

            if verbose >= 0:
                pluralS = "" if nSurfaces == 1 else "s"
                pluralZ = "" if nZones == 1 else "s"

                if nSurfaces:
                    console(f"{nSurfaces} surface{pluralS} without id")

                if nZones:
                    console(f"{nZones} zone{pluralZ} without id")

            infoFile = f"{reportDir}/facs.yml"
            nItems = sum(len(x) for x in pageScans.values())
            nUnique = sum(len(set(x)) for x in pageScans.values())

            writeYaml(pageScans, asFile=infoFile)

            if verbose >= 0:
                plural = "" if nPagesNoFacs == 1 else "s"
                console(f"{nPagesNoFacs} pagebreak{plural} without facs attribute.")

                plural = "" if nItems == 1 else "s"
                console(f"{nItems} pagebreak{plural} encountered.")
                plural = "" if nUnique == 1 else "s"
                console(f"{nUnique} distinct scan{plural} referred to by pagebreaks.")

            if not zoneBased:
                return

            infoFile = f"{reportDir}/facsKind.yml"
            writeYaml(facsKind, asFile=infoFile)
            infoFile = f"{reportDir}/{FACS_MAPPING_YML}"
            writeYaml(facsMapping, asFile=infoFile)

            if verbose >= 0:
                nSurfaces = sum(
                    sum(1 for y in x.values() if y == "surface")
                    for x in facsKind.values()
                )
                nZones = sum(
                    sum(1 for y in x.values() if y == "zone") for x in facsKind.values()
                )
                plural = "" if nSurfaces == 1 else "s"
                console(f"{nSurfaces} surface{plural} declared")
                plural = "" if nZones == 1 else "s"
                console(f"{nZones} zone{plural} declared")

                nItems = sum(len(x) for x in facsMapping.values())
                plural = "" if nItems == 1 else "s"
                console(f"{nItems} scan{plural} declared and mapped.")

            infoFile = f"{reportDir}/facsProblems.yml"
            facsNotUsed = {}

            for xmlPath, mapping in facsMapping.items():
                facsEncountered = set(pageScans[xmlPath])
                thisFacsNotUsed = {}

                for facs in mapping:
                    if facs not in facsEncountered:
                        kind = facsKind[xmlPath][facs]
                        thisFacsNotUsed.setdefault(kind, []).append(facs)

                if len(thisFacsNotUsed):
                    facsNotUsed[xmlPath] = thisFacsNotUsed

            facsProblems = {}

            nFacsNotDeclared = sum(len(x) for x in facsNotDeclared.values())
            nSurfacesNotUsed = sum(
                len(x.get("surface", [])) for x in facsNotUsed.values()
            )
            nZonesNotUsed = sum(len(x.get("zone", [])) for x in facsNotUsed.values())

            if nFacsNotDeclared:
                plural = "" if nFacsNotDeclared == 1 else "s"
                console(f"{nFacsNotDeclared} undeclared scan{plural}", error=True)
                facsProblems["facsNotDeclared"] = {
                    xmlPath: sorted(x)
                    for (xmlPath, x) in facsNotDeclared.items()
                    if len(x)
                }

            if nSurfacesNotUsed:
                plural = "" if nSurfacesNotUsed == 1 else "s"
                console(f"{nSurfacesNotUsed} unused surface{plural}", error=True)
            if nZonesNotUsed:
                plural = "" if nZonesNotUsed == 1 else "s"
                console(f"{nZonesNotUsed} unused zone{plural}", error=True)

            facsProblems["facsNotUsed"] = facsNotUsed

            writeYaml(facsProblems, asFile=infoFile)

            infoFile = f"{reportDir}/zoneErrors.yml"
            nIncomplete = len(zoneRegionIncomplete)
            plural = "" if nIncomplete == 1 else "s"

            if nIncomplete:
                console(
                    f"{nIncomplete} missing zone region specifier{plural}", error=True
                )

                console(f"See {infoFile}", error=True)

            writeYaml(zoneRegionIncomplete, asFile=infoFile)

        def writeNamespaces():
            errorFile = f"{reportDir}/namespaces.txt"

            nErrors = 0

            nTags = len(tagByNs)

            with fileOpen(errorFile, mode="w") as fh:
                for tag, nsInfo in sorted(
                    tagByNs.items(), key=lambda x: (-len(x[1]), x[0])
                ):
                    label = "OK"
                    nNs = len(nsInfo)
                    if nNs > 1:
                        nErrors += 1
                        label = "XX"

                    for ns, amount in sorted(
                        nsInfo.items(), key=lambda x: (-x[1], x[0])
                    ):
                        fh.write(
                            f"{label} {nNs:>2} namespace for "
                            f"{tag:<16} : {amount:>5}x {ns}\n"
                        )

            if verbose >= 0:
                if procins:
                    plural = "" if nProcins == 1 else "s"
                    console(f"{nProcins} processing instruction{plural} encountered.")

                console(
                    (
                        f"{nTags} tags of which {nErrors} with multiple namespaces "
                        f"written to {errorFile}"
                        if verbose >= 0 or nErrors
                        else "Namespaces OK"
                    ),
                    error=nErrors > 0,
                )

        def writeReport():
            reportFile = f"{reportDir}/elements.txt"

            with fileOpen(reportFile, mode="w") as fh:
                fh.write(
                    "Inventory of tags and attributes in the source XML file(s).\n"
                    "Contains the following sections:\n"
                )
                for label in kindLabels.values():
                    fh.write(f"\t{label}\n")
                fh.write("\n\n")

                infoLines = 0

                def writeAttInfo(tag, att, attInfo):
                    nonlocal infoLines
                    nl = "" if tag == "" else "\n"
                    tagRep = "" if tag == "" else f"<{tag}>"
                    attRep = "" if att == "" else f"{att}="
                    atts = sorted(attInfo.items())
                    (val, amount) = atts[0]
                    fh.write(
                        f"{nl}\t{tagRep:<18} " f"{attRep:<11} {amount:>7}x {val}\n"
                    )
                    infoLines += 1

                    for val, amount in atts[1:]:
                        fh.write(f"""\t{'':<18} {'':<11} {amount:>7}x {val}\n""")
                        infoLines += 1

                def writeTagInfo(tag, tagInfo):
                    nonlocal infoLines
                    tags = sorted(tagInfo.items())
                    (att, attInfo) = tags[0]
                    writeAttInfo(tag, att, attInfo)
                    infoLines += 1
                    for att, attInfo in tags[1:]:
                        writeAttInfo("", att, attInfo)

                for kind, label in kindLabels.items():
                    fh.write(f"\n{label}\n")
                    for tag, tagInfo in sorted(analysis[kind].items()):
                        writeTagInfo(tag, tagInfo)

            if verbose >= 0:
                console(f"{infoLines} info line(s) written to {reportFile}")

        def writeElemTypes():
            elemsCombined = {}

            modelSet = set()

            for schemaOverride, eDefs in elementDefs.items():
                model = modelInv[schemaOverride]
                modelSet.add(model)
                for tag, (typ, mixed) in eDefs.items():
                    elemsCombined.setdefault(tag, {}).setdefault(model, {})
                    elemsCombined[tag][model]["typ"] = typ
                    elemsCombined[tag][model]["mixed"] = mixed

            tagReport = {}

            for tag, tagInfo in elemsCombined.items():
                tagLines = []
                tagReport[tag] = tagLines

                if None in tagInfo:
                    teiInfo = tagInfo[None]
                    teiTyp = teiInfo["typ"]
                    teiMixed = teiInfo["mixed"]
                    teiTypRep = "??" if teiTyp is None else typ
                    teiMixedRep = (
                        "??" if teiMixed is None else "mixed" if teiMixed else "pure"
                    )
                    mds = ["TEI"]

                    for model in sorted(x for x in tagInfo if x is not None):
                        info = tagInfo[model]
                        typ = info["typ"]
                        mixed = info["mixed"]
                        if typ == teiTyp and mixed == teiMixed:
                            mds.append(model)
                        else:
                            typRep = (
                                "" if typ == teiTyp else "??" if typ is None else typ
                            )
                            mixedRep = (
                                ""
                                if mixed == teiMixed
                                else (
                                    "??"
                                    if mixed is None
                                    else "mixed" if mixed else "pure"
                                )
                            )
                            tagLines.append((tag, [model], typRep, mixedRep))
                    tagLines.insert(0, (tag, mds, teiTypRep, teiMixedRep))
                else:
                    for model in sorted(tagInfo):
                        info = tagInfo[model]
                        typ = info["typ"]
                        mixed = info["mixed"]
                        typRep = "??" if typ is None else typ
                        mixedRep = (
                            "??" if mixed is None else "mixed" if mixed else "pure"
                        )
                        tagLines.append((tag, [model], typRep, mixedRep))

            reportFile = f"{reportDir}/types.txt"

            with fileOpen(reportFile, mode="w") as fh:
                for tag in sorted(tagReport):
                    tagLines = tagReport[tag]

                    for tag, mds, typ, mixed in tagLines:
                        model = ",".join(mds)
                        fh.write(
                            f"{tag:<18} {model:<18} {typ or '':<7} {mixed or '':<5}\n"
                        )

            if verbose >= 0:
                console(
                    f"{len(elemsCombined)} tag(s) type info written to {reportFile}"
                )

        def writeLbParents():
            reportFile = f"{reportDir}/lb-parents.txt"

            with fileOpen(reportFile, "w") as fh:
                for parent, n in sorted(lbParents.items()):
                    fh.write(f"{n:>5} x {parent}\n")

            if verbose >= 0:
                console(f"lb-parent info written to {reportFile}")

        def writeIdRefs():
            reportIdFile = f"{reportDir}/ids.txt"
            reportRefFile = f"{reportDir}/refs.txt"

            ih = fileOpen(reportIdFile, mode="w")
            rh = fileOpen(reportRefFile, mode="w")

            refdIds = collections.Counter()
            missingIds = set()

            totalRefs = 0
            totalRefsU = 0

            totalResolvable = 0
            totalResolvableU = 0
            totalDangling = 0
            totalDanglingU = 0

            seenItems = set()

            for file, items in refs.items():
                rh.write(f"{file}\n")

                resolvable = 0
                resolvableU = 0
                dangling = 0
                danglingU = 0

                for item, n in sorted(items.items()):
                    totalRefs += n

                    if item in seenItems:
                        newItem = False
                    else:
                        seenItems.add(item)
                        newItem = True
                        totalRefsU += 1

                    (target, idv) = item

                    if target not in ids or idv not in ids[target]:
                        status = "dangling"
                        dangling += n

                        if newItem:
                            missingIds.add((target, idv))
                            danglingU += 1
                    else:
                        status = "ok"
                        resolvable += n
                        refdIds[(target, idv)] += n

                        if newItem:
                            resolvableU += 1
                    rh.write(f"\t{status:<10} {n:>5} x {target} # {idv}\n")

                msgs = (
                    f"\tDangling:   {dangling:>4} x {danglingU:>4}",
                    f"\tResolvable: {resolvable:>4} x {resolvableU:>4}",
                )
                for msg in msgs:
                    rh.write(f"{msg}\n")

                totalResolvable += resolvable
                totalResolvableU += resolvableU
                totalDangling += dangling
                totalDanglingU += danglingU

            if verbose >= 0:
                console(f"Refs written to {reportRefFile}")
                msgs = (
                    f"\tresolvable: {totalResolvableU:>4} in {totalResolvable:>4}",
                    f"\tdangling:   {totalDanglingU:>4} in {totalDangling:>4}",
                    f"\tALL:        {totalRefsU:>4} in {totalRefs:>4} ",
                )
                for msg in msgs:
                    console(msg)

            totalIds = 0
            totalIdsU = 0
            totalIdsM = 0
            totalIdsRefd = 0
            totalIdsRefdU = 0
            totalIdsUnused = 0

            for file, items in ids.items():
                totalIds += len(items)

                ih.write(f"{file}\n")

                unique = 0
                multiple = 0
                refd = 0
                refdU = 0
                unused = 0

                for item, n in sorted(items.items()):
                    nRefs = refdIds.get((file, item), 0)

                    if n == 1:
                        unique += 1
                    else:
                        multiple += 1

                    if nRefs == 0:
                        unused += 1
                    else:
                        refd += nRefs
                        refdU += 1

                    status1 = f"{n}x"
                    plural = "" if nRefs == 1 else "s"
                    status2 = f"{nRefs}ref{plural}"

                    ih.write(f"\t{status1:<8} {status2:<8} {item}\n")

                msgs = (
                    f"\tUnique:     {unique:>4}",
                    f"\tNon-unique: {multiple:>4}",
                    f"\tUnused:     {unused:>4}",
                    f"\tReferenced: {refd:>4} x {refdU:>4}",
                )
                for msg in msgs:
                    ih.write(f"{msg}\n")

                totalIdsU += unique
                totalIdsM += multiple
                totalIdsRefdU += refdU
                totalIdsRefd += refd
                totalIdsUnused += unused

            if verbose >= 0:
                console(f"Ids written to {reportIdFile}")
                msgs = (
                    f"\treferenced: {totalIdsRefdU:>4} by {totalIdsRefd:>4}",
                    f"\tnon-unique: {totalIdsM:>4}",
                    f"\tunused:     {totalIdsUnused:>4}",
                    f"\tALL:        {totalIdsU:>4} in {totalIds:>4}",
                )
                for msg in msgs:
                    console(msg)

        def filterError(msg):
            return msg == (
                "Element 'graphic', attribute 'url': [facet 'pattern'] "
                "The value '' is not accepted by the pattern '\\S+'."
            )

        def doXMLFile(xmlPath):
            xmlFullPath = f"{sourceDir}/{xmlPath}"
            pageScans[xmlPath] = []
            facsMapping[xmlPath] = {}
            facsKind[xmlPath] = {}
            facsNotDeclared[xmlPath] = set()
            facsNoId[xmlPath] = collections.Counter()

            root = self.parseXML(xmlPath, xmlFullPath, parser)

            if root is None:
                return

            ids[xmlFile][""] = 1
            analyse(root, analysis, xmlPath)

        xmlFilesByModel = collections.defaultdict(list)

        if sectionModel == "I":
            for xmlFolder, xmlFiles in self.getXML():
                msg = "Start " if verbose >= 0 else "\t"

                if verbose >= 0:
                    console(f"\t{msg}folder {xmlFolder}")

                for xmlFile in xmlFiles:
                    xmlPath = f"{xmlFolder}/{xmlFile}"
                    xmlFullPath = f"{sourceDir}/{xmlPath}"
                    (model, adapt, tpl) = self.getSwitches(xmlFullPath)
                    xmlFilesByModel[model].append(xmlPath)

        elif sectionModel == "II":
            xmlFile = self.getXML()

            if xmlFile is None:
                console("No XML files found!", error=True)
                return False

            xmlFullPath = f"{sourceDir}/{xmlFile}"
            (model, adapt, tpl) = self.getSwitches(xmlFullPath)
            xmlFilesByModel[model].append(xmlFile)

        elif sectionModel == "III":
            for xmlFile in self.getXML():
                xmlFullPath = f"{sourceDir}/{xmlFile}"
                (model, adapt, tpl) = self.getSwitches(xmlFullPath)
                xmlFilesByModel[model].append(xmlFile)

        good = True
        severeError = False
        fatalError = False

        for model, xmlPaths in xmlFilesByModel.items():
            if verbose >= 0:
                console(f"{len(xmlPaths)} {model or 'TEI'} file(s) ...")

            thisGood = True

            if verbose >= 0:
                console("\tValidating ...")

            schemaFile = modelInfo.get(model, None)

            if schemaFile is None:
                if verbose >= 0:
                    console(f"\t\tNo schema file for {model}")
                if good is not None and good is not False:
                    good = None
                continue

            (thisGood, info, theseErrors) = A.validate(
                True,
                schemaFile,
                [f"{sourceDir}/{xmlPath}" for xmlPath in xmlPaths],
            )
            if thisGood == -1:  # severe error, validation machinery not good
                severeError = True

            elif thisGood is None:
                fatalError = True

                # redo validation for each file separately in order to get all
                # fatal errors
                console("Fatal error in one of the XML files", error=True)

                rInfo = [*info]
                rTheseErrors = [*theseErrors]
                rXmlPaths = [*xmlPaths]

                iteration = 0
                maxIter = 20

                while True:
                    iteration += 1

                    if iteration > maxIter:
                        console(
                            "Stopped looking for more fatal errors after "
                            f"{maxIter} iterations",
                            error=True,
                        )
                        break

                    fatalPath = None

                    for e in rTheseErrors:
                        kind = e[4]

                        if kind == "fatal":
                            (folder, file) = e[0:2]
                            fatalPath = f"{folder}/{file}"

                    if fatalPath is None:
                        console("No more fatal errors", error=True)
                        break

                    console(
                        "Check for more fatal errors "
                        f"(iteration {iteration} of up to {maxIter}) "
                        f"after {fatalPath}",
                        error=True,
                    )
                    newRXmlPaths = []

                    skipping = True

                    for xmlPath in rXmlPaths:
                        if skipping:
                            if xmlPath == fatalPath:
                                skipping = False
                        else:
                            newRXmlPaths.append(xmlPath)

                    if not len(newRXmlPaths):
                        console("No more files to examine", error=True)
                        break

                    rXmlPaths = newRXmlPaths
                    (thisRGood, rInfo, rTheseErrors) = A.validate(
                        True,
                        schemaFile,
                        [f"{sourceDir}/{xmlPath}" for xmlPath in rXmlPaths],
                        verbose=True,
                    )

                    info.extend(rInfo)
                    theseErrors.extend(rTheseErrors)

                    if thisRGood is not None:
                        console("Last fatal error encountered", error=True)
                        break

            for line in info:
                if verbose >= 0:
                    console(f"\t\t{line}")

            if severeError:
                for err in theseErrors:
                    console(err, error=True)

                self.severeError = True
                break

            if fatalError:
                self.fatalError = True

            if not thisGood:
                good = False

                errors.extend(theseErrors)

                if not carryon:
                    continue

            if (good or carryon) and verbose >= 0:
                console("\tMaking inventory ...")

            for xmlPath in xmlPaths:
                doXMLFile(xmlPath)

        if not good:
            self.good = False

        if verbose >= 0:
            console("")

        writeElemTypes()

        if not self.severeError:
            writeErrors()

        if good or carryon:
            writeFacs()
            writeNamespaces()
            writeReport()
            writeIdRefs()
            writeLbParents()

    def readSchemas(self):
        schemaDir = self.schemaDir
        models = self.models
        modelMap = {}
        newModels = []
        self.modelMap = modelMap

        A = self.A

        schemaFiles = dict(rng={}, xsd={})
        self.schemaFiles = schemaFiles
        modelInfo = {}
        self.modelInfo = modelInfo
        modelXsd = {}
        self.modelXsd = modelXsd
        modelInv = {}
        self.modelInv = modelInv

        for model in [None] + models:
            if type(model) is dict:
                (model, href) = list(model.items())[0]
                modelMap[href] = model

            if model is not None:
                newModels.append(model)

            for kind in ("rng", "xsd"):
                schemaFile = (
                    A.getBaseSchema()[kind]
                    if model is None
                    else f"{schemaDir}/{model}.{kind}"
                )
                if fileExists(schemaFile):
                    schemaFiles[kind][model] = schemaFile
                    if (
                        kind == "rng"
                        or kind == "xsd"
                        and model not in schemaFiles["rng"]
                    ):
                        modelInfo[model] = schemaFile

            if model in schemaFiles["rng"] and model not in schemaFiles["xsd"]:
                schemaFileXsd = f"{schemaDir}/{model}.xsd"
                result = A.fromrelax(schemaFiles["rng"][model], schemaFileXsd)

                if not result:
                    console(
                        f"Could not convert relax schema {model} to xsd", error=True
                    )
                    self.good = False

                    if result is None:
                        self.severeError = True
                        return

                schemaFiles["xsd"][model] = schemaFileXsd

        models = newModels
        self.models = models

        baseSchema = schemaFiles["xsd"][None]
        modelXsd[None] = baseSchema
        modelInv[(baseSchema, None)] = None

        for model in models:
            override = schemaFiles["xsd"][model]
            modelXsd[model] = override
            modelInv[(baseSchema, override)] = model

    def getSwitches(self, xmlPath):
        verbose = self.verbose
        models = self.models
        modelMap = self.modelMap
        adaptations = self.adaptations
        templates = self.templates
        triggers = self.triggers
        A = self.A

        text = None

        found = {}

        for kind, allOfKind in (
            ("model", models),
            ("adaptation", adaptations),
            ("template", templates),
        ):
            if text is None:
                with fileOpen(xmlPath) as fh:
                    text = fh.read()

            found[kind] = None

            if kind == "model":
                result = A.getModel(text, modelMap)
                if result is None or result == "tei_all":
                    result = None
            else:
                result = None
                triggerRe = triggers[kind]
                if triggerRe is not None:
                    match = triggerRe.search(text)
                    result = match.group(1) if match else None

            if result is not None and result not in allOfKind:
                if verbose >= 0:
                    console(f"unavailable {kind} {result} in {ux(xmlPath)}")
                result = None
            found[kind] = result

        return (found["model"], found["adaptation"], found["template"])

    def getParser(self):
        """Configure the LXML parser.

        See [parser options](https://lxml.de/parsing.html#parser-options).

        Returns
        -------
        object
            A configured LXML parse object.
        """
        procins = self.procins

        return etree.XMLParser(
            remove_blank_text=False,
            collect_ids=False,
            remove_comments=True,
            remove_pis=not procins,
            huge_tree=True,
        )

    def parseXML(self, fileName, fileOrText, parser):
        """Parse an XML source.

        This is not meant to validate the XML, only to parse the XML into elements,
        attributes, and processing instructions, etc. Validity can be checked by means
        of `tff.tools.xmlschema.Analysis.validate` as is done in the check task.

        Parameters
        ----------
        fileName: indicator of the file name, does not have to be the full path,
            only used in error messages.
        fileOrText: string
            Either the full path of an XML file, or a string of raw XML text.
        parser: object
            A configured LXML parser object.

        Returns
        -------
        object | void
            The root of the resulting parse tree if the parsing succeeded, else None.
            If the parsing failed, a message is written to stderr.
        """
        try:
            tree = etree.parse(fileOrText, parser)
            result = tree.getroot()
        except Exception as e:
            console(f"{fileName}: {str(e)}", error=True)
            result = None

        return result

    def getXML(self):
        """Make an inventory of the TEI source files.

        Returns
        -------
        tuple of tuple | tuple of string | string
            If section model I is in force:

            The outer tuple has sorted entries corresponding to folders under the
            TEI input directory.
            Each such entry consists of the folder name and an inner tuple
            that contains the file names in that folder, sorted.

            If section model II is in force:

            It is the name of the single XML file.

            If section model III is in force:

            It is a tuple of multiple XML files
        """
        verbose = self.verbose
        sourceDir = self.sourceDir
        sectionModel = self.sectionModel

        if verbose == 1:
            console(f"Section model {sectionModel}")

        if sectionModel == "I":
            backMatter = self.backMatter

            IGNORE = "__ignore__"

            xmlFilesRaw = collections.defaultdict(list)

            with scanDir(sourceDir) as dh:
                for folder in dh:
                    folderName = folder.name

                    if folderName == IGNORE:
                        continue
                    if not folder.is_dir():
                        continue
                    with scanDir(f"{sourceDir}/{folderName}") as fh:
                        for file in fh:
                            fileName = file.name

                            if not (
                                fileName.lower().endswith(".xml") and file.is_file()
                            ):
                                continue
                            xmlFilesRaw[folderName].append(fileName)

            xmlFiles = []
            hasBackMatter = False

            for folderName in sorted(xmlFilesRaw, key=versionSort):
                if folderName == backMatter:
                    hasBackMatter = True
                else:
                    fileNames = xmlFilesRaw[folderName]
                    xmlFiles.append((folderName, tuple(sorted(fileNames))))

            if hasBackMatter:
                fileNames = xmlFilesRaw[backMatter]
                xmlFiles.append((backMatter, tuple(sorted(fileNames))))

            xmlFiles = tuple(xmlFiles)

            return xmlFiles

        if sectionModel == "II":
            xmlFile = None

            with scanDir(sourceDir) as fh:
                for file in fh:
                    fileName = file.name

                    if not (fileName.lower().endswith(".xml") and file.is_file()):
                        continue

                    xmlFile = fileName
                    break
            return xmlFile

        if sectionModel == "III":
            xmlFiles = []

            with scanDir(sourceDir) as fh:
                for file in fh:
                    fileName = file.name

                    if not (fileName.lower().endswith(".xml") and file.is_file()):
                        continue

                    xmlFiles.append(fileName)

            return tuple(sorted(xmlFiles))
