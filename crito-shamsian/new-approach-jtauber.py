#!/usr/bin/env python3

import csv
from pathlib import Path
import re


def normalize_greek(text):
    text = text.replace("\u1fbd", "\u2019")
    text = text.replace(":", "·")
    return text


GREEK_WORD_FIX = {
    ",προτιθέντων": "προτιθέντων",
}


def load_rows(filename):
    with Path(filename).open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = [r for r in reader]
        return rows


def skip_substring(A, B, tokens_to_ignore=None):
    if tokens_to_ignore is None:
        tokens_to_ignore = set()
    found = False

    matches = []
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


table = load_rows("wegner-corrected-finalized-versions.csv")
treebank = load_rows("wegner-corrected-treebank.csv")

greek_sentences = {}
persian_sentences = {}
for row in table:
    key = row["Title3"].split("|")[1].strip(".")
    assert key not in greek_sentences
    if key == "231":
        greek_sentences["231"] = (
            "σὺ δὲ οὔτε Λακεδαίμονα προῃροῦ οὔτε Κρήτην, ἃς δὴ ἑκάστοτε φῂς εὐνομεῖσθαι, οὔτε ἄλλην οὐδεμίαν τῶν Ἑλληνίδων πόλεων οὐδὲ τῶν βαρβαρικῶν, ἀλλὰ ἐλάττω ἐξ αὐτῆς ἀπεδήμησας ἢ οἱ χωλοί τε καὶ τυφλοὶ καὶ οἱ ἄλλοι ἀνάπηροι·"
        )
    else:
        greek_sentences[key] = normalize_greek(row["Greek"])
    persian_sentences[key] = row["Primary translation"].strip()


def align_from_column(column: str):
    sentence_show = set()

    for row in treebank:
        # sentence_id = row["sentence_id"]
        sentence_id = row["word - ref"].split("|")[2]
        word_id = row["word - ref"].split("|")[3]
        greek_word = normalize_greek(row["word - form"])

        if greek_word in GREEK_WORD_FIX:
            greek_word = GREEK_WORD_FIX[greek_word]

        persian_translation = row[column].strip()

        greek_sentences[sentence_id]

        if greek_word not in ["[0]", "[1]", "[2]", "[3]", "[4]", "—"]:
            if greek_word not in greek_sentences[sentence_id]:
                print(greek_sentences[sentence_id])
                print(greek_word, sentence_id)
                print("***")
                quit()

        if sentence_id not in sentence_show:
            print()
            print(f"# {sentence_id}")
            print(persian_sentences[sentence_id], sep="\t")
            s_split = [
                token.strip("،؟.:«»![]؛")
                for token in re.split(r"[\u0020]", persian_sentences[sentence_id])
            ]
            tokens = list(enumerate(s_split, 1))
            print("  ".join(b + "{" + str(a) + "}" for a, b in tokens))

            sentence_show.add(sentence_id)
            tokens_used = set()

        if persian_translation:
            # t_split = re.split(r"[\u0020]", persian_translation)
            # print("\t" + word_id, " ".join(t_split), end=" ")
            # found = False
            # for i in range(1, len(s_split) + 1):
            #     poss = s_split[i - 1:i+len(t_split) - 1]
            #     if poss == t_split:
            #         print(" ".join([("{" + str(j) + "}") for j in range(i, i+len(t_split))]))
            #         found = True
            # if not found:
            #     print("X")

            t_split = re.split(r"[\u0020]", persian_translation)
            print("\t" + word_id, " ".join(t_split), end=" ")
            matches = skip_substring(s_split, t_split, tokens_used)
            if not matches:
                matches = skip_substring(s_split, t_split)
            if matches:
                print(" ".join([("{" + str(j) + "}") for j in matches]))
                for match in matches:
                    tokens_used.add(match)
            else:
                print("X")


def main():
    alignment_columns = [
        "Primary translation",
        "Literal translation",
        "Secondary translation",
    ]
    for column in alignment_columns:
        print(f"Aligning based on word-level alignment in {column}")
        align_from_column(column)


if __name__ == "__main__":
    main()