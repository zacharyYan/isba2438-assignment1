# products.py — Command-Line Product Inventory (ISBA2438 Assignment 1)

A small, non-interactive Python 3 command-line tool that keeps a tiny store's
product inventory in a plain UTF-8 JSON file.

## Who it helps and why

- **Store staff and owners** who need a fast way to record products, correct
  quantities after a delivery or a sale, and look up a price without opening a
  spreadsheet.
- **Restock planning:** the custom `low-stock` command lists every product at
  or below a chosen quantity, so staff can see what needs reordering before
  shelves empty.
- **Scripts and automation:** every run performs exactly one operation and
  exits (no menus, no prompts), prints machine-readable JSON, and uses clear
  exit codes, so the tool behaves well inside shell scripts.

## Requirements and setup

- Python 3 (developed and tested with Python 3.9 on macOS).
- **Standard library only** — no packages to install.
- Just download `products.py`. The data file (`products.json` by default) is
  created automatically by the first successful `add` in the directory you run
  from.

## Syntax

```
python3 products.py [--file PATH] COMMAND [OPTIONS]
```

- `--file PATH` is **global and must appear BEFORE the command**. It selects
  the JSON data file. Default: `products.json` in the current working
  directory; relative paths resolve from there.
- Quote names and paths that contain spaces, e.g. `--name "Desk Lamp"`.
- One operation per invocation; the tool never asks interactive questions.

### Commands (exact syntax)

| Command | Effect | Success output (stdout) |
|---|---|---|
| `add --name NAME --price PRICE --quantity QTY` | Create a product; all three flags required; ID auto-assigned | The created product JSON object |
| `list` | All products sorted by numeric ID | JSON array (`[]` when empty) |
| `get ID` | Print one product | The product JSON object |
| `update ID [--name NAME] [--price PRICE] [--quantity QTY]` | Change only the supplied fields; at least one flag required; ID and other fields preserved | The updated product JSON object |
| `delete ID --yes` | Permanently remove one product; `--yes` required, nothing is prompted | `{"deleted_id": ID}` |
| `low-stock --threshold N` | Products with `quantity <= N` (custom feature, see below) | JSON array sorted by numeric ID |

Every command supports `--help` (and so does the top level). Help works even
when the data file is missing or invalid, because help never touches it.

## Field rules

- **id** — positive integer, auto-assigned starting at 1, never changed by
  updates, and **never reused** after a delete (the store's `next_id` only
  moves forward). IDs passed to `get`/`update`/`delete` must be positive
  integers.
- **name** — leading/trailing whitespace is trimmed; it must keep at least one
  non-whitespace character; duplicate names are allowed.
- **price** — nonnegative decimal made of digits with an optional decimal
  point followed by **one or two** digits. Accepted: `0`, `4.5`, `4.50`.
  Rejected: signs, currency symbols, exponents, three or more decimals.
  Stored and printed as a **string with exactly two decimal places**, e.g.
  `"4.50"`.
- **quantity** — nonnegative integer; `0` is valid; negative or fractional
  values are rejected.

## Data file: JSON shape, persistence, ID rules

The store is a UTF-8 JSON object shaped like:

```json
{
  "next_id": 2,
  "products": [
    {"id": 1, "name": "Notebook", "price": "4.50", "quantity": 10}
  ]
}
```

- A **missing file is an empty store** (`next_id` 1, no products). Only a
  successful `add` creates the file; read-only commands never create or
  rewrite it.
- On each successful `add`, `next_id` is assigned to the new product and then
  incremented by one. Updates and deletes never change `next_id`, so IDs are
  unique and never reused, and `next_id` stays greater than every stored ID.
- Successful mutations are **saved before** anything is printed, using a
  temporary file in the same directory plus an atomic rename, so an
  interrupted save can never corrupt the previous data. Missing parent
  directories are not created.
- **Any failed command leaves the file bytes and `next_id` exactly unchanged
  and consumes no ID.** An existing but empty, malformed, or schema-invalid
  data file is an error: the tool reports it and leaves the file untouched.

## Output, exit codes, and stderr behavior

- Successful data commands print **only their JSON result** on stdout (help
  prints ordinary help text).
- Expected errors print a concise explanation on stderr with **no Python
  traceback**. Input/syntax errors produced by the argument parser may also
  include a short usage line, so the exact error text can be more than one
  line; the examples below are illustrative.
- Exit codes:
  - `0` — success, including an empty `list`/`low-stock` result and help.
  - `1` — missing product ID (the message names the ID), invalid stored data,
    file read/write failure.
  - `2` — invalid syntax, missing arguments, or invalid input values.

## Exit-code examples (illustrative)

Error wording shown here is illustrative — argument-parser errors may
additionally print a usage line before the message.

```console
$ python3 products.py get 9
error: no product with ID 9            # exit 1
$ python3 products.py delete 1
usage: ... error: the following arguments are required: --yes   # exit 2
$ python3 products.py add --name Notebook --price 4.505 --quantity 1
error: price must be digits with an optional 1-2 digit decimal part, got '4.505'   # exit 2
```

## Custom feature: low-stock

**Who it helps and why:** store staff planning restocks. Instead of reading
the whole inventory and mentally comparing quantities, one command lists every
product that is at or below a reorder level, so purchasing can happen in one
pass.

**Syntax:**

```
python3 products.py [--file PATH] low-stock --threshold N
```

- `--threshold N` is required; `N` must be a **nonnegative integer** (`0` is
  valid; negative, fractional, or non-numeric values exit 2 without touching
  any file).
- Matching is **inclusive**: products with `quantity <= N` are returned.
- Output: a **JSON array sorted by numeric ID**; `[]` when nothing matches or
  when the data file does not exist yet.
- Strictly **read-only**: it never creates or rewrites the data file, and its
  `--help` works without any data file.
- Works with the global `--file PATH` (placed before the command).

## Self-contained runnable example

Start in the downloaded or cloned project folder — the folder that contains
`products.py`. The commands copy the tool into a fresh temporary directory
and run there, so they cannot touch any data you already have (nothing needs
to be deleted).

```console
$ inventory_demo_dir="$(mktemp -d)"
$ cp products.py "$inventory_demo_dir/"
$ cd "$inventory_demo_dir"
$ python3 products.py add --name "Notebook" --price 4.5 --quantity 10
{"id": 1, "name": "Notebook", "price": "4.50", "quantity": 10}
$ python3 products.py add --name "Pencil" --price 1.25 --quantity 5
{"id": 2, "name": "Pencil", "price": "1.25", "quantity": 5}
$ python3 products.py add --name "Stapler" --price 2 --quantity 0
{"id": 3, "name": "Stapler", "price": "2.00", "quantity": 0}
```

Success — inclusive boundary (`quantity <= 5`), sorted by numeric ID:

```console
$ python3 products.py low-stock --threshold 5
[{"id": 2, "name": "Pencil", "price": "1.25", "quantity": 5}, {"id": 3, "name": "Stapler", "price": "2.00", "quantity": 0}]
```

Edge case — threshold 0 lists only zero-stock products:

```console
$ python3 products.py low-stock --threshold 0
[{"id": 3, "name": "Stapler", "price": "2.00", "quantity": 0}]
```

Edge case — no matches gives an empty array, exit 0:

```console
$ python3 products.py --file bulk.json add --name "Binder" --price 5 --quantity 30
{"id": 1, "name": "Binder", "price": "5.00", "quantity": 30}
$ python3 products.py --file bulk.json add --name "Desk Lamp" --price 12.5 --quantity 7
{"id": 2, "name": "Desk Lamp", "price": "12.50", "quantity": 7}
$ python3 products.py --file bulk.json low-stock --threshold 5
[]
```

Invalid threshold — exit 2, files untouched:

```console
$ python3 products.py low-stock --threshold -1
error: threshold must be a nonnegative integer, got '-1'
```

## Teacher's demo sequence (expected results)

Run in a fresh directory containing `products.py` (no `products.json` yet):

```
python3 products.py --help
python3 products.py add --name "Notebook" --price 4.5 --quantity 10
python3 products.py add --name "Pencil" --price 1.25 --quantity 5
python3 products.py list
python3 products.py get 1
python3 products.py update 1 --quantity 12
python3 products.py delete 2 --yes
python3 products.py list
```

Expected: `add` prints the created products with prices `"4.50"` and
`"1.25"`; `list` shows both sorted by ID; `get 1` returns Notebook;
`update 1 --quantity 12` changes only the quantity; `delete 2 --yes` prints
`{"deleted_id": 2}`; the final `list` shows only Notebook.

Final `products.json`:

```json
{
  "next_id": 3,
  "products": [
    {"id": 1, "name": "Notebook", "price": "4.50", "quantity": 12}
  ]
}
```

Note the ID rules in action: ID 2 was deleted but **not reused** — the next
`add` would receive ID 3, because `next_id` was left at 3 by the earlier adds
and is not changed by updates or deletes. A later invocation (`get 1`, `list`)
reads the saved file and confirms the changes persisted.

## Recording checklist (to prepare in the student's own words)

- [ ] Start with **no** `products.json`; show `--help`, then the eight-command
  sequence above; show the final `products.json` (Notebook, id 1, `"4.50"`,
  quantity 12, `next_id` 3).
- [ ] **Persistence/JSON:** run `get 1`/`list` in a *separate* invocation and
  explain that the data came from the saved JSON file.
- [ ] **Failures with unchanged data:** capture the file hash
  (`shasum products.json`) before and after (a) a missing ID such as
  `get 9` (exit 1, message names the ID), (b) an invalid input such as
  `--price 4.505` (exit 2), and (c) `delete 1` without `--yes` (exit 2);
  show the hash is identical each time.
- [ ] **`--file`:** run a command against `--file other.json` and show the
  default `products.json` is untouched.
- [ ] **Custom feature:** one successful `low-stock` run plus one edge case
  (threshold 0 → zero-stock products; invalid threshold → exit 2).
- [ ] **Explain in your own words:** one selected command's code, the
  read/save flow (load → validate → modify → temp file → atomic
  `os.replace` → print), and why the standard library tools
  (`argparse`, `json`, `re`, `tempfile`) were chosen.
- The recording must describe the exact commit it documents; do not record
  claims about steps that have not actually been done yet.

## Acknowledgments and submission checklist

- This tool was built for the **ISBA2438 Assignment 1** handout; feature and
  error-handling requirements come from that assignment description.
- It was developed incrementally with the **Viber** coding assistant, with
  **ChatGPT** helping coordinate prompts and review passes. The repository
  owner must review, test, and be able to explain the result in their own
  words.

Submission checklist (work through in order; tick as completed):

- [ ] Create the public GitHub repository and push this project to it.
- [ ] Record the demonstration so it describes the exact final full commit
  SHA it documents.
- [ ] Submit the repository URL, artifacts, and the full commit SHA for
  `assignment-1` through the course portal.
