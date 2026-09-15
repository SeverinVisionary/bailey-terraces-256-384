#!/usr/bin/env python3
"""Write every witness record's group in a form GAP can read, for check_ids.g.

For each data/order<N>_*.jsonl.gz file this writes gap_input/<same name>.g,
defining a GAP list RECORDS of [n, id, [image lists of the generators]]. Point
images are shifted from 0..n-1 to 1..n, as PermList expects. Nothing else is
exported: the witness is irrelevant to which group a record describes.

Usage: python3 scripts/export_for_gap.py        (from the package root)
"""
import base64
import glob
import gzip
import json
import os
import struct

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "gap_input")


def main():
    os.makedirs(OUT, exist_ok=True)
    for path in sorted(glob.glob(os.path.join(HERE, "data", "order*_*.jsonl.gz"))):
        name = os.path.basename(path)[:-len(".jsonl.gz")]
        n_rec = 0
        with gzip.open(path, "rt") as f, open(os.path.join(OUT, name + ".g"), "w") as g:
            g.write("RECORDS := [\n")
            first = True
            for line in f:
                if not line.strip():
                    continue
                r = json.loads(line)
                n, k, w = r["order"], r["k"], r["width"]
                raw = base64.b64decode(r["gens_perm_b64"], validate=True)
                flat = struct.unpack(("<%dB" if w == 1 else "<%dH") % (k * n), raw)
                gens = [[x + 1 for x in flat[i * n:(i + 1) * n]] for i in range(k)]
                g.write(("" if first else ",\n") + "[%d,%d,%s]" % (n, r["id"], json.dumps(gens).replace(" ", "")))
                first = False
                n_rec += 1
            g.write("\n];\n")
        print("gap_input/%s.g: %d records" % (name, n_rec))


if __name__ == "__main__":
    main()
