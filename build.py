#!/usr/bin/env python3
"""Збирає сайт клієнта з template.html і JSON-файлу з даними.

    python3 build.py clients/prime-detailing.json            -> sites/prime-detailing/index.html
    python3 build.py clients/detailingrv.json --out index.html
"""
import argparse
import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TAG = re.compile(r"\{\{(\{?)\s*([#^/]?)\s*([^}]+?)\s*\}?\}\}")


# ---------- фото: Unsplash-id отримує набір розмірів, власне фото лишається як є ----------
def _unsplash(photo):
    return isinstance(photo, str) and photo.startswith("photo-")


def _img_args(arg):
    parts = [p for p in arg.split(";") if p]
    fit = "nofit" not in parts
    sizes = [tuple(p.split(",")) for p in parts if p != "nofit"]
    return sizes, fit


def _img_url(photo, w, q, fit):
    url = f"https://images.unsplash.com/{photo}?w={w}&q={q}&auto=format"
    return url + "&fit=crop" if fit else url


def f_src(photo, arg):
    if not _unsplash(photo):
        return photo
    sizes, fit = _img_args(arg)
    w, q = sizes[0]
    return _img_url(photo, w, q, fit)


def f_srcset(photo, arg):
    if not _unsplash(photo):
        return ""
    sizes, fit = _img_args(arg)
    return ", ".join(f"{_img_url(photo, w, q, fit)} {w}w" for w, q in sizes)


def f_step(i, arg):
    step, dec = arg.split(",")
    return f"{i * float(step):.{int(dec)}f}"


FILTERS = {"src": f_src, "srcset": f_srcset, "step": f_step}


# ---------- мінімальний шаблонізатор у стилі Mustache ----------
def parse(src):
    root, stack, pos = [], [], 0
    cur = root
    for m in TAG.finditer(src):
        if m.start() > pos:
            cur.append(src[pos:m.start()])
        raw, kind, name = m.group(1) == "{", m.group(2), m.group(3)
        if kind in "#^" and kind:
            node = {"kind": kind, "name": name, "body": []}
            cur.append(node)
            stack.append((cur, node))
            cur = node["body"]
        elif kind == "/":
            cur, node = stack.pop()
            if node["name"] != name:
                raise ValueError(f"секція {{{{#{node['name']}}}}} закрита як {{{{/{name}}}}}")
        else:
            cur.append({"kind": "var", "name": name, "raw": raw})
        pos = m.end()
    if stack:
        raise ValueError(f"незакрита секція {{{{#{stack[-1][1]['name']}}}}}")
    cur.append(src[pos:])
    return root


_MISSING = object()


def lookup(ctx, path):
    if path == ".":
        return ctx[-1]
    head, *rest = path.split(".")
    for frame in reversed(ctx):
        if isinstance(frame, dict) and head in frame:
            val = frame[head]
            break
    else:
        raise KeyError(f"у даних немає «{path}»")
    for key in rest:
        val = val[int(key)] if isinstance(val, list) else val.get(key, _MISSING)
        if val is _MISSING:
            raise KeyError(f"у даних немає «{path}»")
    return val


def value(ctx, expr):
    name, *filters = expr.split("|")
    val = lookup(ctx, name)
    for flt in filters:
        fname, _, arg = flt.partition(":")
        val = FILTERS[fname](val, arg)
    return val


def render(nodes, ctx):
    out = []
    for n in nodes:
        if isinstance(n, str):
            out.append(n)
        elif n["kind"] == "var":
            val = value(ctx, n["name"])
            out.append(str(val) if n["raw"] else html.escape(str(val)))
        else:
            try:
                val = lookup(ctx, n["name"])
            except KeyError:
                val = None  # необов'язкові поля (tag, gift…) можна не вказувати
            if n["kind"] == "^":
                if not val:
                    out.append(render(n["body"], ctx))
            elif isinstance(val, list):
                for i, item in enumerate(val):
                    meta = {"@i": i, "@n": i + 1, "@first": i == 0, "@last": i == len(val) - 1}
                    out.append(render(n["body"], ctx + [meta, item]))
            elif val:
                out.append(render(n["body"], ctx + [val] if isinstance(val, dict) else ctx))
    return "".join(out)


# ---------- похідні значення, які зручніше рахувати тут, ніж писати руками ----------
def _minutes(hhmm):
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def derive(data):
    hex_ = data["accent"].lstrip("#")
    hours = data["hours"]
    data["_"] = {
        "accent_rgb": ",".join(str(int(hex_[i:i + 2], 16)) for i in (0, 2, 4)),
        "accent_url": "%23" + hex_,
        "solutions": json.dumps([p["solution"] for p in data["problems"]], ensure_ascii=False),
        "caps": json.dumps([[r["before"], r["after"]] for r in data["results"]], ensure_ascii=False),
        "hours": json.dumps({
            "open": _minutes(hours["open"]), "close": _minutes(hours["close"]),
            "openLabel": hours["open"].lstrip("0"), "closeLabel": hours["close"],
            "days": hours["days"],
        }, ensure_ascii=False),
    }
    return data


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("client", help="JSON-файл клієнта, напр. clients/prime-detailing.json")
    ap.add_argument("--out", help="куди записати сайт (типово sites/<назва-файлу>/index.html)")
    args = ap.parse_args()

    client = Path(args.client)
    data = derive(json.loads(client.read_text(encoding="utf-8")))
    page = render(parse((ROOT / "template.html").read_text(encoding="utf-8")), [data])

    out = Path(args.out) if args.out else ROOT / "sites" / client.stem / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")

    # власні фото клієнта: clients/<клієнт>/ копіюється поруч із сайтом
    assets = client.with_suffix("")
    if assets.is_dir():
        shutil.copytree(assets, out.parent, dirs_exist_ok=True)
    print(f"готово: {out}")


if __name__ == "__main__":
    main()
