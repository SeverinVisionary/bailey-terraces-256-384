#!/usr/bin/env python3
"""Coverage check: do the shipped files cover every group they claim to?

verify_terrace.py answers "is each shipped ordering really a terrace of a
genuine group of the stated order?". This script answers the other half:
"is every group that Bailey's conjecture is about actually in there?". It reads
no witness.

THE ARGUMENT, for one order n.

  (1) Every record is well-formed for order n: its "order" field is n (the
      file it sits in says n), its id is an integer in 1..NrSmallGroups(n),
      it has as many relative orders as generators, and the relative orders
      multiply to n. (verify_terrace.py separately proves the generators form
      a genuine group of order n.)
  (2) Every record's group is non-abelian, checked from its own generator
      permutations: gens_perm[i] is right multiplication by generator i, and
      a[b[x]] = x*g_b*g_a, so two of these permutations commute exactly when
      the two generators do; the group is abelian exactly when every pair
      commutes.
  (3) The distinct ids are counted. An id appearing in more than one file is
      allowed only if every copy describes the same group (identical
      generator data); the different witnesses are then two terraces of it.
  (4) The number of groups of order n is NrSmallGroups(n), and the number of
      ABELIAN ones is fixed by the classification of finite abelian groups:
      the product over the prime powers p^e dividing n of p(e), the number of
      partitions of e.
        order 256 = 2^8      -> p(8)            = 22
        order 384 = 2^7 * 3  -> p(7) * p(1) = 15 * 1 = 15
  (5) No generator data appears under two different ids (a cheap guard
      against one group's data being copied under another id).
  (6) If the count of distinct ids equals NrSmallGroups(n) minus that number,
      then every non-abelian id is present. That this means every
      non-abelian GROUP has a terrace depends on each record's id being the
      group its data describes -- which this script cannot check (below).

WHAT THIS DOES NOT CHECK, stated plainly. That the record labelled
SmallGroup(n, i) really is GAP's group number i. Nothing in plain Python can:
it is a fact about GAP's library. The labels were attached when the groups were
exported from GAP, by calling SmallGroup(n, i) and writing its generators
alongside i. If a label were wrong -- say a different presentation of an
already-shipped group, or of an abelian group, under id i -- this count would
not notice, and SmallGroup(n, i) would have no terrace here.
scripts/check_ids.g, run in GAP, closes exactly that gap by recomputing IdGroup
for every record. Completeness is established by this script AND that one.

The only other numbers taken from GAP are NrSmallGroups(256) = 56092 and
NrSmallGroups(384) = 20169.

Usage: python3 scripts/coverage_check.py [data_dir] [order ...]
Exit status is 0 only if every requested order comes out exactly as expected.
"""
import base64
import glob
import gzip
import json
import os
import struct
import sys
from collections import defaultdict

NR_SMALL_GROUPS = {256: 56092, 384: 20169}
PRIME_POWERS = {256: [8], 384: [7, 1]}          # exponents of 2^8 and of 2^7 * 3^1
EXPECTED_SHARED_IDS = {256: 0, 384: 101}         # ids deliberately shipped twice


def reject_duplicate_keys(pairs):
    seen = {}
    for key, value in pairs:
        if key in seen:
            raise ValueError("duplicate key %r in record" % key)
        seen[key] = value
    return seen


def partitions(n, cache={}):
    """Number of partitions of n, by Euler's pentagonal number recurrence."""
    if n < 0:
        return 0
    if n == 0:
        return 1
    if n in cache:
        return cache[n]
    total, k = 0, 1
    while True:
        g1 = k * (3 * k - 1) // 2
        g2 = k * (3 * k + 1) // 2
        if g1 > n and g2 > n:
            break
        sign = -1 if k % 2 == 0 else 1
        total += sign * (partitions(n - g1) + partitions(n - g2))
        k += 1
    cache[n] = total
    return total


def n_abelian(order):
    out = 1
    for e in PRIME_POWERS[order]:
        out *= partitions(e)
    return out


def gens_of(rec):
    n, k, width = rec["order"], rec["k"], rec["width"]
    raw = base64.b64decode(rec["gens_perm_b64"], validate=True)
    if len(raw) != width * k * n:
        raise ValueError("generator data is %d bytes, expected %d" % (len(raw), width * k * n))
    flat = struct.unpack(("<%dB" if width == 1 else "<%dH") % (k * n), raw)
    return [flat[i * n:(i + 1) * n] for i in range(k)]


def is_nonabelian(gens):
    n = len(gens[0])
    for i in range(len(gens)):
        a = gens[i]
        for j in range(i + 1, len(gens)):
            b = gens[j]
            for x in range(n):
                if a[b[x]] != b[a[x]]:
                    return True
    return False


def malformed(rec, order):
    """None if the record is well-formed for this order, else the reason."""
    if rec.get("order") != order:
        return "order field is %r, file is order %d" % (rec.get("order"), order)
    i = rec.get("id")
    if not isinstance(i, int) or isinstance(i, bool) or not 1 <= i <= NR_SMALL_GROUPS[order]:
        return "id %r is not an integer in 1..%d" % (i, NR_SMALL_GROUPS[order])
    rel, k = rec.get("rel"), rec.get("k")
    if not isinstance(rel, list) or len(rel) != k:
        return "k=%r but %r relative orders" % (k, rel)
    prod = 1
    for r in rel:
        prod *= r
    if prod != order:
        return "relative orders multiply to %d, not %d" % (prod, order)
    if rec.get("width") != (1 if order <= 256 else 2):
        return "width %r is wrong for order %d" % (rec.get("width"), order)
    return None


def check_order(data_dir, order):
    files = sorted(glob.glob(os.path.join(data_dir, "order%d_*.jsonl.gz" % order)))
    print("\n== order %d ==" % order)
    if not files:
        print("  no data files found in %s" % data_dir)
        return False

    copies = defaultdict(list)          # id -> [(file, gens_perm_b64)]
    problems = []
    n_records = 0
    for path in files:
        name = os.path.basename(path)
        n_here = 0
        with gzip.open(path, "rt") as f:
            for line in f:
                if not line.strip():
                    continue
                n_here += 1
                n_records += 1
                try:
                    rec = json.loads(line, object_pairs_hook=reject_duplicate_keys)
                    why = malformed(rec, order)
                    if why is None and not is_nonabelian(gens_of(rec)):
                        why = "the group is abelian"
                except Exception as exc:  # noqa: BLE001 -- unreadable is a failure
                    rec, why = {}, "unreadable: %s: %s" % (type(exc).__name__, exc)
                if why is not None:
                    problems.append((name, n_here, rec.get("id"), why))
                    continue
                copies[rec["id"]].append((name, rec["gens_perm_b64"]))
        print("  %-34s %6d records" % (name, n_here))

    shared = {i: c for i, c in copies.items() if len(c) > 1}
    inconsistent = [i for i, c in shared.items() if len({g for _, g in c}) != 1]
    ids_by_gens = defaultdict(set)
    for i, c in copies.items():
        for _, g in c:
            ids_by_gens[g].add(i)
    same_gens_other_ids = sorted(sorted(s) for s in ids_by_gens.values() if len(s) > 1)
    total = NR_SMALL_GROUPS[order]
    n_ab = n_abelian(order)
    expected = total - n_ab

    print("  records                            %6d" % n_records)
    print("  malformed, unreadable or abelian   %6d %s" % (len(problems), problems[:5]))
    print("  distinct ids                       %6d" % len(copies))
    print("  ids shipped in two or more files   %6d (expected %d; group data identical across copies: %s)"
          % (len(shared), EXPECTED_SHARED_IDS[order], "yes" if not inconsistent else "NO %s" % inconsistent[:5]))
    print("  NrSmallGroups(%d)                 %6d" % (order, total))
    print("  abelian groups of this order       %6d (outside the conjecture)" % n_ab)
    print("  non-abelian, must all be covered   %6d" % expected)

    ok = True
    if problems:
        print("  ORDER %d: FAIL -- %d bad record(s)" % (order, len(problems)))
        ok = False
    if inconsistent:
        print("  ORDER %d: FAIL -- an id is shipped twice with different group data" % order)
        ok = False
    if len(shared) != EXPECTED_SHARED_IDS[order]:
        print("  ORDER %d: FAIL -- %d ids shipped more than once, expected %d"
              % (order, len(shared), EXPECTED_SHARED_IDS[order]))
        ok = False
    if same_gens_other_ids:
        print("  ORDER %d: FAIL -- identical generator data under different ids %s"
              % (order, same_gens_other_ids[:5]))
        ok = False
    if len(copies) != expected:
        print("  ORDER %d: FAIL -- %d distinct ids, expected %d" % (order, len(copies), expected))
        ok = False
    if ok:
        print("  ORDER %d: all %d non-abelian ids are present, each with its own generator data."
              % (order, expected))
        print("  (That this is every non-abelian group also needs each id to be right:"
              " scripts/check_ids.g checks that in GAP.)")
    return ok


def main():
    args = sys.argv[1:]
    default_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    data_dir = args[0] if args and not args[0].isdigit() else default_dir
    orders = [int(a) for a in args if a.isdigit()] or sorted(NR_SMALL_GROUPS)
    ok = True
    for order in orders:
        if order not in NR_SMALL_GROUPS:
            print("unknown order %d" % order)
            ok = False
            continue
        ok = check_order(data_dir, order) and ok
    print("\nCOVERAGE: %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
