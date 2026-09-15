#!/usr/bin/env python3
"""
Stand-alone terrace verifier.  Plain Python 3, standard library only.
No GAP, no imports from this repository, no network access, no trust in
whoever produced the data files below.  Full explanation in README.md;
this docstring gives just enough to read the code below.

WHAT THIS FILE CHECKS, per record. First, that the record is well-formed and
strictly encoded (decode_record). Then, that it describes a genuine group of
the stated order (check_is_group: the generators are permutations generating a
regular permutation group of exactly that order). Then, that the ordering is a
terrace of that group (check_terrace). It does NOT check that the group is the
SmallGroup its id names in GAP's library; scripts/check_ids.g does that, and
needs GAP.

WHAT A "TERRACE" IS (the only definition this file uses).  Let G be a
finite group of order n, with identity element e.  An ordering
a_1, ..., a_n of ALL n elements of G, with a_1 = e, is a TERRACE if the
n-1 "differences" b_i = (a_i)^-1 * a_{i+1} satisfy: every element that is
its own inverse (other than e) occurs EXACTLY ONCE among the b_i, and
every other element g occurs, TOGETHER WITH ITS INVERSE g^-1, EXACTLY
TWICE IN TOTAL (g twice, g^-1 twice, or once each -- only the combined
count is pinned down).  Checking this is one linear pass plus one tally.

HOW A GROUP IS DESCRIBED HERE (the "presentation").  Shipping a full
n x n multiplication table for every group would be far too much data
(README.md works out the arithmetic).  Instead each group is described
by a handful of GENERATORS g_0, ..., g_{k-1}.  gens_perm[i] tells you, for
every element x (an index 0..n-1, index 0 always meaning e), what index
x * g_i has -- i.e. gens_perm[i] is the permutation of {0,...,n-1} given by
right-multiplying every element by g_i.  rel[i] is the RELATIVE order of g_i
in the polycyclic generating sequence the generators come from: the number of
exponents 0 <= e_i < rel[i] used for g_i in the normal form below.  It is
generally NOT the order of g_i (a generator of order 4 often has relative
order 2), and the product of the rel[i] is n.

For such a sequence every element x can be written uniquely as
g_0^(e_0) * ... * g_{k-1}^(e_{k-1}) with 0 <= e_i < rel[i].  This file does
NOT take that on trust: build_index_to_exponents() evaluates all n exponent
tuples starting from the identity and requires every one of the n indices to
be reached, which forces the map from tuples to indices to be a bijection.
Once you can right-multiply by each generator, x * y for ANY x, y is computed
by decomposing y this way and applying the generator permutations in turn,
starting from x.  check_is_group() proves this really is a group product.

ELEMENT-INDEXING CONVENTION.  Every group element is referred to purely
by an integer index in 0..n-1.  Index 0 always denotes the identity e.
Indices are just labels, fixed once per group and used consistently for
the generator permutations and the terrace witness alike. A witness is
a list of all n indices in some order, starting with 0.

TWO ON-DISK FORMATS, same content, both decoded STRICTLY.  A record's
generators and witness may be given either as plain JSON integer arrays
(`gens_perm`, `witness`; used by the negative controls), or in the COMPACT
form used by every witness file in this package: `gens_perm_b64` /
`witness_b64`, each the base64 encoding of the same integers packed as
fixed-width little-endian bytes, `width` bytes per integer -- 1 if the order
is <= 256, 2 otherwise -- with `width` itself in the record.  decode_record()
undoes exactly this packing and rejects anything else: unknown or duplicate
keys, a key set mixing the two formats, non-integer or boolean numbers,
non-alphabet base64 characters, a wrong `width`, and byte strings whose length
is not exactly width * (number of integers).  So any two correct readers of a
record that passes see the same integers.  check_terrace() itself never knows
which form a record arrived in.  Data files may be gzip-compressed (detected
by a `.gz` extension); gzip is Python standard library, same as json/base64.
"""

import base64
import binascii
import gzip
import json
import sys

COMPACT_KEYS = {"id", "order", "k", "rel", "width", "gens_perm_b64", "witness_b64"}
PLAIN_KEYS = {"id", "order", "k", "rel", "gens_perm", "witness"}
OPTIONAL_KEYS = {"source", "testing"}


def is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def reject_duplicate_keys(pairs):
    seen = {}
    for key, value in pairs:
        if key in seen:
            raise ValueError("duplicate key %r in record" % key)
        seen[key] = value
    return seen


def parse_line(line):
    return json.loads(line, object_pairs_hook=reject_duplicate_keys)


def unpack_ints(raw_bytes, width, count):
    if len(raw_bytes) != width * count:
        raise ValueError("%d bytes decoded, expected exactly width*count = %d*%d = %d"
                         % (len(raw_bytes), width, count, width * count))
    return [int.from_bytes(raw_bytes[i:i + width], "little")
            for i in range(0, len(raw_bytes), width)]


def strict_b64(text, field):
    if not isinstance(text, str):
        raise ValueError("%s is not a string" % field)
    try:
        return base64.b64decode(text, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("%s is not canonical base64: %s" % (field, exc))


def int_list(v, field):
    if not isinstance(v, list) or not all(is_int(x) for x in v):
        raise ValueError("%s must be a list of integers" % field)
    return v


def decode_record(record):
    """Return (order, gens_perm, rel, witness) for a record in EITHER format,
    or raise ValueError if the record is not strictly well-formed."""
    if not isinstance(record, dict):
        raise ValueError("record is not a JSON object")
    keys = set(record) - OPTIONAL_KEYS
    if keys == COMPACT_KEYS:
        compact = True
    elif keys == PLAIN_KEYS:
        compact = False
    else:
        raise ValueError("fields %s match neither format (compact %s or plain %s, plus optional %s)"
                         % (sorted(record), sorted(COMPACT_KEYS), sorted(PLAIN_KEYS), sorted(OPTIONAL_KEYS)))
    n, k = record["order"], record["k"]
    if not is_int(n) or n < 1:
        raise ValueError("order %r is not a positive integer" % (n,))
    if not is_int(k) or k < 1:
        raise ValueError("k %r is not a positive integer" % (k,))
    rel = int_list(record["rel"], "rel")
    if len(rel) != k:
        raise ValueError("k=%d but %d relative orders" % (k, len(rel)))
    if compact:
        width = record["width"]
        if not is_int(width) or width != (1 if n <= 256 else 2):
            raise ValueError("width %r is wrong for order %d (must be %d)"
                             % (width, n, 1 if n <= 256 else 2))
        flat = unpack_ints(strict_b64(record["gens_perm_b64"], "gens_perm_b64"), width, k * n)
        gens_perm = [flat[i * n:(i + 1) * n] for i in range(k)]
        witness = unpack_ints(strict_b64(record["witness_b64"], "witness_b64"), width, n)
    else:
        gens = record["gens_perm"]
        if not isinstance(gens, list):
            raise ValueError("gens_perm must be a list of lists")
        gens_perm = [int_list(g, "gens_perm[%d]" % i) for i, g in enumerate(gens)]
        witness = int_list(record["witness"], "witness")
    return n, gens_perm, rel, witness


def open_maybe_gzip(path):
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8")
    return open(path, encoding="utf-8")


def build_index_to_exponents(n, rel, gens_perm):
    """For every element index, find the exponents (e_0,...,e_{k-1}) with
    0 <= e_i < rel[i] such that starting at the identity (index 0) and
    right-multiplying by g_0 e_0 times, then g_1 e_1 times, ..., lands on
    that index.  There are exactly n such tuples (the product of the rel[i],
    checked in check_is_group) and n indices.  The final scan below raises
    unless every index was reached, so an accepted record's tuples reach every
    index exactly once: the map is a bijection, not merely assumed to be."""
    k = len(rel)
    index_to_exp = [None] * n

    def recurse(exps, current_index):
        i = len(exps)
        if i == k:
            index_to_exp[current_index] = tuple(exps)
            return
        idx = current_index
        for e in range(rel[i]):
            recurse(exps + [e], idx)
            idx = gens_perm[i][idx]  # one more multiplication by g_i

    recurse([], 0)
    for i, entry in enumerate(index_to_exp):
        if entry is None:
            raise ValueError("element index %d was never reached -- the exponent tuples "
                              "do not cover the group exactly once" % i)
    return index_to_exp


def multiply(x, y, gens_perm, index_to_exp):
    """Compute x * y, both given as element indices, returning an index."""
    result = x
    for gen_index, exponent in enumerate(index_to_exp[y]):
        for _ in range(exponent):
            result = gens_perm[gen_index][result]
    return result


def build_inverse_table(n, gens_perm, index_to_exp):
    """inverse[x] = the index y with x * y = e (index 0)."""
    inverse = [None] * n
    for x in range(n):
        for y in range(n):
            if multiply(x, y, gens_perm, index_to_exp) == 0:
                inverse[x] = y
                break
    return inverse


def check_is_group(n, rel, gens_perm):
    """Returns (True, None) only if the record really describes a group of
    order n, acting on the indices 0..n-1 by right multiplication.

    Without this, the data could describe something that is not a group at
    all -- a non-associative operation, generators that are not
    permutations, a declared order that does not match -- and the terrace
    tally below would still be computed on it and could come out "right".

    The test: the generators must be permutations of 0..n-1, and the set of
    all products of them (the permutation group they generate, found by
    closing under composition) must contain EXACTLY n permutations, sending
    index 0 to n DIFFERENT places. A permutation group of order n that moves
    one point to n different places acts regularly; a regular permutation
    group is a group of order n, and x * y is then "apply to x the unique
    group element that sends 0 to y". That is exactly what multiply() below
    computes from any word for y in the generators, so every later product
    is a genuine group product, associativity included."""
    k = len(rel)
    if len(gens_perm) != k:
        return False, "k=%d relative orders but %d generators" % (k, len(gens_perm))
    size = 1
    for r in rel:
        if not is_int(r) or r < 2:
            return False, "relative order %r is not an integer >= 2" % (r,)
        size *= r
    if size != n:
        return False, "product of relative orders is %d, not the order %d" % (size, n)
    identity = tuple(range(n))
    gens = []
    for i, p in enumerate(gens_perm):
        if len(p) != n or sorted(p) != list(identity):
            return False, "generator %d is not a permutation of 0..%d" % (i, n - 1)
        gens.append(tuple(p))
    # Close under right multiplication by the generators. Composition order is
    # irrelevant to the size of the group generated, and stopping once the set
    # exceeds n keeps a malformed record from running away.
    seen = {identity}
    frontier = [identity]
    while frontier:
        nxt = []
        for g in frontier:
            for h in gens:
                gh = tuple(h[g[x]] for x in range(n))
                if gh not in seen:
                    seen.add(gh)
                    if len(seen) > n:
                        return False, "the generators generate more than %d permutations" % n
                    nxt.append(gh)
        frontier = nxt
    if len(seen) != n:
        return False, "the generators generate %d permutations, not %d" % (len(seen), n)
    if len({g[0] for g in seen}) != n:
        return False, "the generated group does not act regularly on 0..%d" % (n - 1)
    return True, None


def check_terrace(n, gens_perm, rel, witness):
    """Returns (True, None) if `witness` is a terrace of the group described
    by (n, gens_perm, rel); otherwise (False, "human-readable reason")."""
    ok, reason = check_is_group(n, rel, gens_perm)
    if not ok:
        return False, "not a group: " + reason
    if len(witness) != n or sorted(witness) != list(range(n)):
        return False, "not an ordering of all %d elements (repeats or omissions)" % n
    if witness[0] != 0:
        return False, "does not start at the identity (index 0)"

    index_to_exp = build_index_to_exponents(n, rel, gens_perm)
    inverse = build_inverse_table(n, gens_perm, index_to_exp)

    difference_counts = [0] * n
    for i in range(n - 1):
        a_i, a_i_plus_1 = witness[i], witness[i + 1]
        b_i = multiply(inverse[a_i], a_i_plus_1, gens_perm, index_to_exp)
        difference_counts[b_i] += 1

    if difference_counts[0] != 0:
        return False, "the identity occurs %d time(s) as a difference (impossible: " \
                       "that would mean two equal consecutive entries)" % difference_counts[0]

    for g in range(1, n):
        g_inv = inverse[g]
        if g_inv == g:  # g is its own inverse (a self-inverse, "involution" element)
            if difference_counts[g] != 1:
                return False, ("self-inverse element %d occurs %d time(s) as a "
                                "difference, must occur exactly once" % (g, difference_counts[g]))
        elif g < g_inv:  # only check each {g, g^-1} pair once, from the smaller index
            total = difference_counts[g] + difference_counts[g_inv]
            if total != 2:
                return False, ("elements %d and %d (mutual inverses) occur %d time(s) "
                                "combined as a difference, must occur exactly 2" % (g, g_inv, total))
    return True, None


def check_record(record):
    """Decode a parsed record strictly, then check it. (ok, reason); never raises."""
    try:
        n, gens_perm, rel, witness = decode_record(record)
    except ValueError as exc:
        return False, "malformed record: %s" % exc
    try:
        return check_terrace(n, gens_perm, rel, witness)
    except Exception as exc:  # noqa: BLE001 -- any failure is a FAIL
        return False, "could not be checked: %s: %s" % (type(exc).__name__, exc)


def main():
    if len(sys.argv) < 2:
        print("usage: python3 verify_terrace.py <path-to-jsonl[.gz]-file> [more files...]")
        sys.exit(2)
    total = 0
    passed = 0
    unreadable_files = 0
    for path in sys.argv[1:]:
        # A malformed record, or a file that cannot be read to the end, is a
        # FAIL, never a crash: a crash would stop the run, and a caller that
        # ignored the exit status would then have nothing on stdout saying
        # anything went wrong.
        line_no = 0
        try:
            with open_maybe_gzip(path) as f:
                for line in f:
                    line_no += 1
                    if not line.strip():
                        continue
                    total += 1
                    try:
                        record = parse_line(line)
                        label = "SmallGroup(%s,%s)" % (record.get("order"), record.get("id"))
                        ok, reason = check_record(record)
                    except Exception as exc:  # noqa: BLE001 -- any failure is a FAIL
                        label = "line %d of %s" % (line_no, path)
                        ok, reason = False, "could not be checked: %s: %s" % (type(exc).__name__, exc)
                    if ok:
                        passed += 1
                        print("PASS  %s" % label)
                    else:
                        print("FAIL  %s  -- %s" % (label, reason))
        except Exception as exc:  # noqa: BLE001 -- an unreadable file is a failure
            unreadable_files += 1
            print("FAIL  file %s  -- could not be read past line %d: %s: %s"
                  % (path, line_no, type(exc).__name__, exc))
    if total == 0:
        print("FAIL  no records found in %s" % " ".join(sys.argv[1:]))
    print("\n%d / %d PASS" % (passed, total))
    sys.exit(0 if passed == total and total > 0 and unreadable_files == 0 else 1)


if __name__ == "__main__":
    main()
