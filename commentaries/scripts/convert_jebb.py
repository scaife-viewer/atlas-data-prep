#!/usr/bin/env python

import json
import logging
import os
import re

from pathlib import Path

from lxml import etree

from .conversion_utils import to_xml
from .ref_to_urn import get_ref, get_urn

logging.basicConfig(level=logging.INFO)

SRC_DIR = Path(
    os.getenv("JEBB_COMMENTARIES_ROOT", "canonical_pdlrefwk/data/viaf2603144")
)
INTRO_DIRS = [d for d in SRC_DIR.iterdir() if str(d).endswith("i")]
COMMENTARY_DIRS = [
    d for d in SRC_DIR.iterdir() if not str(d).endswith("i") and d.is_dir()
]

NAMESPACES = {
    "tei": "http://www.tei-c.org/ns/1.0",
    "ti": "http://chs.harvard.edu/xmlns/cts",
    "xml": "http://www.w3.org/XML/1998/namespace",
}
XML_ID_ATTR = "{http://www.w3.org/XML/1998/namespace}id"


class Commentary:
    def __init__(self, dirname: Path):
        files = [f for f in dirname.iterdir()]

        self.filename = [f for f in files if str(f).endswith("perseus-eng1.xml")][0]
        metadata_filename = [f for f in files if str(f).endswith("__cts__.xml")][0]

        self.metadata_tree = etree.parse(metadata_filename)
        self.tree = etree.parse(self.filename)

        body = self.tree.find(".//tei:body", namespaces=NAMESPACES)

        assert body is not None, f"No body tag found for {self.filename}; aborting"

        self.urn: str = str(body.get("n"))
        self.metadata = self.collect_metadata(self.metadata_tree, self.urn)
        self.glossae = self.collect_glossae(self.tree, self.urn, self.filename)

    def collect_glossae(self, tree: etree._ElementTree, urn: str, filename: Path | str):
        citation_index = 0

        for commline in tree.iterfind(
            ".//tei:div[@subtype='commline']", namespaces=NAMESPACES
        ):
            n = commline.get("n")

            for lemma in commline.iterfind(".//tei:s", namespaces=NAMESPACES):
                lemma_text = etree.tostring(lemma, encoding="unicode", method="text").strip()
                ana = lemma.get("ana", "").replace("#", "")

                glossa_xpath = f".//tei:gloss[@xml:id='{ana}']"
                glossa = commline.find(glossa_xpath, namespaces=NAMESPACES)

                if glossa is not None:
                    citation_index += 1

                    citations = []

                    for cit in glossa.iterfind(".//tei:cit", namespaces=NAMESPACES):
                        quote = " ".join(cit.xpath("./tei:quote/text()", namespaces=NAMESPACES))  # type: ignore
                        bibl = cit.find("./tei:bibl", namespaces=NAMESPACES)
                        ref = ""

                        if bibl is not None:
                            bibl_n = bibl.get("n", "")
                            bibl_text = etree.tostring(
                                bibl, encoding="unicode", method="text"
                            )
                            ref = get_ref(bibl_n, bibl_text)

                        citation = {
                            "urn": f"{urn}:citations-{citation_index}.{len(citations) + 1}",
                            "data": {
                                "quote": quote,
                                "ref": ref,
                                "urn": get_urn(
                                    ref,
                                    content=to_xml(glossa),
                                    filename=str(self.filename),
                                ),
                            },
                        }

                        citations.append(citation)

                    split_ana = ana.split("_")

                    if len(split_ana) == 2:
                        corresp = f"{n}@{split_ana[0]}"
                    else:
                        corresp = f"{n}@{split_ana[0]}-{n}@{split_ana[1]}"

                    entry = {
                        "urn": f"{urn}:{citation_index}",
                        "corresp": f"{self.metadata['about']}:{corresp}",
                        "content": to_xml(glossa),
                        "citations": citations,
                        "lemma": lemma_text,
                    }

                    yield entry

    def collect_metadata(self, tree: etree._ElementTree, urn: str):
        title_el = tree.find(".//{*}title")

        assert title_el is not None, f"No title found for {urn}"

        about_el = tree.find(".//{*}about")

        assert about_el is not None, f"No ti:about tag found for {urn}"

        about = about_el.get("urn")

        assert about is not None, f"No @urn attribute found on ti:about tag for {urn}"

        title = title_el.text

        return {
            "label": f"{title} by Sir R. C. Jebb",
            "urn": urn,
            "kind": "Commentary",
            "about": about,
        }


def convert():
    for commentary_dir in COMMENTARY_DIRS:
        commentary = Commentary(commentary_dir)

        destination = Path(
            f"test-data/commentaries/{commentary.urn.replace('urn:cts:greekLit:', '')}"
        )

        if not destination.is_dir():
            destination.mkdir(parents=True)

        with open(destination / "glossae_001.jsonl", "w") as f:
            for gloss in commentary.glossae:
                print(json.dumps(gloss, ensure_ascii=False), file=f)

        with open(destination / "metadata.json", "w") as f:
            metadata = commentary.metadata
            metadata["entries"] = "glossae_001.jsonl"

            json.dump(metadata, f, indent=2, ensure_ascii=False)
