from xml.sax.handler import ContentHandler

from xml.sax.xmlreader import AttributesNSImpl


class SectionTransformBuilder(ContentHandler):
    """
    ContentHandler compatible with lxml.sax.saxify().

    Transforms two specific XML patterns before forwarding events to a target:

    1. <div subtype="section" n="p..."> is replaced by a self-closing
       <milestone unit="page_line" n="..."/>, and its matching </div> is dropped.

    2. <milestone unit="text-section" n="..."/> is replaced by a closing </div>
       followed by <div type="textpart" subtype="section" n="...">, and the
       milestone's own closing event is consumed.

    All other events are forwarded to `target` unchanged.  `target` is any
    xml.sax.ContentHandler.
    """

    def __init__(self, target):
        super().__init__()

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
            self._target.startElementNS((ns, "milestone"), "milestone", milestone_attrs)
            self._target.endElementNS((ns, "milestone"), "milestone")
            self._page_div_depth = 1
            return

        # Track nesting depth for any div opened while inside a page-line div
        if self._page_div_depth > 0 and local == "div":
            self._page_div_depth += 1

        # Case 2: text-section milestone → close current div, open new section div
        if local == "milestone" and attrs.get((None, "unit")) == "text-section":
            self._target.endElementNS((ns, "div"), "div")
            new_attrs = AttributesNSImpl(
                {
                    (None, "type"): "textpart",
                    (None, "subtype"): "section",
                    (None, "n"): attrs.get((None, "n"), ""),
                },
                {},
            )
            self._target.startElementNS((ns, "div"), "div", new_attrs)
            self._skip_text_section_end = True
            return

        self._target.startElementNS(name, qname, attrs)

    def endElementNS(self, name, qname):
        ns, local = name

        if local == "milestone" and self._skip_text_section_end:
            self._skip_text_section_end = False
            return

        if local == "div" and self._page_div_depth > 0:
            self._page_div_depth -= 1
            if self._page_div_depth == 0:
                return

        self._target.endElementNS(name, qname)

    # --- pass-through ContentHandler methods ---

    def startDocument(self):
        self._target.startDocument()

    def endDocument(self):
        self._target.endDocument()

    def startPrefixMapping(self, prefix, uri):
        self._target.startPrefixMapping(prefix, uri)

    def endPrefixMapping(self, prefix):
        self._target.endPrefixMapping(prefix)

    def characters(self, content):
        self._target.characters(content)

    def ignorableWhitespace(self, whitespace):
        self._target.ignorableWhitespace(whitespace)

    def processingInstruction(self, target, data):
        self._target.processingInstruction(target, data)

    def skippedEntity(self, name):
        self._target.skippedEntity(name)
