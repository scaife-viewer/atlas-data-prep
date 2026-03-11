import json
import os

from dataclasses import asdict, dataclass
from pathlib import Path

from lxml import etree

DIR = Path(os.getenv("PDLREFWK_ROOT")).resolve() / "data" / "sec00009"
NAMESPACES = {
    "tei": "http://www.tei-c.org/ns/1.0",
    "ti": "http://chs.harvard.edu/xmlns/cts",
    "xml": "http://www.w3.org/XML/1998/namespace",
}
SUBDIRS = [d for d in DIR.iterdir() if d.is_dir()]


@dataclass
class Citation:
    urn: str
    quote: str
    ref: str
    ref_urn: str


@dataclass
class Gloss:
    """
    This class holds information for each gloss,
    and provides a convenient method for converting
    to JSON.

    @urn: The CTS URN in the commentary
    @corresp: The CTS URN in the base text
    @content: The content of the <gloss> XML tag
    @citations: A list of loci paralleli cited in the gloss
    @lemma: The bare lemma of @corresp citation
    """

    urn: str
    corresp: str
    content: str
    citations: list[Citation]
    lemma: str


def read_file(path: Path) -> etree.ElementTree:
    return etree.parse(path)


def collect_glosses(tei_file: Path, work_urn_fragment: str, commentary_base_urn: str):
    tree = read_file(tei_file)

    glosses: list[Gloss] = []

    for textpart in tree.iterfind(
        ".//tei:div[@subtype='section']", namespaces=NAMESPACES
    ):
        for s_el in textpart.iterfind(".//tei:s", namespaces=NAMESPACES):
            lemma = etree.tostring(s_el, method="text", encoding="unicode").strip()
            ana = s_el.get("ana")
            xpath = f".//tei:gloss[@xml:id='{ana.replace("#", "")}']"
            gloss = textpart.find(xpath, namespaces=NAMESPACES)

            assert gloss is not None, f"No gloss found for {ana} in {work_urn_fragment}"

            phi0474_urn = None
            textpart_corresp = textpart.get("corresp")

            if textpart_corresp is not None:
                if textpart_corresp.startswith(work_urn_fragment):
                    phi0474_urn = textpart_corresp
                else:
                    # print(
                    #     f"Incomplete @corresp attribute on {etree.tostring(textpart)}."
                    # )

                    # maybe_corresp = f"{work_urn_fragment}:{textpart_corresp}"

                    # print(f"Does this look correct? {maybe_corresp}")
                    # user_response = input(
                    #     "Type 'y' to accept; otherwise, enter the URN manually.\n\n"
                    # )

                    # if user_response.lower() == "y":
                    #     phi0474_urn = maybe_corresp
                    # else:
                    #     phi0474_urn = user_response
                    textpart_n = textpart.get("n")
                    if len(work_urn_fragment.split(":")) > 4:
                        phi0474_urn = f"{work_urn_fragment}.{textpart_n}"
                    else:
                        phi0474_urn = f"{work_urn_fragment}:{textpart_n}"
            else:
                textpart_n = textpart.get("n")

                if len(work_urn_fragment.split(":")) > 4:
                    phi0474_urn = f"{work_urn_fragment}.{textpart_n}"
                else:
                    phi0474_urn = f"{work_urn_fragment}:{textpart_n}"

            glosses.append(
                Gloss(
                    urn=f"{commentary_base_urn}:{len(glosses) + 1}",
                    corresp=phi0474_urn,
                    content=etree.tostring(
                        gloss, xml_declaration=False, encoding="unicode"
                    ),
                    citations=[],
                    lemma=lemma,
                )
            )

    return glosses


def get_metadata(cts_file: Path):
    tree = read_file(cts_file)

    title_el = tree.find(".//ti:title", namespaces=NAMESPACES)

    assert title_el is not None, f"No title found for {urn}"

    about_el = tree.find(".//ti:about", namespaces=NAMESPACES)

    assert about_el is not None, f"No ti:about tag found for {urn}"

    about = about_el.get("urn")

    assert about is not None, f"No @urn attribute found on ti:about tag for {urn}"

    title = title_el.text

    return {
        "label": title,
        "kind": "Commentary",
        "about": about,
    }


APPROVED_WORK_FRAGMENTS = [
    "sec002",
    "sec003a",
    "sec003b",
    "sec003c",
    "sec004",
    "sec005a",
    "sec005b",
    "sec005c",
    "sec005d",
]

OUT_ROOT = Path(__file__).resolve().parent.parent.parent / "test-data" / "commentaries"


def process_sec00009():
    for d in SUBDIRS:
        # sec001 is the introduction, which we
        # don't need to align
        if d.name not in APPROVED_WORK_FRAGMENTS:
            print(f"Please check if {d.name} is ready for processing.")
            continue
        cts_file = d / "__cts__.xml"
        tei_file = d / f"sec00009.{d.name}.perseus-eng1.xml"

        metadata = get_metadata(cts_file)
        commentary_urn = f"urn:cts:latinLit:sec00009.{d.name}.perseus-eng1"

        metadata["urn"] = commentary_urn

        glosses = collect_glosses(tei_file, metadata["about"], commentary_urn)

        outdir = OUT_ROOT / f"sec00009.{d.name}.perseus-eng1"

        outdir.mkdir(exist_ok=True)

        outfile = outdir / "glossae_001.jsonl"

        with open(outfile, "w", newline="") as f:
            for gloss in glosses:
                print(json.dumps(asdict(gloss), ensure_ascii=False), file=f)

        metadata_file = outdir / "metadata.json"

        with open(metadata_file, "w") as fp:
            json.dump(metadata, fp)

if __name__ == "__main__":
    process_sec00009()
