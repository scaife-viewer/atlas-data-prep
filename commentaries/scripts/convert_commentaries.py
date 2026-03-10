#!/usr/bin/env python

import json
import logging
import os
import re

from pathlib import Path

from lxml import etree

from .conversion_utils import to_xml
from .ref_to_urn import get_ref, get_urn
from .convert_xml_to_json import convert_xml_to_json

logging.basicConfig(level=logging.INFO)

PDLREFWK_DATA_DIR = Path(os.getenv("PDLREFWK_ROOT", "canonical_pdlrefwk")) / "data"


def convert_commentaries():
    for textgroup in PDLREFWK_DATA_DIR.iterdir():
        print(textgroup.name)
