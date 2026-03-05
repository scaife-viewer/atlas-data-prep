def to_xml(el):
    return re.sub(
        r"\s+",
        " ",
        etree.tostring(el, with_tail=True, encoding="unicode", method="xml"),
    ).strip()
