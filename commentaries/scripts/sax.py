import xml.sax
import xml.sax.handler

from xml.sax.xmlreader import AttributesNSImpl


class SAXBuilder:
    """Base class for namespace-aware SAX event handlers (snake_case interface)."""

    def start_document(self):
        pass

    def end_document(self):
        pass

    def start_prefix_mapping(self, prefix: str, uri: str):
        pass

    def end_prefix_mapping(self, prefix: str):
        pass

    def start_element_ns(self, name: tuple, qname: str, attrs):
        pass

    def end_element_ns(self, name: tuple, qname: str):
        pass

    def characters(self, content: str):
        pass

    def ignorable_whitespace(self, whitespace: str):
        pass

    def processing_instruction(self, target: str, data: str):
        pass

    def skipped_entity(self, name: str):
        pass


class ContentHandlerAdapter(SAXBuilder):
    """Adapts any xml.sax.ContentHandler (e.g. lxml.sax.ElementTreeContentHandler)
    to the SAXBuilder snake_case NS interface."""

    def __init__(self, handler: xml.sax.ContentHandler):
        self._handler = handler

    def start_document(self):
        self._handler.startDocument()

    def end_document(self):
        self._handler.endDocument()

    def start_prefix_mapping(self, prefix: str, uri: str):
        self._handler.startPrefixMapping(prefix, uri)

    def end_prefix_mapping(self, prefix: str):
        self._handler.endPrefixMapping(prefix)

    def start_element_ns(self, name: tuple, qname: str, attrs):
        self._handler.startElementNS(name, qname, attrs)

    def end_element_ns(self, name: tuple, qname: str):
        self._handler.endElementNS(name, qname)

    def characters(self, content: str):
        self._handler.characters(content)

    def ignorable_whitespace(self, whitespace: str):
        self._handler.ignorableWhitespace(whitespace)

    def processing_instruction(self, target: str, data: str):
        self._handler.processingInstruction(target, data)

    def skipped_entity(self, name: str):
        self._handler.skippedEntity(name)


class SectionTransformBuilder(xml.sax.handler.ContentHandler):
    """
    ContentHandler compatible with lxml.sax.saxify().

    Transforms two specific XML patterns before forwarding events to a target:

    1. <div subtype="section" n="p..."> is replaced by a self-closing
       <milestone unit="page_line" n="..."/>, and its matching </div> is dropped.

    2. <milestone unit="text-section" n="..."/> is replaced by a closing </div>
       followed by <div type="textpart" subtype="section" n="...">, and the
       milestone's own closing event is consumed.

    All other events are forwarded to `target` unchanged.  `target` may be a
    SAXBuilder or any xml.sax.ContentHandler (which will be wrapped automatically).
    """

    def __init__(self, target):
        super().__init__()
        if not isinstance(target, SAXBuilder):
            target = ContentHandlerAdapter(target)
        self._target = target
        # >0 while inside a transformed page-line div; tracks nesting so only
        # the outermost closing </div> is dropped.
        self._page_div_depth = 0
        # True while waiting to swallow the endElementNS for a consumed text-section milestone.
        self._skip_text_section_end = False

    # --- transforming ContentHandler methods ---

    def startElementNS(self, name, qname, attrs):
        ns, local = name

        # Case 1: page-line div → self-closing milestone
        if (
            local == "div"
            and attrs.get((None, "subtype")) == "section"
            and attrs.get((None, "n"), "").startswith("p")
            and self._page_div_depth == 0
        ):
            n = attrs.get((None, "n"))
            milestone_attrs = AttributesNSImpl({(None, "unit"): "page_line", (None, "n"): n}, {})
            self._target.start_element_ns((ns, "milestone"), "milestone", milestone_attrs)
            self._target.end_element_ns((ns, "milestone"), "milestone")
            self._page_div_depth = 1
            return

        # Track nesting depth for any div opened while inside a page-line div
        if self._page_div_depth > 0 and local == "div":
            self._page_div_depth += 1

        # Case 2: text-section milestone → close current div, open new section div
        if local == "milestone" and attrs.get((None, "unit")) == "text-section":
            self._target.end_element_ns((ns, "div"), "div")
            new_attrs = AttributesNSImpl(
                {
                    (None, "type"): "textpart",
                    (None, "subtype"): "section",
                    (None, "n"): attrs.get((None, "n"), ""),
                },
                {},
            )
            self._target.start_element_ns((ns, "div"), "div", new_attrs)
            self._skip_text_section_end = True
            return

        self._target.start_element_ns(name, qname, attrs)

    def endElementNS(self, name, qname):
        ns, local = name

        if local == "milestone" and self._skip_text_section_end:
            self._skip_text_section_end = False
            return

        if local == "div" and self._page_div_depth > 0:
            self._page_div_depth -= 1
            if self._page_div_depth == 0:
                return

        self._target.end_element_ns(name, qname)

    # --- pass-through ContentHandler methods ---

    def startDocument(self):
        self._target.start_document()

    def endDocument(self):
        self._target.end_document()

    def startPrefixMapping(self, prefix, uri):
        self._target.start_prefix_mapping(prefix, uri)

    def endPrefixMapping(self, prefix):
        self._target.end_prefix_mapping(prefix)

    def characters(self, content):
        self._target.characters(content)

    def ignorableWhitespace(self, whitespace):
        self._target.ignorable_whitespace(whitespace)

    def processingInstruction(self, target, data):
        self._target.processing_instruction(target, data)

    def skippedEntity(self, name):
        self._target.skipped_entity(name)
