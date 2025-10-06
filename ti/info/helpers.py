from ..kit.helpers import console


FOLDER = "folder"
FILE = "file"
LINE = "line"
LN = "ln"
PAGE = "page"
PAGES = "pages"
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
