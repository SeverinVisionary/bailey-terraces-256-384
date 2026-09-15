#!/usr/bin/env python3
"""Rewrite an older-schema witness file into the one verify_terrace.py reads.

Two compact schemas exist in this project's history. Both hold the same
integers; they differ only in how the generator permutations are packed:

  old (order-384 shards 0, 2 and 3):  "gens_perm_b64": [b64, b64, ...]
                                      one base64 string per generator, no "width"
  current (everything else):          "gens_perm_b64": b64
                                      one string for all k*n entries, plus "width"

verify_terrace.py reads only the current schema, so the three older files were
converted with this script before being shipped. The conversion is a repacking
of bytes: it checks that the new single string decodes to the same integers as
the old per-generator strings. That is a consistency check of the repacking, not
an independent decoding of the old files; what guarantees the shipped records is
that every repacked record was afterwards verified by verify_terrace.py and
id-checked by check_ids.g like every other record. It never touches the witness.

Usage: python3 scripts/canonicalize_gens_schema.py IN.jsonl.gz OUT.jsonl.gz
"""
import base64
import gzip
import json
import struct
import sys


def main():
    in_path, out_path = sys.argv[1], sys.argv[2]
    n_rec = 0
    with gzip.open(in_path, "rt") as fi, gzip.open(out_path, "wt") as fo:
        for line in fi:
            if not line.strip():
                continue
            r = json.loads(line)
            n = r["order"]
            width = 1 if n <= 256 else 2
            fmt = "<%dB" if width == 1 else "<%dH"
            if not isinstance(r["gens_perm_b64"], list):
                raise SystemExit("%s is already in the current schema" % in_path)
            if len(r["gens_perm_b64"]) != r["k"]:
                raise SystemExit("record %r: %d generator strings, k=%d"
                                 % (r["id"], len(r["gens_perm_b64"]), r["k"]))
            raw = [base64.b64decode(g) for g in r["gens_perm_b64"]]
            for b in raw:
                if len(b) != width * n:
                    raise SystemExit("record %r: generator block is %d bytes, expected %d"
                                     % (r["id"], len(b), width * n))
            joined = base64.b64encode(b"".join(raw)).decode("ascii")

            old = [list(struct.unpack(fmt % n, b)) for b in raw]
            flat = struct.unpack(fmt % (n * r["k"]), base64.b64decode(joined))
            new = [list(flat[i * n:(i + 1) * n]) for i in range(r["k"])]
            if new != old:
                raise SystemExit("record %r: repacking changed the integers" % (r["id"],))

            out = {"id": r["id"], "order": n, "k": r["k"], "rel": r["rel"], "width": width,
                   "gens_perm_b64": joined, "witness_b64": r["witness_b64"]}
            if "source" in r:
                out["source"] = r["source"]
            fo.write(json.dumps(out) + "\n")
            n_rec += 1
    print("%s -> %s: %d records repacked, integers identical" % (in_path, out_path, n_rec))


if __name__ == "__main__":
    main()
