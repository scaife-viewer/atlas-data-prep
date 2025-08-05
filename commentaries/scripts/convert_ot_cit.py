#!/usr/bin/env python


import json
import re
import pathlib
from typing import Optional

from lxml import etree

from ref_to_urn import get_urn, get_ref, mk_cit_data, CITATION_FAIL_OUT, CITATION_OUT


def TEI(tag):
    return f"{{http://www.tei-c.org/ns/1.0}}{tag}"


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


def get_glossae(src_file, text_urn):
    tree = etree.parse(src_file)
    root = tree.getroot()

    commentary_div = root[1][0][0]
    assert commentary_div.tag == TEI("div")
    assert commentary_div.attrib["type"] == "commentary"
    # urn = commentary_div.attrib["n"]

    for child in commentary_div:
        if child.tag == TEI("p"):
            continue  # for now
        assert child.tag == TEI("div"), child.tag
        assert child.attrib["type"] == "textpart"
        # assert child.attrib["subtype"] == "section"
        corresp = child.attrib.get("corresp")
        if not corresp:
            continue

        for gchild in child:
            if gchild.tag == TEI("head"):
                continue
            elif gchild.tag == TEI("p"):
                for ggchild in gchild:
                    assert ggchild.tag in [
                        TEI("foreign"),
                        TEI("emph"),
                        TEI("title"),
                        TEI("bibl"),
                        TEI("ref"),
                        TEI("cit"),
                        TEI("quote"),
                        TEI("app"),
                    ], ggchild.tag
                yield (corresp, to_xml(gchild))
            else:
                assert gchild.tag == TEI("div"), gchild.tag
                assert gchild.attrib["type"] == "textpart"
                if gchild.attrib["subtype"] != "commline":
                    continue  # for now
                if gchild.attrib.get("corresp"):
                    corresp2 = gchild.attrib["corresp"]
                else:
                    corresp2 = text_urn + str(gchild.attrib["n"])
                for ggchild in gchild:
                    if ggchild.tag == TEI("head"):
                        continue
                    # assert ggchild.tag == TEI("p"), ggchilt.tag
                    for gggchild in ggchild:
                        if isinstance(gggchild, etree._Comment):
                            continue
                        assert gggchild.tag in [
                            TEI("app"),
                            TEI("foreign"),
                            TEI("cit"),
                            TEI("emph"),
                            TEI("bibl"),
                            TEI("title"),
                            TEI("date"),
                            TEI("quote"),
                            TEI("ref"),
                        ], gggchild.tag
                yield (corresp2, to_xml(gchild))


# Take the xml of a <p> element yielded by get_glossae and extract the citations
# from <cit> elements in the format
# [{"urn": "urn:cite2:scaife-viewer:citations.atlas_v1:lsj-445456",
# "data": {"quote": "", "ref": "Od. 1.85 (written", "urn": "urn:cts:greekLit:tlg0012.tlg002.perseus-grc2:1.85"}}]
def extract_citations(
    p_xml: str, idx: int, counter: dict, urn_prefix, filename: Optional[str] = None
) -> list:
    # quick experimentation suggests extracting information from a single <cit> element is faster
    # using regex parsing than lxml.etree parsing
    matches = re.finditer(r"<cit.+?/cit>", p_xml)
    citations = []
    for match in matches:
        cit_urn = f"{urn_prefix}:citations-{idx}.{counter['count']}"
        counter["count"] += 1
        quote = re.search(r"<quote.*?>(.+)</quote>", match.group())
        assert (
            quote
        ), f"Issue extracting quote from {p_xml}\n\nin citation {match.group()}"
        quote = quote.group(1)
        # TODO: sometimes contents of bibl element is in format "v. #"
        # we can't consistently prefer the n attribute or the bibl element, have to
        # check which one better matches the desired pattern
        from_n = re.search(r"<bibl.+?n=\"(.+?)\".*>", match.group())
        from_bibl = re.search(r"<bibl.*?>(.+)</bibl>", match.group())
        # pull from n attribute if bibl element is in the form "v. #" or if bibl element does not contain ref
        if from_n:
            from_n = from_n.group(1)
        if from_bibl:
            from_bibl = from_bibl.group(1)
        ref = get_ref(from_n, from_bibl)
        # assert ref, f"Issue extracting ref from {p_xml}\n\nin citation {match.group()}"
        # sometimes, the n attribute includes important information like author name,
        # that the bibl element lacks
        target_urn = get_urn(ref, content=p_xml, filename=filename)
        citation = {
            "urn": cit_urn,
            "data": {
                "quote": quote,
                "ref": ref,
                "urn": target_urn,
            },
        }
        citations.append(citation)
        # save citation data as separate jsonl files in ./cit_data
        mk_cit_data(ref, from_n, from_bibl, target_urn, quote, p_xml, filename, cit_urn)
    return citations


if __name__ == "__main__":
    SRC_FILE = pathlib.Path(
        "../../../canonical_pdlrefwk/data/viaf2603144/viaf001/viaf2603144.viaf001.perseus-eng1.xml"
    )
    TEXT_URN = "urn:cts:greekLit:tlg0011.tlg004:"  # note trailing colon
    DESTO_DIR = pathlib.Path("../../test-data/commentaries/jebb-ot")
    URN_PREFIX = "urn:cts:greekLit:viaf2603144.viaf001.perseus-eng1"

    CITATION_FAIL_OUT.unlink(missing_ok=True)
    CITATION_OUT.unlink(missing_ok=True)

    with open(DESTO_DIR / "glossae_001.jsonl", "w") as f:
        idx = 0
        cit_counter = {"count": 0}
        for corresp, content in get_glossae(SRC_FILE, TEXT_URN):
            idx += 1
            entry = {
                "urn": f"{URN_PREFIX}:{idx}",
                "corresp": corresp,
                "content": content,
                "citations": extract_citations(
                    content, idx, cit_counter, URN_PREFIX, filename=str(SRC_FILE)
                ),
            }
            print(json.dumps(entry, ensure_ascii=False), file=f)

    metadata = {
        "label": "Commentary on Sophocles: Oedipus Tyrannus by Sir Richard C. Jebb",
        "urn": URN_PREFIX,
        "kind": "Commentary",
        "entries": ["glossae_001.jsonl"],
    }

    with open(DESTO_DIR / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
