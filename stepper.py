"""Step through tdd.py node by node in the browser: back / next buttons, the ← → keys, or the slider.

    from stepper import *
    A = TDD([0, 1, 4, 5, 10, 11], 4)
    play_build(A)                                  # TDD.__init__, one group at a time
    play_find(A, 6)                                # _find, one vtree node at a time
    play_count(A)                                  # __len__, one TDD node at a time
    play_and(A, TDD([1, 2, 3, 4, 5, 6, 7], 4))     # __and__, one pair combination at a time

Each call runs your code in tdd.py, records every step, writes them into one HTML page
(in the temp folder, unless you pass path=...), opens it in your browser and returns its
path. Meant for small examples, L up to about 6.
"""

import json
import os
import tempfile
import webbrowser
from html import escape

from tdd import TDD, bottom_up, group, to_bits
from util import LIMIT, bits, fmt, mark, name, outside, ref, size, span, value_range

INTRO_BUILD = ("Bottom-up over the vtree. At each vtree node, your group() puts the inside chunks that "
               "have the same set of outsides together, and each group becomes one TDD node: at a leaf, "
               "the set of bits it allows; above, the set of pairs (left index, right index) its chunks split into.")
INTRO_FIND = ("Each vtree node reads its own bits of the whole value. A leaf looks up its bit; a node above "
              "looks up the pair of its children's answers. Determinism: each lookup finds at most one TDD node.")
INTRO_COUNT = ("Models of a TDD node: at a leaf, one per allowed bit; above, the sum over its pairs (a, b) of "
               "(models of a) × (models of b). Different pairs never share a model, so nothing is counted twice.")
INTRO_AND = ("A TDD node of A & B is a product (i, j): A's TDD node i AND B's TDD node j at the same vtree node. "
             "At a leaf it allows the bits both allow. Above, every pair of A#i meets every pair of B#j, left with "
             "left and right with right; the pair is added only if both child products were kept. "
             "A product with no models is dropped.")

PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>%TITLE%</title>
<style>
  :root { --bg: #fff; --fg: #222; --dim: #777; --line: #aaa; --box: #f2f2f2;
          --focus: #ffe08a; --left: #bfe3ff; --right: #c9f0c4; --done: #e4d8ff; }
  @media (prefers-color-scheme: dark) {
    :root { --bg: #1e1e1e; --fg: #ddd; --dim: #999; --line: #666; --box: #2b2b2b;
            --focus: #7a6420; --left: #1f4f73; --right: #2f5e2a; --done: #4b3a73; }
  }
  body { background: var(--bg); color: var(--fg); font: 14px system-ui, sans-serif; margin: 16px; }
  .values, .caption, .box { font: 12.5px/1.6 ui-monospace, Menlo, monospace; }
  .values { white-space: pre-wrap; }
  .bar { position: sticky; top: 0; z-index: 1; background: var(--bg); padding: 8px 0; display: flex; gap: 10px;
         align-items: center; flex-wrap: wrap; }
  .caption { white-space: pre-wrap; background: var(--box); padding: 8px 12px; margin: 8px 0; }
  .panels { display: flex; gap: 48px; flex-wrap: wrap; align-items: flex-start; }
  h3 { margin: 12px 0 6px; }

  /* a vtree node's box on top, its left and right subtrees side by side below it, joined by lines */
  .vt { display: flex; flex-direction: column; align-items: center; }
  .box { border: 1px solid var(--line); border-radius: 6px; padding: 2px 8px; white-space: nowrap; }
  .box.here { outline: 2px solid var(--fg); }
  .kids { display: flex; position: relative; margin-top: 14px; }
  .kids::before { content: ""; position: absolute; left: 50%; top: -14px; height: 14px; border-left: 1px solid var(--line); }
  .kids > .vt { position: relative; padding: 14px 4px 0; }
  .kids > .vt::before { content: ""; position: absolute; top: 0; height: 14px; border-top: 1px solid var(--line); }
  .kids > .vt:first-child::before { left: 50%; right: 0; border-left: 1px solid var(--line); }
  .kids > .vt:last-child::before { left: 0; right: 50%; border-right: 1px solid var(--line); }

  .head, .note { color: var(--dim); }
  .note { margin-left: 8px; }
  .focus { background: var(--focus); } .left { background: var(--left); } .right { background: var(--right); }
  .done { background: var(--done); } .unused { opacity: 0.5; text-decoration: line-through; }
</style></head>
<body>
<h2>%TITLE%</h2>
<p>%INTRO%</p>
%VALUES%
<div class="values head">binary is MSB first: bit 0 is the leftmost bit, the same positions the vtree uses</div>
<div class="bar">
  <button id="back">◀ back</button> <button id="next">next ▶</button>
  <input id="slider" type="range" min="0" value="0"> <span id="count"></span>
  <span class="focus">working on</span> <span class="left">left child</span>
  <span class="right">right child</span> <span class="done">done</span>
</div>
<div id="frame"></div>
<script>
const frames = %FRAMES%;
const $ = id => document.getElementById(id);
let i = 0;
function show(k) {
  i = Math.max(0, Math.min(frames.length - 1, k));
  $("frame").innerHTML = frames[i];
  $("slider").value = i;
  $("count").textContent = "step " + (i + 1) + " of " + frames.length;
  history.replaceState(null, "", "#" + i);   // so a reload stays on this step
}
$("slider").max = frames.length - 1;
$("slider").oninput = () => show(Number($("slider").value));
$("back").onclick = () => show(i - 1);
$("next").onclick = () => show(i + 1);
document.onkeydown = e => {
  if (e.target.id === "slider") return;      // the slider handles its own arrow keys
  if (e.key === "ArrowLeft") show(i - 1);
  if (e.key === "ArrowRight") show(i + 1);
};
show(Number(location.hash.slice(1)) || 0);
</script>
</body></html>
"""


# ---------- the page ----------

def play(frames, title, intro, values, path, kind):
    """Write the steps into one HTML page, open it in the browser, and return its path."""
    path = path or os.path.join(tempfile.gettempdir(), f"tdd_{kind}.html")
    page = (PAGE.replace("%TITLE%", escape(title)).replace("%INTRO%", escape(intro)).replace("%VALUES%", values)
                .replace("%FRAMES%", json.dumps(frames).replace("</", "<\\/")))
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)
    webbrowser.open("file://" + os.path.abspath(path))
    return path


def header(label, text):
    """One line at the top of the page, e.g. 'A      0 = 0000,  1 = 0001'."""
    return f'<div class="values"><b>{escape(label.ljust(7))}</b>{escape(text)}</div>'


def listing(tdd):
    """The TDD's values in decimal and in binary, e.g. '0 = 0000,  5 = 0101'."""
    vs = sorted(tdd)
    items = [f"{v} = {bits(tdd, v)}" for v in vs[:4 * LIMIT]]
    if len(vs) > 4 * LIMIT:
        items.append(f"… {len(vs) - 4 * LIMIT} more")
    return ",  ".join(items) or "no values"


def frame(caption, *panels):
    """One step: a caption, then some TDDs drawn side by side."""
    return f'<div class="caption">{escape(caption)}</div><div class="panels">{"".join(panels)}</div>'


def panel(title, root, nodes, marks, here=None, notes=None):
    """A TDD drawn as its vtree: one box per vtree node, listing that vtree node's TDD nodes.
    nodes[t] lists the TDD nodes at vtree node t (none yet if missing), marks[(t, i)] colors
    TDD node i at t, notes[(t, i)] is shown after it, and the box of `here` is outlined."""
    notes = notes or {}
    lines = {}
    for t in bottom_up(root):
        lines[t] = [f'<span class="head">{escape(f"{name(t)}  {span(t)}")}</span>']
        for i, node in enumerate(nodes.get(t, [])):
            note = f'<span class="note">{escape(notes[(t, i)])}</span>' if (t, i) in notes else ""
            lines[t].append(f'<span class="{marks.get((t, i), "")}">{escape(f"#{i} = {fmt(node)}")}</span>{note}')
    return f"<div><h3>{escape(title)}</h3>{tree(root, lines, here)}</div>"


def tree(t, lines, here):
    """The vtree from t down: t's box on top, its left and right subtrees side by side below it."""
    box = f'<div class="box{" here" if t is here else ""}">{"<br>".join(lines[t])}</div>'
    if t.is_leaf():
        return f'<div class="vt">{box}</div>'
    return f'<div class="vt">{box}<div class="kids">{tree(t.left, lines, here)}{tree(t.right, lines, here)}</div></div>'


# ---------- one step-by-step page per algorithm ----------

def play_build(tdd, path=None):
    """TDD.__init__, one group at a time, bottom-up. It replays your group() on the TDD's values."""
    values = {to_bits(v, tdd.L, tdd.signed) for v in tdd}
    strings = sorted(b.to01() for b in values)
    built, node_of, done, frames = {}, {}, {}, []
    for t in bottom_up(tdd.vtree):
        groups = [sorted(c.to01() for c in g) for g in group(t, values)]   # your group()
        node_of[t] = {c: i for i, g in enumerate(groups) for c in g}
        built[t] = []
        for i, g in enumerate(groups):
            outs = {outside(s, t) for s in strings if s[t.lo:t.hi] == g[0]}
            marks = {**done, (t, i): "focus"}
            if t.is_leaf():
                node = {int(c) for c in g}
                lines = ["a leaf node is the set of bits its group allows"]
            else:
                k = t.left.hi - t.lo
                node, lines = set(), []
                for c in g:
                    x, y = c[:k], c[k:]
                    pair = (node_of[t.left][x], node_of[t.right][y])
                    node.add(pair)
                    lines.append(f"{x}|{y} → {pair}: {x} is #{pair[0]} at {name(t.left)}, "
                                 f"{y} is #{pair[1]} at {name(t.right)}")
                    marks[(t.left, pair[0])] = "left"
                    marks[(t.right, pair[1])] = "right"
                if len(lines) > LIMIT:
                    lines = lines[:LIMIT] + [f"… {len(lines) - LIMIT} more chunks"]
            built[t].append(node)
            frames.append(frame(f"{name(t)}, group #{i} = {fmt(g)}: the chunks whose outsides are all {fmt(outs)}\n"
                                + "\n".join(lines) + f"\n→ TDD node #{i} = {fmt(node)}",
                                panel("the TDD built so far", tdd.vtree, built, marks, t)))
            done[(t, i)] = "done"
    same = all(built[t] == tdd.nodes[t] for t in bottom_up(tdd.vtree))
    frames.append(frame("done: " + ("✓ the same TDD nodes as your constructor made" if same
                                    else "✗ your constructor made different TDD nodes"),
                        panel("the TDD", tdd.vtree, built, {})))
    return play(frames, "TDD(values), step by step", INTRO_BUILD, header("values", listing(tdd)), path, "build")


def play_find(tdd, v, path=None):
    """_find, one vtree node at a time, children first: the order in which your recursion answers."""
    lo, hi = value_range(tdd.L, tdd.signed)
    if not lo <= v < hi:
        return play([frame(f"{v} is outside {lo} .. {hi - 1}, so __contains__ returns False before calling _find")],
                    f"{v} in tdd", INTRO_FIND, header("tdd", listing(tdd)) + header("v", f"{v}"), path, "find")
    b = to_bits(v, tdd.L, tdd.signed)
    s = b.to01()
    found, done, frames = {}, {}, []
    for n, t in enumerate(bottom_up(tdd.vtree), 1):
        found[t] = tdd._find(t, b)                 # your _find, started at vtree node t
        marks = {**done, (t, found[t]): "focus"}
        if t.is_leaf():
            key = b[t.lo]
            why = f"a leaf's key is its own bit: {key}"
        else:
            key = (found[t.left], found[t.right])
            why = f"the key is (answer at {name(t.left)}, answer at {name(t.right)}) = {key}"
            marks[(t.left, found[t.left])] = "left"
            marks[(t.right, found[t.right])] = "right"
        frames.append(frame(f"lookup {n}: {name(t)} reads {mark(s, t)}\n{why}\ntdd.up[{name(t)}] gives {ref(found[t])}",
                            panel(f"looking up v = {v} = {s}", tdd.vtree, tdd.nodes, marks, t)))
        done[(t, found[t])] = "done"
    answer = found[tdd.vtree] is not None
    frames.append(frame(f"the root gives {ref(found[tdd.vtree])}, so {v} is {'' if answer else 'NOT '}in the set "
                        f"(your `{v} in tdd` returns {v in tdd})",
                        panel(f"looking up v = {v} = {s}", tdd.vtree, tdd.nodes, done)))
    return play(frames, f"{v} in tdd, step by step", INTRO_FIND,
                header("tdd", listing(tdd)) + header("v", f"{v} = {s}"), path, "find")


def play_count(tdd, path=None):
    """__len__, one TDD node at a time, bottom-up."""
    count, notes, done, frames = {}, {}, {}, []
    for t in bottom_up(tdd.vtree):
        count[t] = []
        for i, node in enumerate(tdd.nodes[t]):
            marks = {**done, (t, i): "focus"}
            if t.is_leaf():
                count[t].append(len(node))
                how = f"a leaf node has one model per allowed bit: {count[t][i]}"
            else:
                terms = [(count[t.left][a], count[t.right][b]) for a, b in sorted(node)]
                count[t].append(sum(x * y for x, y in terms))
                how = ("each pair (a, b) has (models of a) × (models of b); add them up: "
                       + " + ".join(f"{x}×{y}" for x, y in terms[:LIMIT])
                       + (" + …" if len(terms) > LIMIT else "") + f" = {count[t][i]}")
                for a, b in node:
                    marks[(t.left, a)] = "left"
                    marks[(t.right, b)] = "right"
            notes[(t, i)] = f"models: {count[t][i]}"
            frames.append(frame(f"{name(t)}, TDD node #{i} = {fmt(node)} has {len(node)} input(s)\n{how}",
                                panel("model counts so far", tdd.vtree, tdd.nodes, marks, t, notes)))
            done[(t, i)] = "done"
    total = sum(count[tdd.vtree])
    frames.append(frame(f"model count = the sum at the root = {total} "
                        f"({'✓' if total == len(tdd) else '✗'} your len(tdd) returns {len(tdd)})",
                        panel("model counts", tdd.vtree, tdd.nodes, {}, None, notes)))
    return play(frames, "len(tdd), step by step", INTRO_COUNT, header("values", listing(tdd)), path, "count")


def play_and(A, B, path=None):
    """__and__: each vtree node bottom-up, each product (i, j), each pair combination."""
    C = A & B   # your result: it gives the vtree to draw on, and it is checked in the last step
    built, notes, idx, frames = {}, {}, {}, []

    def step(caption, here, ma, mb, mc):
        """Add one frame: A, B and the result built so far, side by side."""
        t, ta, tb = here
        frames.append(frame(caption,
                            panel("A", A.vtree, A.nodes, ma, ta),
                            panel("B", B.vtree, B.nodes, mb, tb),
                            panel("A & B, built so far", C.vtree, built, mc, t, notes)))

    for t, ta, tb in zip(bottom_up(C.vtree), bottom_up(A.vtree), bottom_up(B.vtree)):
        here = (t, ta, tb)
        built[t], idx[t] = [], {}
        step(f"next vtree node {name(t)}: A has {len(A.nodes[ta])} TDD node(s) here and B has {len(B.nodes[tb])}, "
             f"so there are {len(A.nodes[ta]) * len(B.nodes[tb])} products (i, j) to try", here, {}, {}, {})
        for i, ga in enumerate(A.nodes[ta]):
            for j, gb in enumerate(B.nodes[tb]):
                k = len(built[t])               # the index this product gets if it is kept
                node = set()
                built[t].append(node)           # drawn while it is being built
                notes[(t, k)] = f"(A#{i} & B#{j})"
                ma, mb, mc = {(ta, i): "focus"}, {(tb, j): "focus"}, {(t, k): "focus"}
                if t.is_leaf():
                    node |= ga & gb
                    what = f"{name(t)} is a leaf: A#{i} {fmt(ga)} & B#{j} {fmt(gb)} = {fmt(node)}, the bits both allow"
                else:
                    for al, ar in sorted(ga):
                        for bl, br in sorted(gb):
                            left = idx[t.left].get((al, bl))
                            right = idx[t.right].get((ar, br))
                            if left is not None and right is not None:
                                node.add((left, right))
                                verdict = f"both were kept, so add the pair ({left}, {right})"
                            else:
                                verdict = "a side was dropped (it has no models), so skip this combination"
                            step(f"{name(t)}, product A#{i} & B#{j}: A's pair {(al, ar)} with B's pair {(bl, br)}\n"
                                 f"  left with left:   {name(t.left)}  A#{al} & B#{bl} → {ref(left)}\n"
                                 f"  right with right: {name(t.right)}  A#{ar} & B#{br} → {ref(right)}\n"
                                 f"  {verdict}",
                                 here,
                                 {**ma, (ta.left, al): "left", (ta.right, ar): "right"},
                                 {**mb, (tb.left, bl): "left", (tb.right, br): "right"},
                                 {**mc, (t.left, left): "left", (t.right, right): "right"})
                    what = f"{name(t)}: A#{i} & B#{j} = {fmt(node)}, the pairs added above"
                if node:
                    idx[t][(i, j)] = k
                    step(f"{what}  → keep it as #{k}", here, ma, mb, mc)
                else:
                    step(f"{what}  → no models, drop it", here, ma, mb, mc)
                    built[t].pop()
                    del notes[(t, k)]

    same = all(built[t] == C.nodes[t] for t in bottom_up(C.vtree))
    values = sorted(C)
    K = TDD(values, C.L, C.signed)   # what the constructor builds for the same values
    used = {(t, C._find(t, to_bits(v, C.L, C.signed))) for v in values for t in bottom_up(C.vtree)}
    unused = {(t, k): "unused" for t in bottom_up(C.vtree) for k in range(len(built[t])) if (t, k) not in used}
    frames.append(frame(
        ("done: ✓ the same TDD nodes as your A & B" if same else "done: ✗ your A & B has different TDD nodes")
        + f"\nvalues {values}" + (" ✓ = A ∩ B" if values == sorted(set(A) & set(B)) else " ✗ ≠ A ∩ B")
        + f"\n{size(C)} TDD nodes; the constructor builds {size(K)} for the same values."
        + f"\ncrossed out: {len(unused)} TDD node(s) that no stored value goes through",
        panel("A", A.vtree, A.nodes, {}), panel("B", B.vtree, B.nodes, {}),
        panel("A & B", C.vtree, built, unused, None, notes)))
    values = header("A", listing(A)) + header("B", listing(B)) + header("A & B", listing(C))
    return play(frames, "A & B, step by step", INTRO_AND, values, path, "and")
