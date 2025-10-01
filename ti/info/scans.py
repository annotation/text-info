from subprocess import run

from ..kit.files import (
    dirContents,
    dirExists,
    dirRemove,
    dirMake,
    fileExists,
    extNm,
    fileRemove,
)
from ..kit.helpers import console, readCfg

from .iiif import FILE_NOT_FOUND


DS_STORE = ".DS_Store"
LOGO = "logo"
IDENTIFY_COMMAND = "/opt/homebrew/bin/identify"
ATTRIBUTE_OPTIONS = ["-ping", "-format", "%w %h %[colorspace]"]


class Scans:
    def __init__(self, sourceDir, cfgFile, verbose=0, force=False):
        """Detect sizes and colorspaces of scans

        Parameters
        ----------
        sourceDir: string
            Directory where the scans are.
        cfgFile: string
            Path to the configuration file.
        verbose: integer, optional 0
            Verbosity: 1 is minimal, 0 is normal, 1 is verbose
        force: boolean, optional False
            Whether to run when current results are up to date

        """
        self.sourceDir = sourceDir
        self.cfgFile = cfgFile
        self.verbose = verbose
        self.force = force

        if verbose == 1:
            console(f"Source dir = {sourceDir}")

        self.good = True

        (ok, settings) = readCfg(cfgFile, "scanprep", verbose=verbose, plain=False)
        if not ok:
            self.good = False
            return

        self.settings = settings

    def process(self, reportDir, verbose=None, force=None):
        """Extract info from scans.

        Parameters
        ----------
        reportDir: string
            Directory where the report files are written.
        verbose: integer, optional None
            Verbosity: 1 is minimal, 0 is normal, 1 is verbose
            If `None`, the value will be taken from the object
        force: boolean, optional None
            Whether to run when current results are up to date
            If `None`, the value will be taken from the object
        """
        if not self.good:
            return

        sourceDir = self.sourceDir
        settings = self.settings
        scanExt = settings.scanExt

        if verbose is None:
            verbose = self.verbose

        if force is None:
            force = self.force

        if force or not dirExists(reportDir):
            dirRemove(reportDir)
            dirMake(reportDir)

        if verbose == 1:
            console(f"Initialized {reportDir}")
        else:
            if verbose == 1:
                console(f"{reportDir} already present")

        (srcFiles, srcSubDirs) = dirContents(sourceDir)

        print(f"{srcSubDirs=}")

        for sbd in srcSubDirs:
            console(f"{sbd}:")

            if sbd == LOGO:
                continue
            else:
                srcDir = f"{sourceDir}/{sbd}"
                sizesFile = f"{reportDir}/sizes_{sbd}.tsv"
                colorspacesFile = f"{reportDir}/colorspaces_{sbd}.tsv"

                if (
                    force
                    or not fileExists(sizesFile)
                    or not fileExists(colorspacesFile)
                ):
                    self.doAttributes(sbd, srcDir, sizesFile, colorspacesFile)
                else:
                    if verbose == 1:
                        console(
                            f"\tAlready present: sizes and colorspaces files ({sbd})"
                        )

                notFound = f"{FILE_NOT_FOUND}.{scanExt}"
                files = [
                    f
                    for f in dirContents(srcDir)[0]
                    if f not in {DS_STORE, notFound} and extNm(f) == scanExt
                ]
                nFiles = len(files)
                console(f"\tscans: {nFiles}")

    def doAttributes(self, sbd, srcDir, sizesFile, colorspacesFile):
        if not self.good:
            return

        verbose = self.verbose
        settings = self.settings
        scanExt = settings.scanExt
        fileRemove(sizesFile)
        fileRemove(colorspacesFile)

        fileNames = dirContents(srcDir)[0]
        items = []

        for fileName in sorted(fileNames):
            if fileName == DS_STORE:
                continue

            thisExt = extNm(fileName)

            if thisExt != scanExt:
                continue

            base = fileName.removesuffix(f".{thisExt}")
            items.append((base, f"{srcDir}/{fileName}"))

        console(f"\t\tGet attributes of {len(items)} scans ({sbd})")

        j = 0
        nItems = len(items)

        sizes = []
        colorspaces = []

        for i, (base, fromFile) in enumerate(sorted(items)):
            if j == 100:
                perc = int(round(i * 100 / nItems))

                if verbose == 1:
                    console(f"\t\t\t{perc:>3}% done")

                j = 0

            status = run(
                [IDENTIFY_COMMAND] + ATTRIBUTE_OPTIONS + [fromFile], capture_output=True
            )
            j += 1

            if status.returncode != 0:
                console(f"\t{status.stderr.decode('utf-8')}", error=True)
            else:
                (w, h, colorspace) = (
                    status.stdout.decode("utf-8").strip().split(maxsplit=2)
                )
                sizes.append((base, w, h))
                colorspaces.append((base, colorspace))

        perc = 100

        if verbose == 1:
            console(f"\t\t\t{perc:>3}% done")

        with open(sizesFile, "w") as fh:
            fh.write("file\twidth\theight\n")

            for file, w, h in sizes:
                fh.write(f"{file}\t{w}\t{h}\n")

        with open(colorspacesFile, "w") as fh:
            fh.write("file\tcolorspace\n")

            for file, colorspace in colorspaces:
                fh.write(f"{file}\t{colorspace}\n")
