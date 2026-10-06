# %%
from tdd import *

L = 4 # int L (unsigned)

# %% testing block
root = build_vtree(0, L)
S = [0, 1, 4, 5, 10, 11]
n_list = bottom_up(root)

S_set = set(to_bits(s, L) for s in S)

for n in n_list:
    print((n.lo, n.hi), sorted([sorted(c.to01() for c in g) for g in group(n, S_set)]))
    if n.hi - n.lo == L:
        print((n.lo, n.hi), sorted([sorted(from_bits(c) for c in g) for g in group(n, S_set)]))


# %%
d = TDD(range(-8, 8), 4, signed=True)
print(len(d), sorted(d) == list(range(-8, 8)))      # 16 True
d = TDD([-8, -1, 0, 7], 4, signed=True)
print(sorted(d), 8 in d, -9 in d, -8 in d)          # [-8, -1, 0, 7] False False True
print(sorted(TDD([0, 1, 4, 5, 10, 11], 4)))         # [0, 1, 4, 5, 10, 11]  (unsigned still works)

E = [-2**63, -1, 0, 1, 2**63 - 1]
d = TDD(E, 64, signed = True)
print(sorted(d) == E, 2**63 in d, -2**63 - 1 in d)  # True False False

import random
S = [random.randint(-2**63, 2**63 - 1) for _ in range(2000)] + list(range(-50, 50))
d, s = TDD(S, 64, signed = True), set(S)
assert sorted(d) == sorted(s) and len(d) == len(s)
assert all((v in d) == (v in s) for v in (random.randint(-2**63, 2**63 - 1) for _ in range(2000)))

# %%
A = TDD([0, 1, 4, 5, 10, 11], 4)
B = TDD([1, 2, 3, 4, 5, 6, 7], 4)
C = A & B
print(sorted(C), len(C))              # [1, 4, 5] 3
print(sorted(A & TDD([], 4)))         # []
for t in bottom_up(C.vtree):
    print((t.lo, t.hi), [sorted(g) for g in C.nodes[t]])
# Notice node #2 at (2,4), which is 1x: the root never uses it. 
# It's a correct product (A's 1x and B's 1x do have models in common),
# but no value in A ∩ B reaches it. 
# TDD([1, 4, 5], 4) doesn't have it. 
# So the result is correct but not minimal. 
# Membership, len and listing still work, because they only need determinism.

# %% long-running
import random
L = 16
SA = [random.randint(-2**15, 2**15 - 1) for _ in range(800)]
SB = [random.randint(-2**15, 2**15 - 1) for _ in range(800)] + SA[:100]
C = TDD(SA, L, signed=True) & TDD(SB, L, signed=True)
s = set(SA) & set(SB)
assert sorted(C) == sorted(s) and len(C) == len(s)

A = TDD(range(-1000, 1000), 64, signed=True)
B = TDD(range(0, 2**20, 3), 64, signed=True)
C = A & B
print(len(C))   # 334: the multiples of 3 in [0, 1000)

# %%