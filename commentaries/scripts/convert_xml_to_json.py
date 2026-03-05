import json
import logging
import os
import re

from pathlib import Path

from lxml import etree

from .conversion_utils import to_xml
from .ref_to_urn import get_ref, get_urn

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


NAMESPACES = {
    "tei": "http://www.tei-c.org/ns/1.0",
    "ti": "http://chs.harvard.edu/xmlns/cts",
    "xml": "http://www.w3.org/XML/1998/namespace",
}
XML_ID_ATTR = "{http://www.w3.org/XML/1998/namespace}id"


def convert_xml_to_json(source_dir: Path, destination_dir: Path):
    commentary_dirs = [
        d for d in source_dir.iterdir() if not str(d).endswith("i") and d.is_dir()
    ]
    files = [f for d in commentary_dirs for f in d.iterdir()]

    tei_files = [f for f in files if str(f).endswith("perseus-eng1.xml")]
    metadata_files = [f for f in files if str(f).endswith("__cts__.xml")]

    tei_metadata_pairs = zip(tei_files, metadata_files)

    for tei_file, metadata_file in tei_metadata_pairs:
        destination = destination_dir / tei_file.stem

        write_json_output(destination, tei_file, metadata_file)


def write_json_output(destination_filename: Path, tei_file: Path, metadata_file: Path):
    textgroup_metadata_tree = etree.parse(metadata_file.parent / "__cts__.xml")

    textgroup_name = textgroup_metadata_tree.find(".//*:groupname").text

    metadata_tree = etree.parse(metadata_file)
    tei_tree = etree.parse(tei_file)
    body = tei_tree.find(".//tei:body", namespaces=NAMESPACES)

    assert body is not None, f"No body tag found for {tei_file}; aborting"

    refs_decl = tei_tree.find(".//tei:refsDecl", namespaces=NAMESPACES)

    assert refs_decl is not None, f"No refsDecl tag found for {tei_file}; aborting"

    subtype_el = refs_decl.find(".//tei:cRefPattern", namespaces=NAMESPACES)

    subtype = subtype_el.get("n")

    urn = str(body.get("n"))
    metadata = collect_metadata(metadata_tree, urn, textgroup_name)
    glossae = collect_glossae(tei_tree, urn, tei_file, subtype)

    if len(glossae) == 0:
        logger.info(f"No glossae found in {tei_file}")
        return None

    if not destination.is_dir():
        destination.mkdir(parents=True)

    with open(destination / "glossae_001.jsonl", "w") as f:
        for gloss in glossae:
            print(json.dumps(gloss, ensure_ascii=False), file=f)

    with open(destination / "metadata.json", "w") as f:
        metadata = metadata
        metadata["entries"] = "glossae_001.jsonl"

        json.dump(metadata, f, indent=2, ensure_ascii=False)


def collect_glossae(
    tree: etree.ElementTree,
    urn: str,
    filename: Path,
    subtype: str,
    metadata: dict,
):
    citation_index = 0

    for textpart in tree.iterfind(
        f".//tei:div[@subtype='{subtype}']", namespaces=NAMESPACES
    ):
        n = textpart.get("n")

        for lemma in textpart.iterfind(".//tei:s", namespaces=NAMESPACES):
            lemma_text = etree.tostring(
                lemma, encoding="unicode", method="text"
            ).strip()
            ana = lemma.get("ana", "").replace("#", "")

            glossa_xpath = f".//tei:gloss[@xml:id='{ana}']"
            glossa = textpart.find(glossa_xpath, namespaces=NAMESPACES)

            if glossa is not None:
                citation_index += 1

                citations = gather_citations(glossa, citation_index, filename)

                split_ana = ana.split("_")

                corresp = get_corresp(textpart, lemma, metadata)

                entry = {
                    "urn": f"{urn}:{citation_index}",
                    "corresp": corresp,
                    "content": to_xml(glossa),
                    "citations": citations,
                    "lemma": lemma_text,
                }

                yield entry


def gather_citations(glossa, citation, filename):
    citations = []

    for cit in glossa.iterfind(".//tei:cit", namespaces=NAMESPACES):
        quote = " ".join(cit.xpath("./tei:quote/text()", namespaces=NAMESPACES))  # type: ignore
        bibl = cit.find("./tei:bibl", namespaces=NAMESPACES)
        ref = ""

        if bibl is not None:
            bibl_n = bibl.get("n", "")
            bibl_text = etree.tostring(bibl, encoding="unicode", method="text")
            ref = get_ref(bibl_n, bibl_text)

        citation = {
            "urn": f"{urn}:citations-{citation_index}.{len(citations) + 1}",
            "data": {
                "quote": quote,
                "ref": ref,
                "urn": get_urn(
                    ref,
                    content=to_xml(glossa),
                    filename=str(filename),
                ),
            },
        }

        citations.append(citation)

    return citations


def collect_metadata(tree: etree.ElementTree, urn: str, textgroup_name: str):
    title_el = tree.find(".//{*}title")

    assert title_el is not None, f"No title found for {urn}"

    about_el = tree.find(".//{*}about")

    assert about_el is not None, f"No ti:about tag found for {urn}"

    about = about_el.get("urn")

    assert about is not None, f"No @urn attribute found on ti:about tag for {urn}"

    title = title_el.text

    return {
        "label": f"{title} by {textgroup_name}",
        "urn": urn,
        "kind": "Commentary",
        "about": about,
    }


def get_corresp(textpart: etree.ElementTree, lemma: etree.ElementTree, metadata):
    textpart_corresp = textpart.get("corresp")

    if textpart_corresp is not None:
        if textpart_corresp.startswith("urn:"):
            return textpart_corresp

    textpart_subtype = textpart.get("subtype")

    if subtype == "commline":
        n = textpart.get("n")

        if n is not None and n.lower() == "introduction":
            parent_section = textpart.getparent()
            parrent_corresp = parent_section.get("corresp")

            return parrent_corresp
        else:
            return f"{metadata['about']}:{n}"

    if subtype == "subsection":
        parent_section = textpart.getparent()
        parrent_corresp = parent_section.get("corresp")

        return parrent_corresp

    ana = lemma.get("ana", "").replace("#", "")
    if len(split_ana) == 2:
        corresp = f"{n}@{split_ana[0]}"
    else:
        corresp = f"{n}@{split_ana[0]}-{n}@{split_ana[1]}"

    return corresp
