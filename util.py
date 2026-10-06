"""Step-by-step text views of tdd.py, meant for small examples (L up to about 8).

Each view runs your code in tdd.py (group, _find, _models, len, in, &), so breakpoints
set there are hit. What your functions don't return, like in2outs or the per-node counts,
is recomputed here and checked against your results (✓ / ✗). In the interactive window:

    from util import *        # also brings in TDD, group, bottom_up, ... from tdd.py
    A = TDD([0, 1, 4, 5, 10, 11], 4)
    show_vtree(A)             # build_vtree: the bits each vtree node covers
    show_group(A, (0, 2))     # group: inside chunk -> set of outsides -> TDD node
    show_build(A)             # TDD.__init__: every group becomes one TDD node
    show_tdd(A)               # the result: what every TDD node and every pair stands for
    show_find(A, 6)           # _find and __contains__ for one value
    show_count(A)             # __len__: the model count
    show_and(A, TDD([1, 2, 3, 4, 5, 6, 7], 4))    # __and__: the product construction
    explore()                 # all of the above, with widgets to change the inputs

Values are shown as bit strings such as '0110' (to_bits(...).to01()), MSB first.
After editing tdd.py, restart the kernel, or run `%load_ext autoreload` and
`%autoreload 2` once beforehand, so that these views use the new code.
"""

from tdd import TDD, build_vtree, bottom_up, group, to_bits

LIMIT = 8   # longer sets and lists are cut short when printed


# ---------- helpers ----------

def bits(tdd, v):
    """v as a bit string such as '0110', made by your to_bits."""
    return to_bits(v, tdd.L, tdd.signed).to01()


def chunks(tdd, t, i):
    """The chunks (bit strings of t's own bits) that TDD node i at t stands for, from your _models."""
    return {c.to01() for c in tdd._models(t, i)}


def value_range(L, signed):
    """The values an L-bit TDD can hold: lo <= v < hi."""
    return (-2 ** (L - 1), 2 ** (L - 1)) if signed else (0, 2 ** L)


def ints(text):
    """'0 1, 4 -5' -> [0, 1, 4, -5]; anything that is not a whole number is skipped."""
    return [int(x) for x in text.replace(",", " ").split() if x.removeprefix("-").isdigit()]


def vnode(tdd, lo_hi):
    """The vtree node of tdd that covers the bits [lo, hi), or None if there is none."""
    for t in bottom_up(tdd.vtree):
        if (t.lo, t.hi) == tuple(lo_hi):
            return t


def size(tdd):
    """Number of TDD nodes, over all vtree nodes."""
    return sum(len(tdd.nodes[t]) for t in bottom_up(tdd.vtree))


def width(tdd):
    """The largest number of TDD nodes at one vtree node (the paper's k)."""
    return max(len(tdd.nodes[t]) for t in bottom_up(tdd.vtree))


def name(t):
    """A vtree node's name, e.g. (0,2)."""
    return f"({t.lo},{t.hi})"


def span(t):
    """The bit positions a vtree node covers, e.g. 'bit 3' or 'bits 0..1'."""
    return f"bit {t.lo}" if t.is_leaf() else f"bits {t.lo}..{t.hi - 1}"


def fmt(items):
    """A set as {a, b, c}: sorted, cut short after LIMIT items, and ∅ when empty."""
    items = sorted(items)
    if not items:
        return "∅"
    more = f", … {len(items) - LIMIT} more" if len(items) > LIMIT else ""
    return "{" + ", ".join(str(x) for x in items[:LIMIT]) + more + "}"


def ref(k):
    """A TDD node index for printing; None means no TDD node matched."""
    return "none" if k is None else f"#{k}"


def mark(s, t):
    """Bit string s with vtree node t's own bits in brackets, e.g. 0[11]0 for t = (1,3)."""
    return s[:t.lo] + "[" + s[t.lo:t.hi] + "]" + s[t.hi:]


def outside(s, t):
    """Bit string s with t's own bits blanked out by _: the part of the value t does not see."""
    return s[:t.lo] + "_" * (t.hi - t.lo) + s[t.hi:]


def draw(t, text, first="", rest=""):
    """Print the vtree from t down, root first, with the lines text[t] under each vtree node."""
    print(first + text[t][0])
    for line in text[t][1:]:
        print(rest + ("    " if t.is_leaf() else "│   ") + line)
    if not t.is_leaf():
        draw(t.left, text, rest + "├── ", rest + "│   ")
        draw(t.right, text, rest + "└── ", rest + "    ")


# ---------- one view per step of tdd.py ----------

def show_vtree(x):
    """build_vtree: vtree node (lo,hi) covers bit positions lo .. hi-1; position 0 is the MSB.
    Pass L, a TDD, or the root that build_vtree(0, L) returns."""
    root = build_vtree(0, x) if isinstance(x, int) else getattr(x, "vtree", x)
    text = {}
    for t in bottom_up(root):
        if t.is_leaf():
            text[t] = [f"{name(t)}  leaf: {span(t)}"]
        else:
            text[t] = [f"{name(t)}  {span(t)} = left {name(t.left)} + right {name(t.right)}"]
    draw(root, text)
    print("\nbottom_up order:", " ".join(name(t) for t in bottom_up(root)))
    print("The vtree depends only on L. The values decide which TDD nodes live on each vtree node.")


def show_group(tdd, lo_hi):
    """group(t, values) at the vtree node t that covers [lo, hi), e.g. show_group(A, (0, 2))."""
    t = vnode(tdd, lo_hi)
    if t is None:
        print(f"{tuple(lo_hi)} is not a vtree node; pick one of", " ".join(name(t) for t in bottom_up(tdd.vtree)))
        return
    print(f"group at {name(t)}: inside = {span(t)}, shown in [ ]; "
          f"outside = all the other bits, with _ where the inside was\n")

    print("1) split every value into its inside chunk and its outside")
    in2outs = {}
    for n, s in enumerate(sorted(bits(tdd, v) for v in tdd)):
        in2outs.setdefault(s[t.lo:t.hi], set()).add(outside(s, t))   # makes the set the first time
        if n < 2 * LIMIT:
            print(f"   {mark(s, t)}   inside {s[t.lo:t.hi]}   outside {outside(s, t)}")
    if len(tdd) > 2 * LIMIT:
        print(f"   … {len(tdd) - 2 * LIMIT} more values")

    print("\n2) in2outs: collect the SET of outsides of each inside chunk")
    for c in sorted(in2outs):
        print(f"   {c} → {fmt(in2outs[c])}")

    print("\n3) your group(): chunks with the same SET of outsides form one group = one TDD node")
    groups = [sorted(c.to01() for c in g) for g in group(t, {to_bits(v, tdd.L, tdd.signed) for v in tdd})]
    w = max((len(fmt(g)) for g in groups), default=0)
    for i, g in enumerate(groups):
        print(f"   #{i} = {fmt(g):<{w}}   all with outsides {fmt(in2outs[g[0]])}")

    outs2in = {}
    for c, outs in in2outs.items():
        outs2in.setdefault(frozenset(outs), set()).add(c)
    expected = sorted(sorted(cs) for cs in outs2in.values())
    print("\n✓ group() matches step 2" if groups == expected else f"\n✗ from step 2, the groups should be {expected}")
    yours = [chunks(tdd, t, i) for i in range(len(tdd.nodes[t]))]
    if yours == [set(g) for g in groups]:
        print(f"✓ tdd.nodes at {name(t)} stand for exactly these groups, in this order")
    else:
        print(f"✗ tdd.nodes at {name(t)} stand for", ", ".join(fmt(cs) for cs in yours),
              "(expected for a TDD made by __and__, which is not minimal)")


def show_build(tdd):
    """TDD.__init__ replayed with your group(): walk the vtree bottom-up; at each vtree node
    every group becomes one TDD node. Use it on a TDD made by the constructor (one made by
    __and__ is not minimal, so it differs)."""
    values = {to_bits(v, tdd.L, tdd.signed) for v in tdd}
    print("values:", " ".join(sorted(b.to01() for b in values)))
    node_of = {}
    for t in bottom_up(tdd.vtree):
        groups = [sorted(c.to01() for c in g) for g in group(t, values)]
        node_of[t] = {c: i for i, g in enumerate(groups) for c in g}
        nodes = []
        if t.is_leaf():
            print(f"\n{name(t)} is a leaf: a TDD node is the set of bits its group allows")
        else:
            k = t.left.hi - t.lo
            print(f"\n{name(t)}: cut each chunk after {k} bit(s) into its {name(t.left)} part | "
                  f"{name(t.right)} part, and look both parts up in node_of")
        for i, g in enumerate(groups):
            if t.is_leaf():
                nodes.append({int(c) for c in g})
                print(f"   group {fmt(g)} → #{i} = {fmt(nodes[-1])}")
                continue
            print(f"   group {fmt(g)}:")
            node = set()
            for n, c in enumerate(g):
                x, y = c[:k], c[k:]
                pair = (node_of[t.left][x], node_of[t.right][y])
                node.add(pair)
                if n < LIMIT:
                    print(f"      {x}|{y} → {pair}   ({x} is #{pair[0]} at {name(t.left)}, "
                          f"{y} is #{pair[1]} at {name(t.right)})")
            if len(g) > LIMIT:
                print(f"      … {len(g) - LIMIT} more chunks")
            nodes.append(node)
            print(f"   → #{i} = {fmt(node)}: {len(g)} chunk(s) became {len(node)} pair(s)")
        print("   ✓ same as tdd.nodes" if nodes == tdd.nodes[t] else f"   ✗ tdd.nodes has {tdd.nodes[t]}")


def show_tdd(tdd):
    """The finished TDD, root first. Under each vtree node: its TDD nodes tdd.nodes[t][i],
    what each pair and each node stands for, and the set of outsides that all of a node's
    chunks share (sharing it is what makes them one node)."""
    values = [bits(tdd, v) for v in tdd]
    text = {}
    for t in bottom_up(tdd.vtree):
        text[t] = [f"{name(t)}  {len(tdd.nodes[t])} TDD node(s)"]
        seen = {}   # outside set -> the first TDD node here that has it
        for i, node in enumerate(tdd.nodes[t]):
            text[t].append(f"#{i} = {fmt(node)}")
            cs = chunks(tdd, t, i)
            if not t.is_leaf():
                for a, b in sorted(node):
                    text[t].append(f"   {(a, b)} = {fmt(chunks(tdd, t.left, a))} × {fmt(chunks(tdd, t.right, b))}")
                text[t].append(f"   stands for {fmt(cs)}")
            outs = frozenset(outside(s, t) for s in values if s[t.lo:t.hi] in cs)
            note = ""
            if not outs:
                note = "   ← unused: no stored value goes through this node"
            elif outs in seen:
                note = f"   ← same outsides as #{seen[outs]}: the two could be merged"
            seen.setdefault(outs, i)
            text[t].append(f"   outsides {fmt(outs)}{note}")
    draw(tdd.vtree, text)


def show_find(tdd, v):
    """__contains__ and _find for one value. Every vtree node reads its own bits [lo, hi) of
    the WHOLE value and looks up one key in tdd.up[t]: its bit at a leaf, the pair of its
    children's answers above. [n] is the order of the lookups: children first."""
    lo, hi = value_range(tdd.L, tdd.signed)
    print(f"v = {v}; this TDD holds values {lo} .. {hi - 1}")
    if not lo <= v < hi:
        print("out of range, so __contains__ returns False without calling _find")
        answer = False
    else:
        b = to_bits(v, tdd.L, tdd.signed)
        print(f"bits {b.to01()}\n")
        found, text = {}, {}
        for n, t in enumerate(bottom_up(tdd.vtree), 1):   # the order in which your _find answers
            found[t] = tdd._find(t, b)                     # your _find, started at vtree node t
            key = b[t.lo] if t.is_leaf() else (found[t.left], found[t.right])
            check = "" if found[t] == tdd.up[t].get(key) else f"   ✗ but tdd.up[t][{key}] is {ref(tdd.up[t].get(key))}"
            text[t] = [f"[{n}] {name(t)}  {mark(b.to01(), t)}  key {key} → {ref(found[t])}{check}"]
        draw(tdd.vtree, text)
        answer = found[tdd.vtree] is not None
        print(f"\nthe root gives {ref(found[tdd.vtree])}, so {v} is {'' if answer else 'NOT '}in the set")
    yours = v in tdd
    print(f"your `{v} in tdd` returns {yours}", "✓" if yours == answer else "✗")


def show_count(tdd):
    """__len__, bottom-up. A leaf node has one model per allowed bit. A pair (a, b) has
    (models of a) × (models of b): any left part with any right part. A node adds up its
    pairs, which never overlap (determinism). Note: inputs are not models."""
    count, text = {}, {}
    for t in bottom_up(tdd.vtree):
        count[t], text[t] = [], [name(t)]
        w = max((len(fmt(node)) for node in tdd.nodes[t]), default=0)
        for i, node in enumerate(tdd.nodes[t]):
            if t.is_leaf():
                count[t].append(len(node))
                how = f"{len(node)}, one per allowed bit"
            else:
                terms = [(count[t.left][a], count[t.right][b]) for a, b in sorted(node)]
                count[t].append(sum(x * y for x, y in terms))
                how = " + ".join(f"{x}×{y}" for x, y in terms[:LIMIT])
                how += (" + …" if len(terms) > LIMIT else "") + f" = {count[t][i]}"
            text[t].append(f"#{i} = {fmt(node):<{w}}   {len(node)} input(s), models: {how}")
    draw(tdd.vtree, text)
    total = sum(count[tdd.vtree])
    print(f"\nmodel count = sum at the root = {total}; your len(tdd) returns {len(tdd)}",
          "✓" if total == len(tdd) else "✗")


def show_and(A, B):
    """__and__, the product construction, bottom-up. The product (i, j) is A's TDD node i
    AND B's TDD node j at the same vtree node. Pairs combine left with left and right with
    right; a product with no models is dropped, and a pair that needs it is skipped."""
    C = A & B   # your result, compared at every vtree node
    idx, tried = {}, 0
    for t, ta, tb in zip(bottom_up(C.vtree), bottom_up(A.vtree), bottom_up(B.vtree)):
        print(f"\n{name(t)}: A has {len(A.nodes[ta])} TDD node(s), B has {len(B.nodes[tb])}")
        idx[t], nodes = {}, []
        for i, ga in enumerate(A.nodes[ta]):
            for j, gb in enumerate(B.nodes[tb]):
                if t.is_leaf():
                    node = ga & gb
                    line = f"   A#{i} {fmt(ga)} & B#{j} {fmt(gb)} = {fmt(node)}"
                else:
                    node = set()
                    print(f"   A#{i} {fmt(ga)}  with  B#{j} {fmt(gb)}")
                    for al, ar in sorted(ga):
                        for bl, br in sorted(gb):
                            tried += 1
                            left = idx[t.left].get((al, bl))
                            right = idx[t.right].get((ar, br))
                            pair = None
                            if left is not None and right is not None:
                                pair = (left, right)
                                node.add(pair)
                            print(f"      A{(al, ar)} & B{(bl, br)}:  "
                                  f"left {name(t.left)} A#{al}&B#{bl} → {ref(left)},  "
                                  f"right {name(t.right)} A#{ar}&B#{br} → {ref(right)}  "
                                  f"⇒ {pair if pair is not None else 'skip'}")
                    line = f"      = {fmt(node)}"
                if node:
                    idx[t][(i, j)] = len(nodes)
                    nodes.append(node)
                    print(f"{line}  → keep as #{idx[t][(i, j)]}")
                else:
                    print(f"{line}  → empty, drop")
        print("   ✓ same as your A & B" if nodes == C.nodes[t] else f"   ✗ your A & B has {C.nodes[t]}")

    print(f"\ntried {tried} pair combinations (at each vtree node: every pair of A with every pair of B)")
    expect = sorted(set(A) & set(B))
    print(f"values of A & B: {sorted(C)}", "✓ = A ∩ B" if sorted(C) == expect else f"✗ A ∩ B = {expect}")
    K = TDD(expect, A.L, A.signed)   # what the constructor builds for the same values
    print(f"A & B has {size(C)} TDD nodes (width {width(C)}); "
          f"the constructor builds {size(K)} TDD nodes (width {width(K)}) for the same values\n")
    show_tdd(C)


def explore():
    """Widgets around the views above, for Jupyter or the VS Code interactive window.
    A and B are the values of two TDDs (B is only used by __and__), v is the value for
    _find, and node is the vtree node for group, e.g. '0 2'."""
    from ipywidgets import interact, IntText

    def run(step="the TDD", A="0 1 4 5 10 11", B="1 2 3 4 5 6 7", L=4, signed=False, v=6, node="0 2"):
        lo, hi = value_range(L, signed)
        if not all(lo <= x < hi for x in ints(A) + ints(B)):
            print(f"every value in A and B must be in {lo} .. {hi - 1} for L = {L}")
            return
        tdd = TDD(ints(A), L, signed)
        if step == "build_vtree":
            show_vtree(tdd)
        elif step == "group":
            show_group(tdd, ints(node))
        elif step == "__init__":
            show_build(tdd)
        elif step == "the TDD":
            show_tdd(tdd)
        elif step == "_find / in":
            show_find(tdd, v)
        elif step == "__len__":
            show_count(tdd)
        elif step == "__and__":
            show_and(tdd, TDD(ints(B), L, signed))

    steps = ["build_vtree", "group", "__init__", "the TDD", "_find / in", "__len__", "__and__"]
    interact(run, step=steps, L=(1, 8), v=IntText(6))
