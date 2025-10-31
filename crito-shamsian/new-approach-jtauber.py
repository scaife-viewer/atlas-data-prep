#!/usr/bin/env python3

import csv
from collections import defaultdict
from io import TextIOWrapper
from pathlib import Path
import re


def normalize_greek(text: str):
    text = text.replace("\u1fbd", "\u2019")
    text = text.replace(":", "·")
    return text


GREEK_WORD_FIX = {
    ",προτιθέντων": "προτιθέντων",
}


def load_rows(filename: str):
    with Path(filename).open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = [r for r in reader]
        return rows


def skip_substring(A: list[str], B: list[str], tokens_to_ignore: set[int] | None=None):
    if tokens_to_ignore is None:
        tokens_to_ignore = set()
    found = False

    matches: list[int] | None = []
    for i in range(1, len(B) + 1):
        found = False
        if matches:
            start = matches[-1]
        else:
            start = 1
        for j in range(start, len(A) + 1):
            if j in tokens_to_ignore:
                continue
            if A[j - 1] == B[i - 1]:
                matches.append(j)
                found = True
                break
        if found:
            continue
        else:
            matches = None
            break

    return matches


refs: list[str] = []
for line in open("texts/tlg0059.tlg003.perseus-grc2b1.txt"):
    refs.append(line.split(" ", maxsplit=1)[0])

table = load_rows("wegner-corrected-finalized-versions.csv")
treebank = load_rows("wegner-corrected-treebank.csv")

greek_tokens = defaultdict(list)
for line in open("greek_tokens.tsv"):
    sentence_num, token_num, token = line.strip().split("\t")
    greek_tokens[sentence_num].append((token_num, token))

greek_sentences: dict[str, str] = {}
persian_sentences: defaultdict[str, dict[str, str]] = defaultdict(dict)
for row in table:
    key = row["Title3"].split("|")[1].strip(".")
    assert key not in greek_sentences
    if key == "231":
        greek_sentences[
            "231"
        ] = "σὺ δὲ οὔτε Λακεδαίμονα προῃροῦ οὔτε Κρήτην, ἃς δὴ ἑκάστοτε φῂς εὐνομεῖσθαι, οὔτε ἄλλην οὐδεμίαν τῶν Ἑλληνίδων πόλεων οὐδὲ τῶν βαρβαρικῶν, ἀλλὰ ἐλάττω ἐξ αὐτῆς ἀπεδήμησας ἢ οἱ χωλοί τε καὶ τυφλοὶ καὶ οἱ ἄλλοι ἀνάπηροι·"
    else:
        greek_sentences[key] = normalize_greek(row["Greek"])
    for column in ["Primary translation", "Literal translation", "Secondary translation"]:
        persian_sentences[column][key] = row[column].strip()


def align_from_column(column: str, out: TextIOWrapper):
    sentence_show: set[str] = set()

    for row in treebank:
        [_, _, sentence_id, word_id] = row["word - ref"].split("|")
        greek_word = normalize_greek(row["word - form"])

        if greek_word in GREEK_WORD_FIX:
            greek_word = GREEK_WORD_FIX[greek_word]

        persian_translation = row[column].strip()

        if greek_word not in ["[0]", "[1]", "[2]", "[3]", "[4]", "—"]:
            if greek_word not in greek_sentences[sentence_id]:
                print(greek_sentences[sentence_id])
                print(greek_word, sentence_id)
                print("***")
                quit()

        if sentence_id not in sentence_show:
            offset = False
            print(file=out)
            print(f"# {refs[int(sentence_id)-1]} ({sentence_id})", file=out)
            print(file=out)
            print(greek_sentences[sentence_id].strip(), sep="\t", file=out)
            print(persian_sentences[column][sentence_id], sep="\t", file=out)
            print(file=out)

            # r_split = [
            #     token.strip(".,;")
            #     for token in re.split(r"[\u0020]", greek_sentences[sentence_id].strip())
            # ]
            # tokens = list(enumerate(r_split, 1))
            # print("  ".join(b + "[" + str(a) + "]" for a, b in tokens), file=out)

            print("  ".join(b + "[" + str(a) + "]" for a, b in greek_tokens[sentence_id]), file=out)

            s_split = [
                token.strip("،؟.:«»![]؛")
                for token in re.split(r"[\u0020]", persian_sentences[column][sentence_id])
            ]
            tokens = list(enumerate(s_split, 1))
            print("  ".join(b + "{" + str(a) + "}" for a, b in tokens), file=out)

            sentence_show.add(sentence_id)
            tokens_used: set[int] = set()

            print(file=out)

        if persian_translation:
            t_split = re.split(r"[\u0020]", persian_translation)
            if word_id == "1" and greek_sentences[sentence_id].split()[0] in [
                "Σωκράτης.",
                "Κρίτων.",
            ]:
                offset = True
                print("\t[0] {1}", s_split[0], file=out)
            print("\t[" + word_id + "]", " ".join(t_split), end=" ", file=out)
            matches = skip_substring(s_split, t_split, tokens_used)
            if not matches:
                matches = skip_substring(s_split, t_split)
            if matches:
                print(" ".join([("{" + str(j) + "}") for j in matches]), file=out)
                for match in matches:
                    tokens_used.add(match)
            else:
                print("XXX", file=out)


def main():
    alignment_columns = [
        ("Primary translation", "alignment_primary.txt"),
        ("Literal translation", "alignment_literal.txt"),
        ("Secondary translation", "alignment_secondary.txt"),
    ]
    for column, output in alignment_columns:
        with open(output, "w") as g:
            align_from_column(column, g)


if __name__ == "__main__":
    main()
