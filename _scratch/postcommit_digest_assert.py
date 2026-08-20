import sys
sys.path.insert(0, "src")
from stockedge100.reporting.stage_package import repo_state

EXPECTED = "30cadd00c89fc09cbbcd37ae98ec69546c5992a652f3556e29d07a5a2d2d94a2"
files, d = repo_state()
print("files   :", len(files))
print("digest  :", d)
print("expected:", EXPECTED)
assert d == EXPECTED, "DIGEST MOVED: %s" % d
print("OK - repo_state_id unchanged after commit 0027d94")
