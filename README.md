# An explicit terrace for every non-abelian group of order 256 and 384

Archived at Zenodo: [10.5281/zenodo.22785373](https://doi.org/10.5281/zenodo.22785373)
(all versions: [10.5281/zenodo.22785372](https://doi.org/10.5281/zenodo.22785372)).

This deposit gives an explicit terrace for **every one of the 76,224 non-abelian
groups of order 256 and 384** — 56,070 of order 256 and 20,154 of order 384 —
in 76,325 witness records (101 groups of order 384 have two). It also ships a
small standalone program that checks each record. Checking is the point: nothing
here asks you to trust how the terraces were found.

```sh
sh run_all.sh          # four checks, a few hours, Python 3 and nothing else
sh run_all.sh quick    # order 256 only
```

No GAP, no network, no installation, no third-party packages. One further check,
tying each record to the group its id names in GAP's library, needs GAP; see
[What you still have to trust](#what-you-still-have-to-trust). Both checks were
run on exactly these files, and their logs ship here: see
[Verification logs](#verification-logs).

## What a terrace is

Let `G` be a finite group of order `n` with identity `e`. Order all `n`
elements as `a_1, ..., a_n` with `a_1 = e`, and form the `n-1` **differences**

    b_i = (a_i)^-1 * a_{i+1}

The ordering is a **terrace** when every element that is its own inverse (other
than `e`) occurs **exactly once** among the differences, and every other element
`g` occurs **together with its inverse** `g^-1` **exactly twice in total** —
`g` twice, `g^-1` twice, or one each; only the combined count is fixed.

**Bailey's conjecture**, as stated in Ollis's survey (below, Conjecture 33), is
that every finite group is terraced except the elementary abelian 2-groups of
order at least 4. For abelian groups this is settled (the survey's Theorem 31:
an abelian group is terraced if and only if it is not a non-cyclic elementary
abelian 2-group), so what remains open is the non-abelian groups. Abelian
groups are outside this deposit — except that one of the exceptions,
`C_2^8 = SmallGroup(256, 56092)`, appears among the negative controls precisely
because it provably has no terrace.

## What this establishes, and what it does not

**It establishes** that every non-abelian group of order 256 and of order 384
has a terrace, by exhibiting one for each and letting you check it:

| order | groups in GAP's library | abelian (outside the question) | covered here |
|---|---|---|---|
| 256 | 56,092 | 22 | **56,070** |
| 384 | 20,169 | 15 | **20,154** |

Theorem 32(vi) of M. A. Ollis's dynamic survey *Sequenceable Groups and Related
Topics* (Electronic Journal of Combinatorics, Dynamic Survey DS10, Version 3,
published 14 February 2025) states that all non-abelian groups of order up to
511 are terraced **except possibly those of order 256 and 384**, citing
B. A. Anderson, *Bailey's conjecture holds through 87 except possibly for 64*,
J. Combin. Math. Combin. Comput. 12 (1992) 187–195, and M. A. Ollis, *Terraces
for small groups*, J. Combin. Math. Comput. 108 (2019) 231–244. **Combined with
that result**, every non-abelian group of order at most 511 is terraced. The
deposit itself proves only the two orders; the other orders rest on the survey
and the work it cites.

## The four checks in `run_all.sh`

The script stops at the first check that does not come out exactly as expected.
A crash, a truncated file or a wrong count is a failure, never a pass.

0. **The files are the published ones.** `SHA256SUMS` over every file.
1. **Every record is a terrace of a genuine group.** `verify_terrace.py` over
   every file in `data/`. It is one file of plain Python — standard library only,
   nothing imported from the project that produced the data. For each record it
   first decodes the record strictly (no unknown or duplicate keys, canonical
   base64, exact byte lengths), then proves the data describes a group of the
   stated order: the generators must be permutations of the element indices, and
   the permutation group they generate must have exactly `n` elements and move
   index 0 to `n` different places. That makes it a genuine group of order `n`
   acting on itself, so every product computed afterwards is a real group
   product. Only then does it apply the definition above literally. Expect
   `76325 / 76325 PASS`.
2. **The checker can fail.** The same verifier over
   `data/negative_controls.jsonl.gz`: nine records that are wrong on purpose.
   Six take real groups of order 256 and break the ordering — a swapped pair, a
   repeated element, a wrong starting element, a valid terrace checked against
   the wrong group, a transposed tail, and `C_2^8`, which has no terrace at all.
   Three break the group data instead — a non-associative operation, generators
   that are not permutations, and more generators than relative orders — and
   each of those three would pass a checker that only tallied differences.
   Expect `0 / 9 PASS`. `negative_controls_log.txt` gives each one's reason.
3. **Every non-abelian id is present.** `scripts/coverage_check.py` checks that
   every record is well-formed for its order (order field, id in
   `1..NrSmallGroups(n)`, relative orders consistent), that every record's group
   is non-abelian (from its own generators), that ids shipped twice carry
   identical group data, and that no generator data appears under two different
   ids. It then counts the distinct ids and compares against `NrSmallGroups(n)`
   minus the number of abelian groups of order `n`, which it recomputes from the
   partition function: 22 for `2^8`, 15 for `2^7 * 3`.

   This shows every non-abelian **id** is present. That it means every
   non-abelian **group** is covered also needs each record's id to be the group
   its data describes: a different presentation of an already-shipped group
   under another id would pass these four checks. That is what the GAP check
   below rules out.

## What you still have to trust

**That each record's label is right — unless you run the GAP check.** The four
checks prove that each record is a genuine non-abelian group of the stated order
with a terrace, and that every non-abelian id in `1..NrSmallGroups(n)` has a
record. They cannot prove that the record labelled `SmallGroup(384, 3)` is GAP's
group number 3: that is a fact about GAP's library, and plain Python cannot see
it. If a label were wrong, some group could be missing while every count still
came out right.

The labels were attached when each group was exported from GAP, by calling
`SmallGroup(n, i)` and writing its generators next to `i`. Check them yourself
with GAP 4 (the SmallGrp package is part of every standard installation):

```sh
python3 scripts/export_for_gap.py     # writes gap_input/, about 630 MB
gap -q scripts/check_ids.g
```

For every record, `scripts/check_ids.g` builds the permutation group its
generators generate, and checks that the group has order `n` and that
`IdGroup` of it is `[n, id]`. It prints one line per data file and ends with
`IDS: PASS` or `IDS: FAIL`. `ids_check_log.txt` records these two commands run
on this release (see below for its runtime).

**GAP's library itself**, for the list of groups of each order. The only numbers
taken from it are `NrSmallGroups(256) = 56,092` and `NrSmallGroups(384) = 20,169`.

## Verification logs

Two logs record the checks run on exactly the files in this release. Each starts
with the SHA-256 of every code and data file it used, so you can compare them
with `SHA256SUMS`, and then gives each command followed by its complete,
unedited output.

- `verification_log.txt`: `sh run_all.sh` (all four checks, both orders).
- `ids_check_log.txt`: the two GAP commands above; then, as a control, the same
  check on a copy of two exported records relabelled with a neighbouring id,
  which must fail and name the true ids.

They are a record, not a substitute: running the commands yourself is the check.

## The data format

One JSON object per line, gzipped. Each record is one group and one ordering:

| field | meaning |
|---|---|
| `id` | the group is `SmallGroup(order, id)` in GAP's Small Groups library |
| `order`, `k`, `rel` | order `n`; `k` generators; `rel[i]` is generator `i`'s relative order in the polycyclic generating sequence the generators come from (not, in general, the order of generator `i`); the `rel[i]` multiply to `n` |
| `gens_perm_b64` | the `k` generator permutations: `gens_perm[i][x]` is the index of `x * g_i` |
| `witness_b64` | the terrace: all `n` element indices in order, starting with index 0 |
| `width` | bytes per packed integer: 1 at order 256, 2 at order 384 |
| `source` | which search run produced the record (see the glossary) |

Element indices are labels `0..n-1`, fixed per group, with `0` the identity.
`gens_perm_b64` and `witness_b64` are base64 of those integers packed
little-endian, `width` bytes each; `verify_terrace.py`'s docstring explains the
encoding in full. Because the generators generate the group, their permutations
determine every product. A full multiplication table for one group of order 384
would take about 295 KB (384 × 384 entries of 2 bytes); a shipped record takes
about 1.7 KB compressed.

## Glossary

- **direct search** (in `source`): the terrace was found by a computer search in
  that group itself, not derived from a construction.
- **checked by two independent programs** (in `source`): before the witness was
  kept, two separately written checkers accepted it, one working from the
  group's multiplication table and one from its polycyclic presentation (see
  below). `verify_terrace.py` is a third.
- **batch**, **follow-up batch**, **earlier run** (in `source`): which search run
  the record came from, with its dates where recorded. They carry no
  mathematical meaning.
- **`order*_terraces.jsonl.gz`** and **`order*_certs_shard*.jsonl.gz`**: the
  names are historical. The `terraces` files come from the first search
  campaign; the `certs_shard` files from a later one, over groups that an earlier
  version of this work had covered only by a construction certificate rather
  than an explicit ordering. In this deposit every record in every file is an
  explicit terrace in the same format, checked the same way.
- **(also terraced by a published theorem)** (in `source`, three records):
  SmallGroup(256, 539), (256, 540) and (256, 541). By invariants computed from
  their shipped generators (number of involutions, largest element order, centre)
  these are the dihedral, semidihedral and generalised quaternion groups of
  order 256. The first two are terraced by Theorem 3 of M. A. Ollis and
  D. T. Willmott, *An extension theorem for terraces*, Electron. J. Combin. 20
  (2013) #P34, as is the modular group M_256, which is SmallGroup(256, 538) and
  carries no such note. The generalised quaternion group has a symmetric
  sequencing by B. A. Anderson and E. C. Ihrig (DS10 Theorem 10) and so is
  terraced by DS10 Theorem 32(i). None of these theorems is used by this
  deposit: all four records are explicit witnesses checked like every other.

## How the terraces were found

By direct search, group by group. The search is not part of the claim — that is
why this deposit ships the answers and the checker rather than the search — but
two things about it are worth stating.

**Each search run first had to reproduce known answers.** Ten groups whose
terraces were already known were re-solved from scratch with the stored answer
hidden, and the two groups that provably have no terrace
(`C_2^8 = SmallGroup(256, 56092)` and `C_2^7 = SmallGroup(128, 2328)`) were given
the same time limit. A run's output counted only if it solved 10 out of 10 and
0 out of 2.

**Each witness was checked twice before it was kept**, by two separately written
programs working from different representations of the same group exported
from GAP — a multiplication table and a polycyclic presentation — plus a check
that the ordering is a permutation of all `n` elements. `verify_terrace.py` is a
third implementation of the same arithmetic. All three were written within one
project and all three rely on the same export from GAP, so they are independent
as arithmetic, not as provenance; the GAP check above is what connects the
export back to GAP's library.

`PROVENANCE.csv` lists every data file with its record count, size, SHA-256 and
the runs that produced its records, and marks the three order-384 files that
were repacked from an equivalent older encoding by
`scripts/canonicalize_gens_schema.py`. That script checks its own repacking is
consistent; what vouches for the repacked records is that they were verified and
id-checked like every other record.

## Reuse

Everything here — data, code, logs and documentation — is released under CC0 1.0
(public domain dedication). See `LICENSE.txt`. Citation is not required but is
appreciated; `CITATION.cff` has the citation metadata.
