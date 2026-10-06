# %%
from bitarray import bitarray, frozenbitarray
from bitarray.util import int2ba, ba2int
L = 4 # int L (unsigned)


# helper functions
def to_bits(v : int, length : int, signed = False) -> frozenbitarray:
    # transform an int64 to an inmutable bitarray of length L
    return frozenbitarray(int2ba(v, length=length, signed = signed, endian='big'))

def from_bits(ba : bitarray, signed = False) -> int:
    # from frozenbitarray back to int
    return ba2int(ba, signed = signed)

class VNode:

    def __init__(self, lo, hi, left = None, right = None):
        # a vtree node that covers the bits in [lo, hi)
        self.lo = lo
        self.hi = hi
        # whose left right children are left and right
        self.left = left
        self.right = right
        # where mid = (hi + lo // 2) 
        # left covers [lo, mid) and right covers [mid, hi)

    def is_leaf(self) -> bool:
        return (not self.left) and (not self.right)

# a recursive function to build a vtree of int L covering bits of [lo, hi)
def build_vtree(lo, hi):
    # base case (a leaf)
    if hi - lo < 2:
        return VNode(lo, hi)

    # recursion
    mid = (lo + hi) // 2
    return VNode(lo, hi, left = build_vtree(lo, mid), right = build_vtree(mid, hi))


# a post-order traversal from bottom up, given the root of a vtree
def bottom_up(node) -> list:

    # base case (none node)
    if node.is_leaf():
        return [node]

    # post-order traversal
    return bottom_up(node.left) + bottom_up(node.right) + [node]

# TDD: X_t-subfunction
def group(v : VNode, vals : set[frozenbitarray]) -> list:
    # given a vtree node v covering [v.lo, v.hi) 
    # and a set of values as frozenbitarrays
    # return a list of value-groups (within each group, inside bits have the same SET of outside bits)
    # inside bits are b[v.lo : v.hi]
    # outside bits are b[ : t.lo] + b[t.hi : ]
    
    in2outs = {} # inside_bit -> {outside_bits} set
    for b in vals:
        in_b = b[v.lo : v.hi]
        out_b = b[ : v.lo] + b[v.hi : ]
        
        if in_b in in2outs:
            in2outs[in_b].add(out_b)
        else:
            in2outs[in_b] = set([out_b])

    outs2in = {} # {outside_bits} set -> {inside_bits} set
    # !! set is not hashable, but frozenset is!!
    for in_b, out_set in in2outs.items():
        out_set = frozenset(out_set) # freeze it to hash

        if out_set in outs2in:
            outs2in[out_set].add(in_b)
        else:
            outs2in[out_set] = set([in_b])

    # return the indistinguishable inside bits
    res = []
    for _, in_set in outs2in.items():
        res.append(list(in_set))

    # cosmetic sorting to read easily
    # list of inside chunk groups
    return sorted(sorted(g) for g in res)

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
class TDD:

    def __init__(self, values, length, signed = False):
        # n values
        self.signed = signed
        self.L = length
        self.vtree = build_vtree(0, length)
        self.nodes = {} # maps each vtree node to a TDD node
        bits = set(to_bits(v, length, self.signed) for v in values)
        node_of = {}    # local : maps an inside chunk of a vtree node t
                        # to the index of this group i
                        # i is later TDD node i at t

        # bottom-up DP to compile a vtree
        for t in bottom_up(self.vtree): # O (2L) vtree nodes
            groups = group(t, bits)
            node_of[t] = {} # given a vtree node t
                            # maps an inside chunk c to its group idx
            self.nodes[t] = []
            for idx, g in enumerate(groups):
                for c in g:
                    node_of[t][c] = idx

                # make each group into a TDD node == set of its inputs
                # leaf
                if t.hi - t.lo < 2:
                    # each group contains single-bit inside chunks
                    self.nodes[t].append(set(c[0] for c in g))

                    continue

                # internal, otherwise
                # [t.lo, t.hi) = [t.left.lo, t.left.hi) \cup [t.right.lo, t.right.hi)
                # mid = t.left.hi
                mid = (t.lo + t.hi) // 2
                k = mid - t.lo # the number of bits under its left child
                self.nodes[t].append(
                    set((node_of[t.left][c[ : k]], node_of[t.right][c[k : ]]) for c in g)
                    )
                # bottom-up DP guarantees children being visited before parent


        self._build_up()


    def _build_up(self):        
        # build the reverse lookup from a value x to a TDD node i at vtree node v
        self.up = {}    # one dict per vtree node self.up[t] = {}
                        # self.up[t][v]
                        # maps an input x to the index of the TDD node it belongs to

        for t in bottom_up(self.vtree):
            self.up[t] = {}
            # a vtree node -> LIST of TDD nodes
            # self.nodes[t]: list of the TDD nodes at vtree node t
            # its TDD node i is self.nodes[t][i] (each pair above / one level refers to it by i)
            # 
            # a TDD node -> the set of its inputs
            #   leaf:     bit values, {0}, {1} or {0, 1}
            #   internal: pairs (a, b) = self.nodes[t.left][a] and self.nodes[t.right][b]
            # built from one group: inside chunks that share the same SET of outside chunks
            for idx, node in enumerate(self.nodes[t]):
                # each input of a TDD node
                for x in node:
                    assert(x not in self.up[t])
                    self.up[t][x] = idx


    # return the index of TDD node at vtree node t that chunk of b matches
    def _find(self, t : VNode, b : frozenbitarray) -> int | None:
        # leaf
        if t.hi - t.lo < 2:
            return self.up[t].get(b[t.lo]) # None if no key otherwise int val

        # internal
        return self.up[t].get((self._find(t.left, b), self._find(t.right, b)))

    # membership check if v in tdd
    def __contains__(self, v : int):
        # sanity check
        if (not self.signed) and (not 0 <= v < 2 ** (self.L)):
            return False

        if self.signed and (not -2 ** (self.L - 1) <= v < 2 ** (self.L - 1)):
                return False

        #
        return self._find(self.vtree, to_bits(v, self.L, self.signed)) is not None

    # model count
    def __len__(self) -> int:
        count = {} # vtree node t -> (TDD node n -> int count of models)
        # bottom-up DP
        for t in bottom_up(self.vtree):
            count[t] = {}
            # leaf
            if t.hi - t.lo < 2:
                for idx, node in enumerate(self.nodes[t]):
                    count[t][idx] = len(node)
                
                continue

            # internal
            for idx, node in enumerate(self.nodes[t]):
                count[t][idx] = 0
                for a, b in node:
                    # combinatorial of models of either child
                    count[t][idx] += \
                        count[t.left][a] *\
                        count[t.right][b]

        if len(count[self.vtree]) < 1:
            return 0

        return count[self.vtree].get(0)

    # list the values with __iter__
    # the opposite of the model counts above
    # instead of multiplying them, generate the inside chunks
    # with a recursive generator
    def _models(self, t : VNode, i : int):
        # leaf
        if t.hi - t.lo < 2:
            for bit in self.nodes[t][i]:
                # wrap the single-bit array with frozenbitarray
                yield frozenbitarray([bit])
            
            return

        # internal
        for (a, b) in self.nodes[t][i]:
            for l_chunk in self._models(t.left, a):
                for r_chunk in self._models(t.right, b):
                    # the concatenation of 2 frozenbitarrays is still frozen
                    yield l_chunk + r_chunk

    # lazy enumeration
    def __iter__(self):
        for i in range(len(self.nodes[self.vtree])):
            for chunk in self._models(self.vtree, i):
                yield from_bits(chunk, signed = self.signed)


    # proposition 28 given the same vtree, compute TDD1 a \and TDD2 b
    def __and__(self, other : "TDD") -> "TDD":
        assert (self.L == other.L) # making sure lengths / vtrees match
        assert (self.signed == other.signed)

        r = TDD([], self.L, self.signed) # an empty TDD to hold the res
        idx = {} # maps a product (i, j) to the idx of TDD node in r.nodes[t], like node_of above
        # i, j are the TDD nodes of a and b respectively

        # bottom-up walk 3 trees together
        for t, ta, tb in\
             zip(bottom_up(r.vtree), bottom_up(self.vtree), bottom_up(other.vtree)):
            # vtrees are structurally the same, but each VNode
            # serves as a key for looking up its TDD node
            r.nodes[t] = []
            idx[t] = {}
            for i, ga in enumerate(self.nodes[ta]):
                for j, gb in enumerate(other.nodes[tb]):
                    # i, j are idx 
                    # ga, gb are the inside chunks (sets)
                    node = set() # build the local node (set) first, before deciding whether to keep
                                # TDD node

                    # leaf
                    if t.hi - t.lo < 2:
                        # ga, gb \in {{0}, {1}, {0, 1}}
                        node = ga & gb # python & does the set intersection

                    # internal
                    else:
                        # a TDD node in each tree is a tuple
                        # pointing to its left and right child TDD nodes
                        for al, ar in ga:
                            for bl, br in gb:    
                            # check if the combination is valid 
                            # against the new tree's children
                            # if either is missing => skip
                                if(not (al, bl) in idx[t.left]) or\
                                (not (ar, br) in idx[t.right]):
                                    continue

                                # both valid
                                # combine left with left, right with right
                                node.add((
                                    idx[t.left][al, bl],\
                                    idx[t.right][ar, br]
                                    ))

                    # keep ONLY non-empty nodes
                    if not len(node):
                        continue

                    idx[t][(i, j)] = len(r.nodes[t]) # the idx for (i, j) pair
                    r.nodes[t].append(node) # append TDD 'node' to the corresponding VNode t

        # build the reverse lookup
        r._build_up()

        return r


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

# %%
