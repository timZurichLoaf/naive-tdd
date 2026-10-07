# naive-tdd
A naive implementation of [TDD](https://arxiv.org/abs/2604.05537) for set intersection

## See a TDD being built, step by step

[![TDD([0, 1, 4, 5, 10, 11], 4) being built, one group at a time](docs/play_build.gif)](https://raw.githack.com/timZurichLoaf/naive-tdd/main/docs/play_build.html)

This is `TDD([0, 1, 4, 5, 10, 11], 4)` being built bottom-up over the vtree, one group at a time. Each box is a vtree node, and each line inside it is one of its TDD nodes. Yellow marks the TDD node being built, blue and green mark the left and right children its pairs point to, and purple marks nodes that are done.

The animation is a recording of an interactive page. [Open the page](https://raw.githack.com/timZurichLoaf/naive-tdd/main/docs/play_build.html) to step back and forth with the buttons, the ← → keys or the slider. After cloning, you can also open [`docs/play_build.html`](docs/play_build.html) directly in your browser.

### Make your own

You need Python 3.10 or later and [bitarray](https://pypi.org/project/bitarray/):

```bash
pip install bitarray
```

Then, from the repository folder:

```python
from stepper import *

A = TDD([0, 1, 4, 5, 10, 11], 4)
# A = TDD(range(8), 4)
play_build(A)
```

`play_build` runs the constructor in `tdd.py`, writes every step into one self-contained HTML page and opens it in your browser. The page is saved to your temp folder unless you pass a path, e.g. `play_build(A, path="docs/play_build.html")`.

The other operations have pages too:

| call | steps through |
|---|---|
| `play_build(A)` | `TDD(values, L)`, one group at a time |
| `play_find(A, 6)` | `6 in A`, one vtree node at a time |
| `play_count(A)` | `len(A)`, one TDD node at a time |
| `play_and(A, B)` | `A & B`, one pair combination at a time |

Values are unsigned `L`-bit integers by default; `TDD(values, L, signed=True)` stores signed ones in two's complement. Keep `L` small (up to about 6) so the pages stay readable.

`util.py` shows the same steps as text, e.g. `show_build(A)` or `show_and(A, B)`, and `explore()` wraps them in notebook widgets (this needs `ipywidgets`).
