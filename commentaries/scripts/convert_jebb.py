#!/usr/bin/env python
import json
import os

from pathlib import Path

from lxml import etree

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

        filename = [f for f in files if str(f).endswith("perseus-eng1.xml")][0]
        metadata_filename = [f for f in files if str(f).endswith("__cts__.xml")][0]

        self.metadata_tree = etree.parse(metadata_filename)
        self.tree = etree.parse(filename)
        self.urn = self.tree.find(".//tei:body", namespaces=NAMESPACES).get("n")
        self.glossae = self.collect_glossae(self.tree, self.urn)
        self.metadata = self.collect_metadata(self.metadata_tree, self.urn)

    def collect_glossae(self, tree: etree._ElementTree, urn: str):
        glosses = []

        idx = 0

        for commline in tree.iterfind(
            ".//tei:div[@subtype='commline']", namespaces=NAMESPACES
        ):
            n = commline.get("n")

            assert n is not None, f"No n for commline {commline}"

            for lemma in commline.iterfind(".//tei:s", namespaces=NAMESPACES):
                ana = lemma.get("ana").replace("#", "")
                parent = lemma.getparent()

                gloss = parent.iterfind(
                    f"./tei:gloss[@xml:id='{ana}']", namespaces=NAMESPACES
                )

                assert gloss, f"No gloss found for {ana}"

                split_citation = ana.split("_")

                citation_fragment = None

                if len(split_citation) == 4:
                    [citation_token_1, citation_token_2, _line_n, _line_n_idx] = (
                        split_citation
                    )
                elif len(split_citation) == 3:
                    [citation_token_1, citation_token_2, _line_n] = split_citation
                    citation_fragment = "-".join(
                        [f"{n}@{citation_token_1}", f"{n}@{citation_token_2}"]
                    )
                else:
                    [citation_token_1, _line_n] = split_citation
                    citation_fragment = f"{n}@{citation_token_1}"

                glosses.append(
                    {
                        "content": etree.tostring(
                            parent, with_tail=True, encoding="unicode", method="xml"
                        ),
                        "corresp": f"{urn}:{citation_fragment}",
                        "urn": f"{urn}.jebb:{idx}",
                    }
                )

                idx += 1

        return glosses

    def collect_metadata(self, tree: etree._ElementTree, urn: str):
        title = tree.find("./ti:title", namespaces=NAMESPACES).text

        return {
            "label": f"{title} by Sir R. C. Jebb",
            "urn": urn,
            "kind": "Commentary",
        }


def convert():
    for commentary_dir in COMMENTARY_DIRS:
        commentary = Commentary(commentary_dir)

        destination = Path(f"test-data/commentaries/{commentary.urn}")

        if not destination.is_dir():
            destination.mkdir(parents=True)

        with open(destination / "glossae_001.jsonl", "w") as f:
            for gloss in commentary.glossae:
                print(gloss)
                print(json.dumps(gloss, ensure_ascii=False), file=f)

        with open(destination / "metadata.json", "w") as f:
            metadata = commentary.metadata
            metadata["entries"] = "glossae_001.jsonl"

            json.dump(metadata, f, indent=2, ensure_ascii=False)
