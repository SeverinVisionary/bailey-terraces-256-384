#!/bin/sh
# Re-check this package from scratch. Plain POSIX sh + Python 3 (standard
# library only). No GAP, no network, no installation. Expect a few hours:
# it re-checks 76,325 witness records one element at a time.
#
#   sh run_all.sh            everything below
#   sh run_all.sh quick      the same checks on order 256 only
#
# FOUR CHECKS, and what each would catch:
#
#   0. THE FILES ARE THE ONES PUBLISHED. SHA256SUMS over every file.
#
#   1. EVERY WITNESS IS A TERRACE OF A GENUINE GROUP. verify_terrace.py over
#      every data/order*_*.jsonl.gz. For each record it first proves the data
#      describes a group of the stated order (generators are permutations that
#      generate a regular permutation group of exactly that order), then checks
#      the ordering against the definition. Expect every record PASS, and the
#      exact total below.
#
#   2. THE CHECKER CAN FAIL. The same verifier over
#      data/negative_controls.jsonl.gz: nine orderings or group data that are
#      deliberately wrong. A checker that passes everything proves nothing.
#      Expect all nine FAIL.
#
#   3. EVERY NON-ABELIAN ID IS PRESENT. scripts/coverage_check.py. Expect
#      COVERAGE: PASS. That this means every non-abelian GROUP is covered also
#      needs each record's id to be the group its data describes; that is a fact
#      about GAP's library, checked by scripts/check_ids.g in GAP (README.md).
#
# The script stops at the first check that does not come out exactly as
# expected, and exits non-zero. It never reports a pass it did not observe:
# a crash, a truncated file or a wrong count is a failure.

set -eu
cd "$(dirname "$0")"
PY=${PYTHON:-python3}
MODE=${1:-full}
EXPECT_NEGATIVE=9

case "$MODE" in
    full|quick) ;;
    *) echo "usage: sh run_all.sh [quick]   (unknown mode '$MODE')"; exit 2 ;;
esac

fail() { echo "$1"; echo "STOPPED: not all checks passed."; exit 1; }

echo "=== 0/3  checksums ==="
if command -v sha256sum >/dev/null 2>&1; then
    sha256sum -c --quiet SHA256SUMS || fail "CHECK 0: FAIL -- a file differs from SHA256SUMS"
else
    shasum -a 256 -c --quiet SHA256SUMS || fail "CHECK 0: FAIL -- a file differs from SHA256SUMS"
fi
echo "CHECK 0: PASS"

if [ "$MODE" = "quick" ]; then
    set -- data/order256_*.jsonl.gz
    EXPECT_POSITIVE=56070
else
    set -- data/order256_*.jsonl.gz data/order384_*.jsonl.gz
    EXPECT_POSITIVE=76325
fi

echo
echo "=== 1/3  verifying every shipped witness (this is the long one) ==="
if "$PY" verify_terrace.py "$@" > check1_witnesses.txt; then status=0; else status=$?; fi
tail -n 1 check1_witnesses.txt
[ "$status" -eq 0 ] || fail "CHECK 1: FAIL -- verifier exit status $status; see check1_witnesses.txt"
[ "$(tail -n 1 check1_witnesses.txt)" = "$EXPECT_POSITIVE / $EXPECT_POSITIVE PASS" ] \
    || fail "CHECK 1: FAIL -- expected exactly '$EXPECT_POSITIVE / $EXPECT_POSITIVE PASS'"
echo "CHECK 1: PASS"

echo
echo "=== 2/3  the verifier must reject every negative control ==="
if "$PY" verify_terrace.py data/negative_controls.jsonl.gz > check2_negative.txt; then status=0; else status=$?; fi
tail -n 1 check2_negative.txt
[ "$status" -eq 1 ] || fail "CHECK 2: FAIL -- expected exit status 1 (some records rejected), got $status"
[ "$(tail -n 1 check2_negative.txt)" = "0 / $EXPECT_NEGATIVE PASS" ] \
    || fail "CHECK 2: FAIL -- expected exactly '0 / $EXPECT_NEGATIVE PASS'"
[ "$(grep -c '^FAIL' check2_negative.txt)" -eq "$EXPECT_NEGATIVE" ] \
    || fail "CHECK 2: FAIL -- expected $EXPECT_NEGATIVE FAIL lines"
echo "CHECK 2: PASS (all $EXPECT_NEGATIVE rejected; reasons in check2_negative.txt)"

echo
echo "=== 3/3  coverage ==="
if [ "$MODE" = "quick" ]; then ORDERS=256; else ORDERS="256 384"; fi
# shellcheck disable=SC2086
if "$PY" scripts/coverage_check.py data $ORDERS > check3_coverage.txt; then status=0; else status=$?; fi
cat check3_coverage.txt
[ "$status" -eq 0 ] || fail "CHECK 3: FAIL -- coverage exit status $status"
[ "$(tail -n 1 check3_coverage.txt)" = "COVERAGE: PASS" ] || fail "CHECK 3: FAIL"
echo "CHECK 3: PASS"

echo
echo "ALL CHECKS PASSED."
echo "(The id labels are checked separately, in GAP: see README.md, 'What you still have to trust'.)"
