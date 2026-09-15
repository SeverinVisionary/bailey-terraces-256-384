#!/usr/bin/env python3
"""Rebuild data/negative_controls.jsonl.gz and negative_controls_log.txt.

Every record here is WRONG on purpose, and verify_terrace.py must reject every
one. A checker that accepts everything proves nothing; these records are the
evidence that it does not.

Six controls, (a)-(f), were built earlier from real groups of order 256 and are
kept exactly as they were, except that the explanation attached to (d) is
replaced by a correct proof. Three more, (g)-(i), attack the part of the
checker that decides whether the data describes a group at all -- the part the
first six never exercised:

  (g) a non-associative operation whose tallies nonetheless come out like a
      terrace's (it passed a checker that only did the tally);
  (h) generators that are not permutations;
  (i) more generators than relative orders: the tally sees only the first
      generator, a cyclic group of order 8, and would accept a genuine terrace
      of it, while the unused second generator makes the "group" non-abelian.

Usage: python3 scripts/build_negative_controls.py   (run from the package root)
It reads the existing file for (a)-(f), so it is idempotent.
"""
import gzip
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import verify_terrace  # noqa: E402

PATH = os.path.join(HERE, "data", "negative_controls.jsonl.gz")
LOG = os.path.join(HERE, "negative_controls_log.txt")

KEEP = ["NEGATIVE_CONTROL_A_swap", "NEGATIVE_CONTROL_B_repeat_omit",
        "NEGATIVE_CONTROL_C_bad_start", "NEGATIVE_CONTROL_D_C2^8",
        "NEGATIVE_CONTROL_E_wrong_presentation", "NEGATIVE_CONTROL_F_last_two_transposed"]

D_TEXT = (
    "(d) C_2^8 = SmallGroup(256,56092), elementary abelian and non-cyclic: no ordering "
    "of it is a terrace. Every non-identity element is its own inverse, so a terrace "
    "would need each of the 255 non-identity elements exactly once among the 255 "
    "differences. The product of the differences telescopes: b_1 b_2 ... b_255 = "
    "a_1^-1 a_256 = a_256, which is not the identity. But in C_2^m with m >= 2 the "
    "product of all non-identity elements is the identity: written as 0/1 vectors, "
    "each of the m coordinates is 1 in exactly 2^(m-1) elements, an even number, so "
    "every coordinate of the sum is 0. Contradiction. So the checker must reject the shipped "
    "ordering, and would have to reject any ordering of this group."
)

EXTRA = [
    {
        "id": "NEGATIVE_CONTROL_G_not_associative",
        "order": 6, "k": 2, "rel": [2, 3],
        "gens_perm": [[3, 4, 5, 0, 2, 1], [1, 2, 0, 4, 5, 3]],
        "witness": [0, 3, 1, 2, 4, 5],
        "testing": ("(g) not a group: the operation these 'generators' induce is not "
                    "associative ((1*3)*3 = 2 but 1*(3*3) = 1), and the first generator "
                    "has order 4, not its declared 2. The difference tally alone accepts "
                    "this ordering."),
    },
    {
        "id": "NEGATIVE_CONTROL_H_not_permutations",
        "order": 6, "k": 2, "rel": [2, 3],
        "gens_perm": [[1, 0, 0, 0, 5, 0], [4, 5, 0, 0, 2, 3]],
        "witness": [0, 1, 2, 3, 4, 5],
        "testing": ("(h) not a group: neither 'generator' is a permutation of 0..5. The "
                    "difference tally alone accepts this ordering."),
    },
    {
        "id": "NEGATIVE_CONTROL_I_generators_exceed_relative_orders",
        "order": 8, "k": 2, "rel": [8],
        "gens_perm": [[1, 2, 3, 4, 5, 6, 7, 0], [0, 7, 6, 5, 4, 3, 2, 1]],
        "witness": [0, 1, 7, 2, 6, 3, 5, 4],
        "testing": ("(i) inconsistent data: two generators but one relative order. The "
                    "tally uses only the first generator, a cyclic group of order 8, of "
                    "which this ordering is a genuine terrace; the second generator makes "
                    "the described structure non-abelian. The record must be rejected "
                    "rather than read as a terrace of a non-abelian group."),
    },
]


def main():
    old = {}
    with gzip.open(PATH, "rt") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                old[r["id"]] = r
    missing = [i for i in KEEP if i not in old]
    if missing:
        raise SystemExit("existing controls missing: %s" % missing)

    records = []
    for i in KEEP:
        r = dict(old[i])
        if i == "NEGATIVE_CONTROL_D_C2^8":
            r["testing"] = D_TEXT
        records.append(r)
    for r in EXTRA:
        r = dict(r)
        r["source"] = "negative_control"
        records.append(r)

    lines = []
    for r in records:
        # The same strict decoding and checks the verifier's main() applies to a record.
        ok, reason = verify_terrace.check_record(json.loads(json.dumps(r)))
        if ok:
            raise SystemExit("%s is ACCEPTED by the verifier -- the control is broken" % r["id"])
        lines.append("FAIL  %s\n  testing: %s\n  verifier reason: %s\n" % (r["id"], r["testing"], reason))

    with gzip.open(PATH, "wt") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    with open(LOG, "w") as f:
        f.write("".join(lines))
        f.write("\n%d / %d correctly FAIL, 0 / %d incorrectly PASS.\n"
                % (len(records), len(records), len(records)))
    print("wrote %d negative controls; all rejected by the verifier" % len(records))


if __name__ == "__main__":
    main()
