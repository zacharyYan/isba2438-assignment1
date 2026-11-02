#!/usr/bin/env python3
"""ISBA2438 Assignment 1: command-line product inventory tool.

Implements argument parsing, input validation, UTF-8 JSON storage and the
commands add, list, get, update, delete and low-stock (custom feature).
"""

import argparse
import json
import os
import re
import sys
import tempfile

DEFAULT_FILE = "products.json"

PRICE_PATTERN = re.compile(r"\d+(?:\.\d{1,2})?")
INTEGER_PATTERN = re.compile(r"\d+")


def syntax_error(message):
    print(f"error: {message}", file=sys.stderr)
    sys.exit(2)


def runtime_error(message):
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def validate_id(text):
    if not INTEGER_PATTERN.fullmatch(text) or int(text) <= 0:
        syntax_error(f"product ID must be a positive integer, got {text!r}")
    return int(text)


def validate_name(text):
    name = text.strip()
    if not name:
        syntax_error("name must contain at least one non-whitespace character")
    return name


def validate_price(text):
    if not PRICE_PATTERN.fullmatch(text):
        syntax_error(
            "price must be digits with an optional 1-2 digit decimal part, "
            f"got {text!r}"
        )
    whole, _, fraction = text.partition(".")
    whole = whole.lstrip("0") or "0"
    return f"{whole}.{(fraction + '00')[:2]}"


def validate_quantity(text):
    if not INTEGER_PATTERN.fullmatch(text):
        syntax_error(f"quantity must be a nonnegative integer, got {text!r}")
    return int(text)


def validate_threshold(text):
    if not INTEGER_PATTERN.fullmatch(text):
        syntax_error(f"threshold must be a nonnegative integer, got {text!r}")
    return int(text)


def load_store(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = handle.read()
    except FileNotFoundError:
        return {"next_id": 1, "products": []}
    except UnicodeDecodeError:
        runtime_error(f"data file '{path}' is not valid UTF-8")
    except OSError as exc:
        runtime_error(f"cannot read data file '{path}': {exc.strerror or exc}")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        runtime_error(f"data file '{path}' is empty or not valid JSON")
    return validate_store(data)


def validate_store(data):
    if not isinstance(data, dict) or set(data) != {"next_id", "products"}:
        runtime_error(
            "data file must be an object with keys 'next_id' and 'products'"
        )
    next_id = data["next_id"]
    products = data["products"]
    if type(next_id) is not int or next_id <= 0:
        runtime_error("'next_id' must be a positive integer")
    if not isinstance(products, list):
        runtime_error("'products' must be a JSON array")
    seen_ids = set()
    for index, product in enumerate(products):
        where = f"product {index}"
        if not isinstance(product, dict) or set(product) != {
            "id", "name", "price", "quantity"
        }:
            runtime_error(
                f"{where} must be an object with keys 'id', 'name', "
                "'price', 'quantity'"
            )
        if type(product["id"]) is not int or product["id"] <= 0:
            runtime_error(f"{where} needs a positive integer 'id' (not boolean)")
        if product["id"] in seen_ids:
            runtime_error(f"{where} repeats ID {product['id']}")
        seen_ids.add(product["id"])
        name = product["name"]
        if not isinstance(name, str) or not name.strip() or name != name.strip():
            runtime_error(f"{where} needs a trimmed, nonblank 'name'")
        price = product["price"]
        if not isinstance(price, str) or not re.fullmatch(r"\d+\.\d{2}", price):
            runtime_error(f"{where} needs a 'price' string with exactly two decimals")
        if type(product["quantity"]) is not int or product["quantity"] < 0:
            runtime_error(f"{where} needs a nonnegative integer 'quantity' (not boolean)")
        if next_id <= product["id"]:
            runtime_error("'next_id' must be greater than every existing product ID")
    return data


def save_store(path, store):
    directory = os.path.dirname(os.path.abspath(path))
    temp_path = None
    try:
        descriptor, temp_path = tempfile.mkstemp(
            prefix=".products-", suffix=".tmp", dir=directory
        )
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(store, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        temp_path = None
    except OSError as exc:
        runtime_error(f"cannot write data file '{path}': {exc.strerror or exc}")
    finally:
        if temp_path is not None:
            try:
                os.unlink(temp_path)
            except OSError:
                pass


def find_product(store, product_id):
    for product in store["products"]:
        if product["id"] == product_id:
            return product
    runtime_error(f"no product with ID {product_id}")


def cmd_low_stock(args):
    store = load_store(args.file)
    matches = [product for product in store["products"]
               if product["quantity"] <= args.threshold]
    matches.sort(key=lambda product: product["id"])
    print(json.dumps(matches, ensure_ascii=False))


def cmd_add(args):
    path = args.file
    store = load_store(path)
    product = {
        "id": store["next_id"],
        "name": args.name,
        "price": args.price,
        "quantity": args.quantity,
    }
    store["products"].append(product)
    store["next_id"] = product["id"] + 1
    save_store(path, store)
    print(json.dumps(product, ensure_ascii=False))


def cmd_list(args):
    store = load_store(args.file)
    products = sorted(store["products"], key=lambda product: product["id"])
    print(json.dumps(products, ensure_ascii=False))


def cmd_get(args):
    store = load_store(args.file)
    product = find_product(store, args.id)
    print(json.dumps(product, ensure_ascii=False))


def cmd_update(args):
    path = args.file
    store = load_store(path)
    product = find_product(store, args.id)
    if args.name is not None:
        product["name"] = args.name
    if args.price is not None:
        product["price"] = args.price
    if args.quantity is not None:
        product["quantity"] = args.quantity
    save_store(path, store)
    print(json.dumps(product, ensure_ascii=False))


def cmd_delete(args):
    path = args.file
    store = load_store(path)
    product = find_product(store, args.id)
    store["products"].remove(product)
    save_store(path, store)
    print(json.dumps({"deleted_id": args.id}, ensure_ascii=False))


def validate_args(args):
    if args.command in ("get", "update", "delete"):
        args.id = validate_id(args.id)
    if args.command == "add":
        args.name = validate_name(args.name)
        args.price = validate_price(args.price)
        args.quantity = validate_quantity(args.quantity)
    if args.command == "update":
        if args.name is None and args.price is None and args.quantity is None:
            syntax_error(
                "update requires at least one of --name, --price, --quantity"
            )
        if args.name is not None:
            args.name = validate_name(args.name)
        if args.price is not None:
            args.price = validate_price(args.price)
        if args.quantity is not None:
            args.quantity = validate_quantity(args.quantity)
    if args.command == "low-stock":
        args.threshold = validate_threshold(args.threshold)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="products.py",
        description="Manage a small store's product inventory (JSON data file).",
        allow_abbrev=False,
    )
    parser.add_argument(
        "--file",
        metavar="PATH",
        default=DEFAULT_FILE,
        help=f"JSON data file path, given BEFORE the command (default: {DEFAULT_FILE})",
    )
    subparsers = parser.add_subparsers(
        dest="command",
        metavar="COMMAND",
        required=True,
        title="commands",
    )

    add_parser = subparsers.add_parser(
        "add",
        allow_abbrev=False,
        help="create one product",
        description="create one product",
    )
    add_parser.add_argument(
        "--name", required=True, metavar="NAME",
        help="product name (trimmed, must not be blank)",
    )
    add_parser.add_argument(
        "--price", required=True, metavar="PRICE",
        help="digits with optional 1-2 decimals, e.g. 4.5",
    )
    add_parser.add_argument(
        "--quantity", required=True, metavar="QTY",
        help="nonnegative integer, 0 allowed",
    )
    add_parser.set_defaults(handler=cmd_add)

    list_parser = subparsers.add_parser(
        "list",
        allow_abbrev=False,
        help="list products sorted by ID",
        description="list products sorted by ID",
    )
    list_parser.set_defaults(handler=cmd_list)

    get_parser = subparsers.add_parser(
        "get",
        allow_abbrev=False,
        help="print one product by ID",
        description="print one product by ID",
    )
    get_parser.add_argument("id", metavar="ID", help="positive integer product ID")
    get_parser.set_defaults(handler=cmd_get)

    update_parser = subparsers.add_parser(
        "update",
        allow_abbrev=False,
        help="change supplied fields of one product",
        description="change supplied fields of one product",
    )
    update_parser.add_argument("id", metavar="ID", help="positive integer product ID")
    update_parser.add_argument(
        "--name", metavar="NAME", help="new name (trimmed, must not be blank)",
    )
    update_parser.add_argument(
        "--price", metavar="PRICE", help="digits with optional 1-2 decimals, e.g. 4.5",
    )
    update_parser.add_argument(
        "--quantity", metavar="QTY", help="nonnegative integer, 0 allowed",
    )
    update_parser.set_defaults(handler=cmd_update)

    delete_parser = subparsers.add_parser(
        "delete",
        allow_abbrev=False,
        help="remove one product permanently",
        description="remove one product permanently",
    )
    delete_parser.add_argument("id", metavar="ID", help="positive integer product ID")
    delete_parser.add_argument(
        "--yes", action="store_true", required=True,
        help="confirm deletion (no prompting)",
    )
    delete_parser.set_defaults(handler=cmd_delete)

    low_stock_parser = subparsers.add_parser(
        "low-stock",
        allow_abbrev=False,
        help="list products with quantity <= threshold",
        description="list products with quantity <= threshold",
    )
    low_stock_parser.add_argument(
        "--threshold", required=True, metavar="N",
        help="nonnegative integer, 0 allowed",
    )
    low_stock_parser.set_defaults(handler=cmd_low_stock)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    validate_args(args)
    args.handler(args)


if __name__ == "__main__":
    main()
