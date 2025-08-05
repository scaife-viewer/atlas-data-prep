#!/usr/bin/env python

# ultimately, we want to use some machine learning model to intelligently
# decide how to resolve ambiguous references via some sort of ML
# hoover all abbreviated citations into a file with abbreviated form and resolved form
# do this for numeric citations as well
# also have a file mapping all refs to their resolutions

import logging
from typing import Optional, Union
import sys
import pathlib
import jsonlines
import re
from lxml import etree

from works_greek import (
    GREEK_AUTH_URNS,
    GREEK_WORK_URNS,
    GREEK_AUTH_ABB,
    GREEK_SINGLE_WORK_AUTHORS,
)
from works_latin import (
    LATIN_AUTH_URNS,
    LATIN_WORK_URNS,
    LATIN_AUTH_ABB,
    LATIN_SINGLE_WORK_AUTHORS,
)
from works_other import OTHER_AUTH_ABB, OTHER_WORK_URNS, OTHER_AUTH_URNS
from works_schol import SCHOL_AUTH_ABB, SCHOL_WORK_URNS, SCHOL_AUTH_URNS

# check for duplicate keys betwen greek and latin works
assert not set(GREEK_AUTH_URNS.keys()).intersection(LATIN_AUTH_URNS.keys())
assert not set(GREEK_WORK_URNS.keys()).intersection(LATIN_WORK_URNS.keys())
assert not set(GREEK_AUTH_ABB.keys()).intersection((LATIN_AUTH_ABB.keys()))

# check for duplicate keys betwen greek and other works
assert not set(GREEK_AUTH_URNS.keys()).intersection(OTHER_AUTH_URNS.keys())
assert not set(GREEK_WORK_URNS.keys()).intersection(OTHER_WORK_URNS.keys())
assert not set(GREEK_AUTH_ABB.keys()).intersection((OTHER_AUTH_ABB.keys()))

# check for duplicate keys betwen greek and schol works
assert not set(GREEK_AUTH_URNS.keys()).intersection(SCHOL_AUTH_URNS.keys())
assert not set(GREEK_WORK_URNS.keys()).intersection(SCHOL_WORK_URNS.keys())
assert not set(GREEK_AUTH_ABB.keys()).intersection((SCHOL_AUTH_ABB.keys()))

# check for duplicate keys betwen latin and other works
assert not set(LATIN_AUTH_URNS.keys()).intersection(OTHER_AUTH_URNS.keys())
assert not set(LATIN_WORK_URNS.keys()).intersection(OTHER_WORK_URNS.keys())
assert not set(LATIN_AUTH_ABB.keys()).intersection((OTHER_AUTH_ABB.keys()))

# check for duplicate keys betwen latin and schol works
assert not set(LATIN_AUTH_URNS.keys()).intersection(SCHOL_AUTH_URNS.keys())
assert not set(LATIN_WORK_URNS.keys()).intersection(SCHOL_WORK_URNS.keys())
assert not set(LATIN_AUTH_ABB.keys()).intersection((SCHOL_AUTH_ABB.keys()))

# check for duplicate keys betwen other and schol works
assert not set(OTHER_AUTH_URNS.keys()).intersection(SCHOL_AUTH_URNS.keys())
assert not set(OTHER_WORK_URNS.keys()).intersection(SCHOL_WORK_URNS.keys())
assert not set(OTHER_AUTH_ABB.keys()).intersection((SCHOL_AUTH_ABB.keys()))

AUTH_URNS = GREEK_AUTH_URNS | LATIN_AUTH_URNS | OTHER_AUTH_URNS | SCHOL_AUTH_URNS
AUTH_ABB = GREEK_AUTH_ABB | LATIN_AUTH_ABB | OTHER_AUTH_ABB | SCHOL_AUTH_ABB
WORK_URNS = GREEK_WORK_URNS | LATIN_WORK_URNS | OTHER_WORK_URNS | SCHOL_WORK_URNS
SINGLE_WORK_AUTHORS = GREEK_SINGLE_WORK_AUTHORS.union(LATIN_SINGLE_WORK_AUTHORS)

AUTHORS = set(AUTH_URNS.keys())

CITATION_OUT = pathlib.Path("./cit_data/resolved.jsonl")
CITATION_FAIL_OUT = pathlib.Path("./cit_data/unresolved.jsonl")

CITATION_OUT.parent.mkdir(parents=True, exist_ok=True)
CITATION_FAIL_OUT.parent.mkdir(parents=True, exist_ok=True)


logger = logging.getLogger(__name__)
file_handler = logging.FileHandler(filename="log_ref_to_urn.log")
stdout_handler = logging.StreamHandler(stream=sys.stdout)
handlers = [file_handler, stdout_handler]
logging.basicConfig(
    encoding="utf-8",
    level=logging.DEBUG,
    handlers=handlers,
)


def to_string(el):
    return re.sub(
        r"\s+",
        " ",
        etree.tostring(el, with_tail=True, encoding="unicode", method="text"),
    ).strip()


def to_xml(el):
    return re.sub(
        r"\s+",
        " ",
        etree.tostring(el, with_tail=True, encoding="unicode", method="xml"),
    ).strip()


def mk_cit_data(
    ref: Optional[str],
    from_n: Optional[str],
    from_bibl: Optional[str],
    urn: Optional[str],
    quote: Optional[str],
    xml_context: Union[str, etree._Element],
    filename: Union[str, pathlib.Path, None],
    cit_urn: Optional[str],
) -> None:
    """function to save citations as json files, one file for successful resolutions (citations.jsonl)
    and another for unsuccessful resolutions (citations_unr.jsonl). get_ref and get_urn both return None in case of
    failure to resolve urn, so mk_cit_data interprets ref = None as failure, ref != None as success.
    """
    if isinstance(xml_context, etree._Element):
        xml_context = to_xml(xml_context)
    if isinstance(filename, pathlib.Path):
        filename = str(filename)
    # deal with failure case
    if ref is None or urn is None:
        out = {
            "ref": ref,
            "n_attrib": from_n,
            "bibl": from_bibl,
            "urn": "",
            "quote": quote,
            "xml_context": xml_context,
            "filename": filename,
            "doc_cit_urn": cit_urn,
        }
        with jsonlines.open(CITATION_FAIL_OUT, "a") as f:
            f.write(out)
        return
    out = {
        "n_attrib": from_n,
        "bibl": from_bibl,
        "ref": ref,
        "urn": urn,
        "quote": quote,
        "xml_context": xml_context,
        "filename": filename,
        "doc_cit_urn": cit_urn,
    }
    with jsonlines.open(CITATION_OUT, "a") as f:
        f.write(out)
    return


def _smart_suspend(title: str, skip_de=True, join_char=".") -> str:
    func_words = {"the", "a", "an", "of", "in", "by", "for", "on", "and", "de", "ad"}
    vowels = {"a", "e", "i", "o", "u", "y"}
    plosives = {"t", "p", "d", "g", "k", "x", "c", "b"}
    suspensions = []
    title = title.replace(" ", "_")  # standardize spacing
    for word in title.split("_"):
        vowel_seen = False
        cons_last_seen = False
        if word in {"de", "on"}:
            if skip_de:
                continue
            suspensions.append(word)
            continue
        elif (
            word in func_words
        ):  # I don't think it's common to abbreviate nouns/adjective but keep these other function words
            continue
        buffer = []
        for char in word:
            if char in vowels:
                if vowel_seen and cons_last_seen:
                    break
                vowel_seen = True
                cons_last_seen = False
                buffer.append(char)
            else:
                if vowel_seen and char in plosives:
                    buffer.append(char)
                    break
                else:  # catches cases where char is consonant but not plosive, and where char is consonant at start of word
                    cons_last_seen = True
                    buffer.append(char)

        suspensions.append("".join(buffer))
    terminal = "." if join_char == "." else ""
    if suspensions[0] in {"de", "on"}:
        return suspensions[0] + "_" + join_char.join(suspensions[1:]) + terminal
    return join_char.join(suspensions) + terminal


def _transform_title(title: str, titles: list) -> list:
    prev_titles = set(titles)
    transformations = []

    if title.isnumeric():
        return []

    # latinize and anglicize one-word plural titles
    if len(title.split()) == 1:
        if title[-1] == "s":
            transformations.append(title[:-1] + "a")
        elif title[-1] == "a":
            transformations.append(title[:-1] + "s")

    initials = "".join([word[0] for word in title.split()])
    dot_initials = ".".join([word[0] for word in title.split()]) + "."
    under_initials = "_".join([word[0] for word in title.split()])
    dot_under_initials = "._".join([word[0] for word in title.split()]) + "."
    if initials not in prev_titles:
        transformations.append(initials)
    if dot_initials not in prev_titles:
        transformations.append(dot_initials)
    if under_initials not in prev_titles:
        transformations.append(under_initials)
    if dot_under_initials not in prev_titles:
        transformations.append(dot_under_initials)

    first_letter = title[0]
    if first_letter not in prev_titles:
        transformations.append(first_letter)
    if f"{first_letter}." not in prev_titles:
        transformations.append(f"{first_letter}.")
    first_two = title[:2]
    if first_two not in prev_titles:
        transformations.append(first_two)
    if f"{first_two}." not in prev_titles:
        transformations.append(f"{first_two}.")
    if len(title.split()[0]) > 2:
        first_three = title[:3]
        if first_three not in prev_titles:
            transformations.append(first_three)
        if f"{first_three}." not in prev_titles:
            transformations.append(f"{first_three}.")
    if len(title.split()[0]) > 3:
        first_four = title[:4]
        if first_four not in prev_titles:
            transformations.append(first_four)
        if f"{first_four}." not in prev_titles:
            transformations.append(f"{first_four}.")
    if len(title.split()[0]) > 4:
        first_five = title[:5]
        if first_five not in prev_titles:
            transformations.append(first_five)
        if f"{first_five}." not in prev_titles:
            transformations.append(f"{first_five}.")
    if len(title.split()[0]) > 5:
        first_six = title[:6]
        if first_six not in prev_titles:
            transformations.append(first_six)
        if f"{first_six}." not in prev_titles:
            transformations.append(f"{first_six}.")

    if len(title.split()) > 1:
        first_word = title.split()[0]
        if first_word not in prev_titles:
            transformations.append(first_word)

    # first two words for longer titles
    if len(title.split()) > 2:
        two_words = "_".join(title.split()[:2])
        if two_words not in prev_titles:
            transformations.append(two_words)

    # first three words for longer titles
    if len(title.split()) > 3:
        three_words = "_".join(title.split()[:3])
        if three_words not in prev_titles:
            transformations.append(three_words)

    # deal with function words
    func_words = {"the", "a", "an", "of", "in", "by", "for", "on", "and", "de", "ad"}
    if func_words & set(title.split()):
        initials = "".join(
            [word[0] for word in title.split() if word not in func_words]
        )
        dot_initials = (
            ".".join([word[0] for word in title.split() if word not in func_words])
            + "."
        )
        under_initials = "_".join(
            [word[0] for word in title.split() if word not in func_words]
        )
        dot_under_initials = (
            "._".join([word[0] for word in title.split() if word not in func_words])
            + "."
        )
        if initials not in prev_titles:
            transformations.append(initials)
        if dot_initials not in prev_titles:
            transformations.append(dot_initials)
        if under_initials not in prev_titles:
            transformations.append(under_initials)
        if dot_under_initials not in prev_titles:
            transformations.append(dot_under_initials)

    # add transformation of title by taking suspensions
    # by going until you have (CONS* VOWEL CONS+) VOWEL, e.g. part.an. for de partibus animalium
    # note that get_urn will replace spaces with underscores before checking for known work titles
    smart_suspension = _smart_suspend(title, skip_de=True)
    if smart_suspension not in prev_titles:
        transformations.append(smart_suspension)

    smart_suspension = _smart_suspend(title, skip_de=False)
    if smart_suspension not in prev_titles:
        transformations.append(smart_suspension)

    if len(title.split()) > 1:
        underscored = title.replace(" ", "_")
        if underscored not in prev_titles:
            transformations.append(underscored)

    return list(set(transformations))


additions = {}

for author in WORK_URNS.keys():
    for title in WORK_URNS[author].keys():
        prev_titles = list(additions.get(author, {}).keys()) + list(
            WORK_URNS[author].keys()
        )
        for transform in _transform_title(title, prev_titles):
            if not additions.get(author):
                additions[author] = {transform: WORK_URNS[author][title]}
            else:
                additions[author][transform] = WORK_URNS[author][title]

for author in additions.keys():
    for title in additions[author].keys():
        WORK_URNS[author][title] = additions[author][title]


def _detect_urn(ref) -> Optional[str]:
    match = re.search(r"tlg\d+\.tlg\d+(:\d+.?\d*)?(ff)?", ref)
    if match:
        return match.group(0)
    match = re.search(r"phi\d+\.phi\d+(:\d+.?\d*)?(ff)?", ref)
    if match:
        return match.group(0)
    match = re.search(r"stoa\d+\.stoa\d+(:\d+.?\d*)?(ff)?", ref)
    if match:
        return match.group(0)
    return


def _res_ordered_works(
    work_collection: tuple[str, int, int], ref: str, auth: str
) -> Optional[str]:
    # some keys in the dictionary of work urns amap to a function that returns the tuple
    # that can be passed as work_collection
    urn_stem, start, end = work_collection
    if len(auth) >= len(ref):
        logging.warning(f"Problem processing collection of works for {ref}.")
        return
    work_number = ref[len(auth) :].split()[1]
    work_number = work_number.split(".")[0]
    if not work_number.isnumeric():
        logging.warning(f"Problem processing collection of works for {ref}.")
        return
    work_number = int(work_number)
    urn_number = start - 1 + work_number
    if urn_number > end:
        logging.warning(f"Problem processing collection of works for {ref}.")
        return
    urn_number = str(urn_number).zfill(3)
    urn = f"{urn_stem}{urn_number}"
    return urn


def get_ref(
    from_n: Optional[str] = None, from_bibl: Optional[str] = None
) -> Optional[str]:
    """
    Takes in string contents of bibl element within cit element, as well as
    string contents of attribute "n" of bibl element,
    compares them, evaluates which better fits the desired citation format,
    cleans this string, and returns it. Returns None if no viable ref found.
    """
    if isinstance(from_n, str):
        from_n = from_n.lower().strip()
    if isinstance(from_bibl, str):
        from_bibl = from_bibl.lower().strip()

    # process in list form to apply same operations to both from_bibl and from_n
    refs = [from_n, from_bibl]
    refs = [
        re.sub("<title.*?>", "", ref) if isinstance(ref, str) else ref for ref in refs
    ]
    refs = [re.sub(r"[\(\)]", "", ref) if isinstance(ref, str) else ref for ref in refs]
    refs = [
        ref.replace("</title>", "") if isinstance(ref, str) else ref for ref in refs
    ]
    refs = [ref.replace(", ", " ") if isinstance(ref, str) else ref for ref in refs]
    # deal with section symbols
    refs = [re.sub(r" *§ *", ".", ref) if isinstance(ref, str) else ref for ref in refs]
    # deal with spacing issues with alphabetic page/section references (e.g. with Stephanus pages)
    refs = [
        re.sub(r"(\d+) ([A-Za-z])", r"\1\2", ref) if isinstance(ref, str) else ref
        for ref in refs
    ]
    from_n, from_bibl = refs

    # early return conditions
    if not isinstance(from_bibl, str) or not from_bibl.strip():
        assert isinstance(from_n, str)
        return from_n
    if not isinstance(from_n, str) or not from_n.strip():
        assert isinstance(from_bibl, str)
        return from_bibl
    if _detect_urn(from_n):
        return from_n

    # check if at least one string begins with the best case
    # where we have at least 2 alphabetic strings followed by two numeric strings
    # this can get refs of format Dion. Hal. Rom. ant. 2.2, with author and work as bigrams
    best_pattern = (
        r"([a-zA-Z]+\.?\s?[a-zA-Z]*) ([a-zA-Z]+\.?\s?[a-zA-Z]*) \d+(\s|\.|:)\d+"
    )
    # second_best has two strings followed by one numeric string
    second_best = r"([a-zA-Z]+\.?\s?[a-zA-Z]*) ([a-zA-Z]+\.?\s?[a-zA-Z]*) \d+"
    # third_best has one alphabetic string followed by two numeric strings,
    # and captures cases where the work is given by a numeral
    third_best = r"([a-zA-Z]+\.?) \d+(\s|\.|:)\d+"
    # This captures something like Bion 20, where Bion can be presumed to ref to
    # his main surviving work, the Lament for Adonis, and 20 to he line number
    fourth_best = r"([a-zA-Z]+\.?) \d+"

    patterns = (best_pattern, second_best, third_best, fourth_best)
    ref = None

    # the basic idea here is:
    # we take the best pattern, and if a given pattern matches from_n and from_n has
    # a recognized author, we from_n. If not, we do the same check on from_bibl, and if it
    # matches, we return from_bibl. We then do the same for the other patterns in order.
    # If no pattern matches, we instead simply try to identify an author in one of
    # from_n and from_bibl.

    for pattern in patterns:
        if re.search(pattern, from_n):
            split = from_n.split()
            # check that author is recognized, up to trigram
            if AUTH_ABB.get(split[0]) or split[0] in AUTHORS:
                ref = from_n
                break
            elif AUTH_ABB.get(" ".join(split[:2])) or " ".join(split[:2]) in AUTHORS:
                ref = from_n
                break
            elif AUTH_ABB.get(" ".join(split[:3])) or " ".join(split[:3]) in AUTHORS:
                ref = from_n
                break
        # at this point, we know that from_n either does not fit pattern, or has unrecognized author
        # so we do the same check on from_bibl
        if re.search(pattern, from_bibl):
            split = from_bibl.split()
            # check that author is recognized, up to trigram
            if AUTH_ABB.get(split[0]) or split[0] in AUTHORS:
                ref = from_bibl
                break
            elif AUTH_ABB.get(" ".join(split[:2])) or " ".join(split[:2]) in AUTHORS:
                ref = from_bibl
                break
            elif AUTH_ABB.get(" ".join(split[:3])) or " ".join(split[:3]) in AUTHORS:
                ref = from_bibl
                break

    # organized this way so more checks could easily be added
    if ref:
        return ref

    # at this point, none of the desired patterns have been recognized
    # check if either or both strings have a recognized author
    n_auth_rec = False
    bibl_auth_rec = False
    auth_form_from_n = ""  # so we can try to match work
    auth_form_from_bibl = ""

    split = from_n.split()
    if AUTH_ABB.get(split[0]) or split[0] in AUTHORS:
        n_auth_rec = True
        auth_form_from_n = split[0]
    elif AUTH_ABB.get(" ".join(split[:2])) or " ".join(split[:2]) in AUTHORS:
        n_auth_rec = True
        auth_form_from_n = " ".join(split[:2])
    elif AUTH_ABB.get(" ".join(split[:3])) or " ".join(split[:3]) in AUTHORS:
        n_auth_rec = True
        auth_form_from_n = " ".join(split[:3])

    split = from_bibl.split()
    if AUTH_ABB.get(split[0]) or split[0] in AUTHORS:
        bibl_auth_rec = True
        auth_form_from_bibl = split[0]
    elif AUTH_ABB.get(" ".join(split[:2])) or " ".join(split[:2]) in AUTHORS:
        bibl_auth_rec = True
        auth_form_from_bibl = " ".join(split[:2])
    elif AUTH_ABB.get(" ".join(split[:3])) or " ".join(split[:3]) in AUTHORS:
        bibl_auth_rec = True
        auth_form_from_bibl = " ".join(split[:3])

    if n_auth_rec and not bibl_auth_rec:
        return from_n
    if bibl_auth_rec and not n_auth_rec:
        return from_bibl

    # if both have a recognized author, determine which has a recognized work
    if n_auth_rec and bibl_auth_rec:
        if auth_form_from_n in AUTHORS:
            auth = auth_form_from_n
        else:
            auth = AUTH_ABB.get(auth_form_from_n, "")
        split = from_n[len(auth_form_from_n) :].split()
        auth_space = WORK_URNS.get(auth)
        if auth_space:
            # check for work up to trigram
            if len(split) > 0 and auth_space.get(split[0]):
                return from_n
            elif len(split) > 1 and auth_space.get(" ".join(split[:2])):
                return from_n
            elif len(split) > 2 and auth_space.get(" ".join(split[:3])):
                return from_n

        if auth_form_from_bibl in AUTHORS:
            auth = auth_form_from_bibl
        else:
            auth = AUTH_ABB.get(auth_form_from_bibl, "")
        split = from_bibl[len(auth_form_from_bibl) :].split()
        auth_space = WORK_URNS.get(auth)
        if auth_space:
            # check for work up to trigram
            if len(split) > 0 and auth_space.get(split[0]):
                return from_bibl
            elif len(split) > 1 and auth_space.get(" ".join(split[:2])):
                return from_bibl
            elif len(split) > 2 and auth_space.get(" ".join(split[:3])):
                return from_bibl

    warning_msg = (
        f"Problem where n attribute is\n{from_n}\nand bibl element is\n{from_bibl}\n"
    )
    if not isinstance(ref, str):
        logging.warning(warning_msg)
    # if this line is reached, no urn was recognized
    return


def get_urn(
    ref: Optional[str], content: Optional[str] = None, filename: Optional[str] = None
) -> Optional[str]:
    if not ref:
        return

    # for now, keep ff in references to line numbers,
    # but remove " " and "." to make it easier to process
    if ref[-2:] == "ff":
        if ref[-3] == " ":
            ref = ref[:-3] + ref[-2:]
    elif ref[-3:] == "ff.":
        if ref[-4] == " ":
            ref = ref[:-4] + "ff"
        else:
            ref = ref[:-3] + "ff"

    # detect if ref is already formatted as urn
    # note that this won't work if urn already has reference to edition, e.g. perseus-grc2
    urn_if_urn = _detect_urn(ref)
    if urn_if_urn:
        loc = ref[ref.index(urn_if_urn) + len(urn_if_urn) :]
        loc_match = re.search(r"\d+.*", loc)
        loc = loc_match.group(0) if loc_match else ""
        if "tlg" in urn_if_urn:
            if "urn:cts:greeklit" not in urn_if_urn:
                urn_if_urn = "urn:cts:greekLit:" + urn_if_urn
            urn = f"{urn_if_urn}.perseus-grc2:{loc}"
        elif "phi" in urn_if_urn:
            if "urn:cts:latinLit" not in urn_if_urn:
                urn_if_urn = "urn:cts:latinLit:" + urn_if_urn
            urn = f"{urn_if_urn}.perseus-lat2:{loc}"
        else:
            raise ValueError
        return urn

    # idea is that SINGLE_WORK_AUTHORS will only be used if the work cannot be identified by name
    as_one_book_auth = False
    split = ref.split()
    auth = split[0].lower()
    auth = AUTH_ABB.get(auth, auth)
    pos_after_auth = 1
    # deal with bigram author name, trigram, etc
    while auth not in AUTH_URNS.keys() and not callable(auth):
        pos_after_auth += 1
        # only try to match author name up to quadrigram
        if pos_after_auth == 5:
            break
        auth = " ".join(split[:pos_after_auth]).lower()
        auth = AUTH_ABB.get(auth, auth)

    # some auth strings are mapped to functions in AUTH_ABB
    if auth not in AUTH_URNS.keys() and not callable(auth):
        logging.warning(
            f"Author not recognized for {auth}\n\nThe xml context, if available, is: {content}.\n\nFilename, if available, is: {filename}"
        )
        return  # failure case

    # this deals with references to a work name for an author mainly known for one work
    while auth in SINGLE_WORK_AUTHORS:
        as_one_book_auth = True
        if auth not in WORK_URNS.keys():
            break
        if len(split) <= 1:
            break

        for i in range(1, len(split) - pos_after_auth):
            term = "_".join(split[pos_after_auth : pos_after_auth + i])
            if WORK_URNS[auth].get(term):
                as_one_book_auth = False
                break
        break
    # deal with authors known solely/primary from single work,
    # so that they are cited without ref to specific work
    # code above identifies whether the citation should be treated this way
    if as_one_book_auth:
        auth_urn = AUTH_URNS[auth]
        work = "tlg001"
        numerics = []
        term = ""
        for term in re.split(r"[\s,.:]", ref[pos_after_auth:]):
            if term.isnumeric():
                numerics.append(term)
        # deal with dashes in loc
        if re.search(r"\d+[–-—]{1}\d+", term):
            numerics.append(re.sub(r"(\d+)[–-—]{1}(\d+)", r"\1-\2", term))
        elif "ff" in term:
            numerics[-1] += "ff"
        loc = ".".join(numerics)
        urn = f"{auth_urn}.{work}.perseus-grc2:{loc}"
        return urn

    if callable(auth):
        # deal with cases where auth maps to function
        work_words = 0
        while not isinstance(auth, str):
            work_words += 1
            work_name = " ".join(
                ref.split()[pos_after_auth : pos_after_auth + work_words]
            )
            auth = auth(work_name)
            if work_words == 4:
                break
        if not isinstance(auth, str):
            logging.warning(
                f"author failed to resolve for ref: {ref}.\n\nXML context, if available, is: {content}\n\nFilename, if available, is: {filename}"
            )
            return

    # standardize form of author reference in ref
    ref = ref.replace(" ".join(ref.split()[:pos_after_auth]), auth)
    pos_after_auth = len(auth.split())
    # deal with work titles with spaces
    new_ref = ref
    for i, term in enumerate(ref.split()[pos_after_auth:]):
        if term[0].isnumeric():
            break
        if i > 0:
            term_index = new_ref.index(term)
            new_ref = new_ref[: term_index - 1] + "_" + new_ref[term_index:]

    ref = new_ref

    # this deals with the case where we have -> author work#.loc format
    if len(ref.split()) == pos_after_auth + 1:
        work_loc = ref.split()[pos_after_auth]
        if not len(work_loc.split(".", maxsplit=1)) == 2:
            logging.warning(
                f"wrong format for citation for ref: {ref}.\n\nXML context, if available, is: {content}\n\nFilename, if available, is: {filename}"
            )
            return  # failure case
        work, loc = work_loc.split(".", maxsplit=1)

    # now we need to define work and loc for the other cases,
    # primarily the case -> author work loc

    # there are various cases where the ref at this point has more than three words (or four if author is bigram)
    # one is where the title of the work has multiple words, which is addressed by checking
    # if the possible multiple word titles are known words and replacing replevant spaces with underscores
    if len(ref.split()) > pos_after_auth + 2:
        # iterate through work titles of two words and more
        if not WORK_URNS.get(auth):
            logging.warning(
                f"Author not recognized for {ref}.\nContents, if available: {content}.\nFilename, if available: {filename}."
            )
            return  # failure case
        for i in range(pos_after_auth + 1, len(ref.split())):
            if WORK_URNS[auth].get("_".join(ref.split()[pos_after_auth:i]).lower()):
                ref = ref.replace(
                    " ".join(ref.split()[1:i]), "_".join(ref.split()[1:i])
                )
                break

    # now, deal with cases where there are spaces between digits giving location in text
    # if there was somehow an author form with a number in it, it would have been replaced by a
    # nonnumeric form by this point
    while re.search(r"\d\.?\s\d", ref):
        ref = re.sub(r"(\d\.)\s(\d)", r"\1\2", ref)
        ref = re.sub(r"(\d)\s(\d)", r"\1\.\2", ref)

    # greatest possible ref length: author bigram + work + loc
    if len(ref.split()) not in (2, 3, 4):
        logging.warning(
            f"""
            wrong format for citation ref: {ref}\n
            citation content, if available, is: {content}\n
            filename, if available, is: {filename}
        """
        )
        return  # failure case

    if len(ref.split()) == pos_after_auth + 1:
        work_loc = ref.split()[pos_after_auth]
        if len(work_loc.split(".", maxsplit=1)) != 2:
            logging.warning(
                f"wrong format for citation ref: {ref}\n\nXML context, if available, is: {content}\n\nFilename, if available, is: {filename}"
            )
            return  # failure case
        work, loc = work_loc.split(".", maxsplit=1)
    else:
        if len(ref.split()[pos_after_auth:]) != 2:
            warning_msg = f"Formatting issues with ref: {ref}.\n\nXML context, if provided, is: {content}\n\nFilename, if provided, is: {filename}"
            logging.warning(warning_msg)
            return  # failure case
        work, loc = ref.split()[pos_after_auth:]

    work = work.lower()

    if auth not in AUTHORS:
        auth = AUTH_ABB.get(auth)
        if not auth:
            logging.warning(
                f"Author not recognized for: {ref}\ncitation content, if provided, is: {content}.\nFilename, if provided, is: {filename}."
            )
            return  # failure case

    auth_urn = AUTH_URNS[auth]

    work_urn = WORK_URNS[auth].get(work)

    # deal with case where auth is mapped to tuple, rather than urn
    if isinstance(work_urn, tuple):
        work_urn = _res_ordered_works(work_urn, ref, auth)
        numerics = []
        term = ""
        numeric_count = 0
        for term in re.split(r"[\s,.:]", ref[pos_after_auth:]):
            if term.isnumeric():
                if numeric_count == 0:
                    numeric_count += 1
                    continue  # skip numeric term that specifies which work in collection
                numerics.append(term)
        # deal with dashes in loc
        if re.search(r"\d+[–-—]{1}\d+", term):
            numerics.append(re.sub(r"(\d+)[–-—]{1}(\d+)", r"\1-\2", term))
        elif "ff" in term:
            numerics[-1] += "ff"
        loc = ".".join(numerics)
        urn = f"{auth_urn}.{work_urn}.perseus-grc2:{loc}"
        return urn

    if not work_urn and work.isnumeric():
        if "tlg" in auth_urn:
            prefix = "tlg"
        elif "phi" in auth_urn:
            prefix = "phi"
        else:
            prefix = ""

        if work[0] == "0":
            work_urn = f"{prefix}{work}"
        else:
            work_urn = f"{prefix}0{work}"

    # deal with cases like Isoc. Letter 7.7,
    # where "Letter 7" identifies the work urn
    elif not work_urn:
        if len(loc.split(".", maxsplit=1)) == 2:
            work_number, loc = loc.split(".", maxsplit=1)
            work = work + "_" + work_number
            work_urn = WORK_URNS[auth].get(work)
        # deal with cases where work is assumed to be author's primary work, hopefully tlg001
        else:
            work_urn = "tlg001"
            msg = f"""
            Warning: possible issues with the work name or the passage citation with {ref}. 
            Content, if provided, is {content}, filename {filename}.
            """
            logging.warning(msg)

    if not work_urn:
        logging.warning(f"Work not recognized for {ref}")
    # assert work_urn, f"Work not recognized for {ref}"

    if "greekLit" in auth_urn:
        urn = f"{auth_urn}.{work_urn}.perseus-grc2:{loc}"
    elif "latinLit" in auth_urn:
        urn = f"{auth_urn}.{work_urn}.perseus-lat2:{loc}"
    elif "englishLit" in auth_urn:
        urn = f"{auth_urn}.{work_urn}.perseus-eng2:{loc}"
    else:
        urn = f"{auth_urn}.{work_urn}:{loc}"
        logging.warning(
            f"""
        "warning: possible incorrectly formatted citation urn. 
        {urn}
        """
        )
    return urn


if __name__ == "__main__":
    # run module as script to output a text file with all
    # title forms and author abbreviations, both as specified explicitly
    # and as automatically generated
    with open("title_forms.txt", "w") as f:
        for auth in WORK_URNS.keys():
            f.write(f"___{auth}___\n")
            auth_abb_list = []
            for auth_form in AUTH_ABB.keys():
                # this assumes dictionary keys are in alphabetic order
                if auth_form[0] > auth[0]:
                    break
                if AUTH_ABB[auth_form] == auth:
                    auth_abb_list.append(auth_form)
            f.write(f"Author abbreviations: {','.join(auth_abb_list)}\n")
            f.write("Title forms:\n")
            for title_form in WORK_URNS[auth].keys():
                f.write(f"{title_form}\n")
