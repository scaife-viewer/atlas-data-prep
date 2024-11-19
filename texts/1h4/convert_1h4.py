#!/usr/bin/env python3

import json
from pathlib import Path
import re

from lxml import etree

CANONICAL_ENGLIT = Path(__file__).parent.parent.parent.parent / Path("PerseusDL") /  Path("canonical-engLit")
namespaces = {"tei": "http://www.tei-c.org/ns/1.0"}


def tei(element_name):
    return f"{{{namespaces['tei']}}}{element_name}"


def text_content(el):
    return re.sub(r"\s+", " ", "".join(el.xpath(".//text()"))).strip()


class Converter:

    def convert_play(self, filename):
        # we have to do this because there are undeclared entities
        parser = etree.XMLParser(load_dtd=False, no_network=True, resolve_entities=False)

        root = etree.parse(filename, parser=parser).getroot()

        body = root.xpath("/tei:TEI/tei:text/tei:body", namespaces=namespaces)[0]
        for child in body:
            assert child.tag == tei("div"), child.tag
            assert child.attrib["type"] == "edition", child.attrib
            yield from self.handle_edition(child)


    def handle_edition(self, el):
        self.urn = el.attrib["n"]
        for child in el:
            assert child.attrib["type"] == "textpart", child.attrib
            assert child.attrib["subtype"] == "act", child.attrib
            if child.attrib["n"] == "cast":
                pass  # ignore cast list for now
            else:
                yield from self.handle_act(child)


    def handle_act(self, el):
        self.act_num = int(el.attrib["n"])
        self.scene_num = 0
        self.line_num = 0
        assert el[0].tag == tei("head")
        yield from self.handle_head(el[0])
        for child in el[1:]:
            if child.tag == tei("lb"):
                pass
            else:
                assert child.tag == tei("div"), child.tag
                assert child.attrib["type"] == "textpart", child.attrib
                assert child.attrib["subtype"] == "scene", child.attrib
                yield from self.handle_scene(child)


    def handle_scene(self, el):
        self.scene_num = int(el.attrib["n"])
        self.speech_num = 0
        self.who = None
        self.line_num = 0
        assert el[0].tag == tei("head")
        self.handle_head(el[0])
        for child in el[1:]:
            if child.tag == tei("lb"):
                pass
            elif child.tag == tei("stage"):
                yield from self.handle_stage(child)
            else:
                assert child.tag == tei("sp"), child.tag
                yield from self.handle_speech(child)


    def handle_head(self, el):
        assert el.attrib == {}
        ref = self.get_ref()
        yield ref, {"kind": "head"}, text_content(el)


    def handle_speech(self, el):
        assert el[0].tag == tei("speaker")
        self.who = el.attrib["who"]
        self.speech_num += 1
        for child in el[1:]:
            if child.tag == tei("lb"):
                pass
            elif child.tag == tei("stage"):
                yield from self.handle_stage(child, in_speech=True)
            elif child.tag == tei("p"):
                yield from self.handle_prose(child)
            else:
                assert child.tag == tei("l"), child.tag
                yield from self.handle_line(child)
        self.who = None


    def get_ref(self):
        return f"{self.act_num}.{self.scene_num}.{self.line_num}"


    def handle_stage(self, el, in_speech=False):
        assert el.attrib.get("type") in ["setting", "entrance", "exit", None], f"bad stage direction: {el.text}"
        annotations = {"kind": "stage"}
        if self.who:
            annotations["who"] = self.who
        if el.attrib.get("type"):
            annotations["type"] = el.attrib["type"]
        if in_speech:
            annotations["sp"] = self.speech_num
        self.line_num += 1
        ref = self.get_ref()
        yield ref, annotations, text_content(el)


    def handle_prose(self, el):
        annotations = {"kind": "prose"}
        annotations["sp"] = self.speech_num
        if self.who:
            annotations["who"] = self.who
        if el.attrib.get("part"):
            annotations["part"] = el.attrib["part"]
        self.line_num += 1
        ref = self.get_ref()
        yield ref, annotations, text_content(el)


    def handle_line(self, el):
        annotations = {"kind": "line"}
        annotations["sp"] = self.speech_num
        if self.who:
            annotations["who"] = self.who
        if el.attrib.get("part"):
            annotations["part"] = el.attrib["part"]
        self.line_num += 1
        ref = self.get_ref()
        yield ref, annotations, text_content(el)


if __name__ == "__main__":
    c = Converter()
    filename = CANONICAL_ENGLIT / "data/shakespeare/1h4.xml"
    with open("1h4-text.tsv", "w") as text_fd, open("1h4-anno.jsonl", "w") as anno_fd:
        for ref, annotations, content in c.convert_play(filename):
            print(ref, content, sep="\t", file=text_fd)
            annotations["ref"] = ref
            print(json.dumps(annotations), file=anno_fd)
