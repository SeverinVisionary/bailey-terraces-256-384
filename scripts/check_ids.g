# check_ids.g -- the one check that needs GAP.
#
# verify_terrace.py proves each record describes a genuine group of the stated
# order and that the witness is a terrace of it. coverage_check.py proves the
# records are as many distinct non-abelian groups as exist. Neither can prove
# that the record labelled SmallGroup(n, i) is GAP's group number i: that is a
# fact about GAP's library. This script checks it, record by record:
#
#     G := Group(generator permutations);   Size(G) = n;   IdGroup(G) = [n, i]
#
# The generators act on the element indices by right multiplication, a regular
# action, so the permutation group they generate is isomorphic to the group the
# record describes, and IdGroup identifies it.
#
# Usage, from the package root:
#     python3 scripts/export_for_gap.py
#     gap -q scripts/check_ids.g
# Needs GAP 4 with the SmallGrp package (standard in every GAP distribution).
# Prints one line per data file and a final verdict; exits 0 only if every
# record's IdGroup matches its label.

#
# To check another directory of exported files (for instance a control set, or
# one file at a time in parallel), set GAP_INPUT_DIR first:
#     echo 'GAP_INPUT_DIR := "some_dir"; Read("scripts/check_ids.g");' | gap -q

Print("GAP ", GAPInfo.Version, "\n");
if not IsBound(GAP_INPUT_DIR) then GAP_INPUT_DIR := "gap_input"; fi;
bad := [];;
total := 0;;
files := Filtered(DirectoryContents(GAP_INPUT_DIR), f -> EndsWith(f, ".g"));;
Sort(files);;
for f in files do
    RECORDS := fail;;
    Read(Filename(Directory(GAP_INPUT_DIR), f));;
    nbad := 0;;
    for r in RECORDS do
        n := r[1];; id := r[2];;
        G := Group(List(r[3], PermList));;
        if Size(G) <> n then
            Add(bad, [f, id, "size", Size(G)]);; nbad := nbad + 1;;
        elif IdGroup(G) <> [n, id] then
            Add(bad, [f, id, "IdGroup", IdGroup(G)]);; nbad := nbad + 1;;
        fi;
        total := total + 1;;
    od;
    Print(f, ": ", Length(RECORDS), " records, ", nbad, " mismatches\n");
od;
Print("\n", total, " records checked, ", Length(bad), " mismatches\n");
if Length(bad) > 0 then
    Print("first mismatches: ", bad{[1 .. Minimum(10, Length(bad))]}, "\n");
    Print("IDS: FAIL\n");
    QuitGap(1);
fi;
Print("IDS: PASS -- every record is the SmallGroup its id names\n");
QuitGap(0);
