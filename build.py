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


# ---------- фото ----------
# Unsplash-id ("photo-…"): якщо в images/photos/ є оптимізовані копії (tools/optimize-images.py),
# сайт бере їх (AVIF + WebP, різні ширини); інакше — адаптивні посилання на Unsplash.
# Власне фото клієнта (img/назва.jpg) лишається як є.
LOCAL = ROOT / "images" / "photos"
USED = set()  # локальні файли, які треба скопіювати поруч із сайтом клієнта


def _unsplash(photo):
    return isinstance(photo, str) and photo.startswith("photo-")


def _local(photo, widths, ext):
    """Шляхи до локальних копій або None, якщо хоч однієї бракує."""
    if not _unsplash(photo):
        return None
    paths = [f"images/photos/{photo}-{w}.{ext}" for w in widths]
    if all((ROOT / p).exists() for p in paths):
        USED.update(paths)
        return paths
    return None


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
    local = _local(photo, [w], "webp")
    return local[0] if local else _img_url(photo, w, q, fit)


def f_srcset(photo, arg):
    if not _unsplash(photo):
        return ""
    sizes, fit = _img_args(arg)
    local = _local(photo, [w for w, _ in sizes], "webp")
    if local:
        return ", ".join(f"{p} {w}w" for p, (w, _) in zip(local, sizes))
    return ", ".join(f"{_img_url(photo, w, q, fit)} {w}w" for w, q in sizes)


def f_avifset(photo, arg):
    """srcset у форматі AVIF для <source>; порожньо, якщо локальних копій немає (браузер пропустить source)."""
    sizes, _ = _img_args(arg)
    local = _local(photo, [w for w, _ in sizes], "avif")
    return ", ".join(f"{p} {w}w" for p, (w, _) in zip(local, sizes)) if local else ""


def f_step(i, arg):
    step, dec = arg.split(",")
    return f"{i * float(step):.{int(dec)}f}"


FILTERS = {"src": f_src, "srcset": f_srcset, "avifset": f_avifset, "step": f_step}


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


def _week(hours):
    """Графік на 7 днів (0 = неділя): [відкриття, закриття, "9:00", "20:00"] або None.
    Або однаковий час на всі робочі дні (open/close/days), або свій для кожного дня (week)."""
    week = hours.get("week") or [
        [hours["open"], hours["close"]] if d in hours["days"] else None for d in range(7)
    ]
    days = [[_minutes(o), _minutes(c), o.lstrip("0"), c] if o else None for o, c in (d or (None, None) for d in week)]
    return {"week": days, "daily": all(days) and len({tuple(d) for d in days}) == 1}


def _pairs(data, client_dir):
    """results[].pair = "images/before-after/<категорія>": шукаємо before/after.webp (або jpg/png)."""
    for r in data.get("results", []):
        folder = r.get("pair")
        if not folder:
            continue
        found = {}
        for side in ("before", "after"):
            for base in (ROOT, client_dir):
                hit = next((p for p in sorted((base / folder).glob(side + ".*")) if p.suffix.lower() in (".webp", ".jpg", ".jpeg", ".png")), None)
                if hit:
                    rel = f"{folder}/{hit.name}"
                    small = hit.with_name(side + "-800.webp")
                    found[side] = rel
                    found[side + "_set"] = f"{rel} 1600w" + (f", {folder}/{small.name} 800w" if small.exists() else "")
                    if base == ROOT:
                        USED.add(rel)
                        if small.exists():
                            USED.add(f"{folder}/{small.name}")
                    break
        if "before" in found and "after" in found:
            r["real"] = found
        else:
            print(f"увага: у {folder} немає before/after — показую фото з ефектом «до»")


def derive(data):
    # на телефоні в рядок заголовка вміщається ~14 символів, довший переноситься
    for line in data["hero"]["title"]:
        text = html.unescape(re.sub(r"<[^>]+>", "", line["text"]))
        if len(text) + text.count("-") > 14:  # по дефісу браузер теж переносить
            print(f"увага: рядок заголовка «{text}» на телефоні перенесеться — скоротіть (до ~14 символів, дефіс рахується за два)")
    og = data["seo"]["og_image"]
    hex_ = data["accent"].lstrip("#")
    hours = data["hours"]
    data["_"] = {
        "accent_rgb": ",".join(str(int(hex_[i:i + 2], 16)) for i in (0, 2, 4)),
        "accent_url": "%23" + hex_,
        "solutions": json.dumps([p["solution"] for p in data["problems"]], ensure_ascii=False),
        "caps": json.dumps([[r["before"], r["after"]] for r in data["results"]], ensure_ascii=False),
        "hours": json.dumps(_week(hours), ensure_ascii=False),
        # OG-картинка: відносний шлях → повна адреса (Telegram, Facebook тощо потребують абсолютного URL)
        "og_image": og if og.startswith("http") or not data.get("site_url") else data["site_url"].rstrip("/") + "/" + og.lstrip("/"),
        # головне фото лежить локально → preload замість preconnect до Unsplash
        "local_photos": bool(_unsplash(data["hero"]["photo"]) and (LOCAL / f"{data['hero']['photo']}-1200.webp").exists()),
    }
    return data


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("client", help="JSON-файл клієнта, напр. clients/prime-detailing.json")
    ap.add_argument("--out", help="куди записати сайт (типово sites/<назва-файлу>/index.html)")
    args = ap.parse_args()

    client = Path(args.client)
    data = json.loads(client.read_text(encoding="utf-8"))
    _pairs(data, client.with_suffix(""))
    data = derive(data)
    page = render(parse((ROOT / "template.html").read_text(encoding="utf-8")), [data])

    out = Path(args.out) if args.out else ROOT / "sites" / client.stem / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")

    # власні фото клієнта: clients/<клієнт>/ копіюється поруч із сайтом
    assets = client.with_suffix("")
    if assets.is_dir():
        shutil.copytree(assets, out.parent, dirs_exist_ok=True)
    # локальні фото (images/…) — поруч із сайтом клієнта; для index.html у корені вони вже на місці
    if out.parent.resolve() != ROOT:
        for rel in sorted(USED):
            dst = out.parent / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, dst)
    print(f"готово: {out}")


if __name__ == "__main__":
    main()
