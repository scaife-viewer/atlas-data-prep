import json
import logging
import os
import re

from collections import Counter
from pathlib import Path

from lxml import etree

from convert_ot_cit import to_xml
from ref_to_urn import get_ref, get_urn

NAMESPACES = {
    "tei": "http://www.tei-c.org/ns/1.0",
    "xml": "http://www.w3.org/XML/1998/namespace",
}

logging.basicConfig(level=logging.INFO)

LOGGER = logging.getLogger(__name__)

BASE_URN = "urn:cts:greekLit:tlg0011.tlg004"


def convert(tree: etree._ElementTree, filename: str):
    commentary_urn = "urn:cts:greekLit:viaf2603144.viaf004.perseus-eng1"
    citation_index = 0

    for commline in tree.iterfind(
        ".//tei:div[@subtype='commline']", namespaces=NAMESPACES
    ):
        n = commline.get("n")

        for lemma in commline.iterfind(".//tei:s", namespaces=NAMESPACES):
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
                        "urn": f"{commentary_urn}:citations-{citation_index}.{len(citations) + 1}",
                        "data": {
                            "quote": quote,
                            "ref": ref,
                            "urn": get_urn(
                                ref, content=to_xml(glossa), filename=filename
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
                    "urn": f"{commentary_urn}:{citation_index}",
                    "corresp": corresp,
                    "content": to_xml(glossa),
                    "citations": citations,
                }

                yield entry


def main():
    TEST_DATA_DIR = os.getenv("TEST_DATA_DIR")

    assert TEST_DATA_DIR is not None

    filename = (
        Path(TEST_DATA_DIR)
        / "viaf2603144"
        / "viaf004"
        / "viaf2603144.viaf004.perseus-eng1.xml"
    )

    assert filename.is_file()

    tree = etree.parse(filename)

    with open(
        "./test-data/commentaries/viaf2603144.viaf004.perseus-eng1/glossae_001.jsonl",
        "w",
    ) as outfile:
        for entry in convert(tree, str(filename)):
            print(json.dumps(entry, ensure_ascii=False), file=outfile)


if __name__ == "__main__":
    main()
