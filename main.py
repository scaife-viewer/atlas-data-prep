#!/usr/bin/env python

# from commentaries.scripts.convert_commentaries import convert_commentaries

# # if __name__ == "__main__":
# #     convert_commentaries()

from pathlib import Path
from lxml import etree
from lxml.sax import ElementTreeContentHandler, saxify

from commentaries.scripts.sax import SectionTransformBuilder


def convert_divs_and_milestones():
    p = "/Users/pletcher/code/PerseusDL/canonical_pdlrefwk/data/sec00009/sec005d/sec00009.sec005d.perseus-eng1.xml"
    tree = etree.parse(Path(p))

    handler = ElementTreeContentHandler()
    transformer = SectionTransformBuilder(handler)

    saxify(tree, transformer)

    with open(p, "wb") as fp:
        etree.indent(handler.etree, space="\t")
        fp.write(etree.tostring(handler.etree, encoding="utf-8", xml_declaration=True))


if __name__ == "__main__":
    convert_divs_and_milestones()
