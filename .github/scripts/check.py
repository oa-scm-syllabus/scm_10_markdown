#!/usr/bin/env python3
"""Automatická kontrola zadání cvičení 01: Markdown pro classroom50.

Kontroluje strukturu dvou deliverable souborů (project_readme.md, it_markdown_practice.md)
podle požadavků v ukol-a-projekt.md a ukol-b-volne-tema.md. Nehodnotí obsah/téma,
jen přítomnost požadovaných markdown prvků.

Výstup: JSON na stdout (a volitelně do souboru), exit kód 0 = vše splněno, 1 = ne.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Callable, NamedTuple


class FileContext:
    """Obsah souboru s variantou bez fenced code bloků (pro spolehlivé regexy)."""

    def __init__(self, raw: str) -> None:
        self.raw = raw
        self.no_code = strip_code_blocks(raw)


CheckFn = Callable[[FileContext], bool]


class Requirement(NamedTuple):
    id: str
    description: str
    check: CheckFn


def strip_code_blocks(text: str) -> str:
    def repl(match: re.Match) -> str:
        return "\n" * match.group(0).count("\n")

    return re.sub(r"```.*?```", repl, text, flags=re.DOTALL)


def find_code_blocks(text: str) -> list[tuple[str, str]]:
    return re.findall(r"```([^\n`]*)\n(.*?)```", text, flags=re.DOTALL)


def find_headings(text: str) -> list[tuple[int, str]]:
    return [
        (len(m.group(1)), m.group(2).strip())
        for m in re.finditer(r"^(#{1,6})\s+(.+)$", text, re.MULTILINE)
    ]


def find_blockquote_groups(text: str) -> list[int]:
    groups: list[int] = []
    current = 0
    for line in text.splitlines():
        if re.match(r"^\s*>", line):
            current += 1
        else:
            if current:
                groups.append(current)
            current = 0
    if current:
        groups.append(current)
    return groups


def find_tables(text: str) -> list[dict]:
    lines = text.splitlines()
    sep_re = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$")
    tables = []
    i = 0
    while i < len(lines) - 1:
        header, sep = lines[i], lines[i + 1]
        if "|" in header and sep_re.match(sep):
            cols = len([c for c in header.strip().strip("|").split("|")])
            rows = 0
            j = i + 2
            while j < len(lines) and "|" in lines[j] and lines[j].strip() != "":
                rows += 1
                j += 1
            tables.append({"cols": cols, "rows": rows})
            i = j
        else:
            i += 1
    return tables


def check_bold(text: str) -> bool:
    return bool(re.search(r"\*\*[^\n*]+\*\*", text) or re.search(r"__[^\n_]+__", text))


def check_italic(text: str) -> bool:
    return bool(
        re.search(r"(?<!\*)\*(?!\*)[^\n*]+(?<!\*)\*(?!\*)", text)
        or re.search(r"(?<!_)_(?!_)[^\n_]+(?<!_)_(?!_)", text)
    )


def check_strikethrough(text: str) -> bool:
    return bool(re.search(r"~~[^\n~]+~~", text))


def check_formatting_all(ctx: FileContext) -> bool:
    return check_bold(ctx.no_code) and check_italic(ctx.no_code) and check_strikethrough(ctx.no_code)


def check_headings_h1_and_more(ctx: FileContext) -> bool:
    levels = {lvl for lvl, _ in find_headings(ctx.no_code)}
    return 1 in levels and ({2, 3} & levels)


def check_headings_h1_h2_h3(ctx: FileContext) -> bool:
    levels = {lvl for lvl, _ in find_headings(ctx.no_code)}
    return {1, 2, 3}.issubset(levels)


def check_anchor_link(ctx: FileContext) -> bool:
    return bool(re.search(r"\[[^\]]+\]\(#[^)]+\)", ctx.no_code))


def check_unordered_min(min_items: int, require_nested: bool = False) -> CheckFn:
    def fn(ctx: FileContext) -> bool:
        lines = ctx.no_code.splitlines()
        top_items = [l for l in lines if re.match(r"^[-*+]\s+\S", l)]
        if len(top_items) < min_items:
            return False
        if not require_nested:
            return True
        return any(
            re.match(r"^[ \t]{2,}[-*+]\s+\S", l) or re.match(r"^[ \t]{2,}\d+\.\s+\S", l)
            for l in lines
        )

    return fn


def check_ordered_min(min_items: int) -> CheckFn:
    def fn(ctx: FileContext) -> bool:
        top_items = [l for l in ctx.no_code.splitlines() if re.match(r"^\d+\.\s+\S", l)]
        return len(top_items) >= min_items

    return fn


def check_nested_ordered_in_unordered(ctx: FileContext) -> bool:
    lines = ctx.no_code.splitlines()
    for idx, line in enumerate(lines):
        if not re.match(r"^[-*+]\s+\S", line):
            continue
        j = idx + 1
        while j < len(lines):
            nxt = lines[j]
            if re.match(r"^[ \t]{2,}\d+\.\s+\S", nxt):
                return True
            if re.match(r"^[-*+]\s+\S", nxt) or re.match(r"^\d+\.\s+\S", nxt):
                break
            if nxt.strip() == "":
                j += 1
                continue
            if not nxt.startswith((" ", "\t")):
                break
            j += 1
    return False


def check_links_inline_and_reference(ctx: FileContext) -> bool:
    inline = re.search(r"(?<!!)\[[^\]]+\]\([^)]+\)", ctx.no_code)
    reference = re.search(r"(?<!!)\[[^\]]+\]\[[^\]]+\]", ctx.no_code)
    definition = re.search(r"^\s*\[[^\]]+\]:\s*\S+", ctx.no_code, re.MULTILINE)
    return bool(inline) and bool(reference) and bool(definition)


def check_images_inline_and_reference(ctx: FileContext) -> bool:
    inline = re.search(r"!\[[^\]]*\]\([^)]+\)", ctx.no_code)
    reference = re.search(r"!\[[^\]]*\]\[[^\]]+\]", ctx.no_code)
    definition = re.search(r"^\s*\[[^\]]+\]:\s*\S+", ctx.no_code, re.MULTILINE)
    return bool(inline) and bool(reference) and bool(definition)


def check_code_block_and_inline(require_lang: set[str] | None = None) -> CheckFn:
    def fn(ctx: FileContext) -> bool:
        blocks = find_code_blocks(ctx.raw)
        if not blocks:
            return False
        if require_lang is not None:
            if not any(lang.strip().lower() in require_lang for lang, _ in blocks):
                return False
        inline = re.search(r"(?<!`)`[^`\n]+`(?!`)", ctx.no_code)
        return bool(inline)

    return fn


def check_table(min_cols: int, min_rows: int) -> CheckFn:
    def fn(ctx: FileContext) -> bool:
        return any(
            t["cols"] >= min_cols and t["rows"] >= min_rows for t in find_tables(ctx.no_code)
        )

    return fn


def check_blockquote_any(ctx: FileContext) -> bool:
    return bool(find_blockquote_groups(ctx.no_code))


def check_blockquote_single_and_multi(ctx: FileContext) -> bool:
    groups = find_blockquote_groups(ctx.no_code)
    return any(g == 1 for g in groups) and any(g >= 2 for g in groups)


def check_details_block(ctx: FileContext) -> bool:
    t = ctx.raw.lower()
    return "<details>" in t and "</details>" in t and "<summary>" in t


def check_checkboxes(min_items: int, mixed: bool = True) -> CheckFn:
    def fn(ctx: FileContext) -> bool:
        unchecked = re.findall(r"^\s*[-*+]\s+\[\s?\]\s+\S", ctx.no_code, re.MULTILINE)
        checked = re.findall(r"^\s*[-*+]\s+\[[xX]\]\s+\S", ctx.no_code, re.MULTILINE)
        if len(unchecked) + len(checked) < min_items:
            return False
        if mixed and not (unchecked and checked):
            return False
        return True

    return fn


def check_hr(ctx: FileContext) -> bool:
    for line in ctx.no_code.splitlines():
        s = line.strip()
        if re.fullmatch(r"-{3,}", s) or re.fullmatch(r"\*{3,}", s) or re.fullmatch(r"_{3,}", s):
            return True
    return False


def check_footnote(ctx: FileContext) -> bool:
    refs = re.findall(r"\[\^[^\]]+\]", ctx.no_code)
    defs = re.findall(r"^\s*\[\^[^\]]+\]:", ctx.no_code, re.MULTILINE)
    return bool(defs) and len(refs) > len(defs)


def check_no_todo(ctx: FileContext) -> bool:
    return "<!-- TODO" not in ctx.raw and "<!--TODO" not in ctx.raw


REQUIREMENTS_A: list[Requirement] = [
    Requirement("a1_headings", "Nadpisy: H1 a alespoň jedna další úroveň (H2 nebo H3)", check_headings_h1_and_more),
    Requirement("a2_formatting", "Tučný text, kurzíva i přeškrtnutý text", check_formatting_all),
    Requirement("a3_anchor", "Odkaz s kotvou (anchor) na sekci v dokumentu", check_anchor_link),
    Requirement(
        "a4_unordered_list",
        "Nečíslovaný seznam s min. 4 položkami a vnořeným podseznamem",
        check_unordered_min(4, require_nested=True),
    ),
    Requirement("a5_ordered_list", "Číslovaný seznam s min. 3 položkami", check_ordered_min(3)),
    Requirement(
        "a6_code",
        "Blok kódu se zvýrazněním syntaxe bash a inline kód",
        check_code_block_and_inline(require_lang={"bash", "sh", "shell"}),
    ),
    Requirement("a7_images", "Inline i reference obrázek", check_images_inline_and_reference),
    Requirement("a8_links", "Inline i reference odkaz", check_links_inline_and_reference),
    Requirement("a9_table", "Tabulka s min. 2 sloupci a 3 řádky", check_table(2, 3)),
    Requirement("a10_quote", "Citace (blockquote)", check_blockquote_any),
    Requirement("a11_details", "Sbalitelný blok <details><summary>", check_details_block),
    Requirement(
        "a12_checkboxes",
        "Checkbox seznam s min. 3 položkami, zaškrtnutými i nezaškrtnutými",
        check_checkboxes(3, mixed=True),
    ),
    Requirement("a13_hr", "Horizontální čára", check_hr),
    Requirement("a14_footnote", "Poznámka pod čarou (footnote)", check_footnote),
    Requirement("a15_no_todo", "V souboru nezůstala žádná značka <!-- TODO -->", check_no_todo),
]

REQUIREMENTS_B: list[Requirement] = [
    Requirement("b1_headings", "Nadpisy H1 až H3", check_headings_h1_h2_h3),
    Requirement("b2_formatting", "Tučný text, kurzíva i přeškrtnutý text", check_formatting_all),
    Requirement("b3_unordered_list", "Nečíslovaný seznam s min. 3 položkami", check_unordered_min(3)),
    Requirement("b4_ordered_list", "Číslovaný seznam s min. 3 položkami", check_ordered_min(3)),
    Requirement(
        "b5_nested_list",
        "Vnořený číslovaný podseznam uvnitř položky nečíslovaného seznamu",
        check_nested_ordered_in_unordered,
    ),
    Requirement("b6_links", "Inline i reference odkaz", check_links_inline_and_reference),
    Requirement("b7_images", "Inline i reference obrázek", check_images_inline_and_reference),
    Requirement(
        "b8_quotes",
        "Jednořádková i víceřádková citace",
        check_blockquote_single_and_multi,
    ),
    Requirement("b9_code", "Blok kódu a inline kód", check_code_block_and_inline()),
    Requirement("b10_table", "Tabulka s min. 2 sloupci a 3 řádky", check_table(2, 3)),
    Requirement("b11_hr", "Horizontální čára", check_hr),
    Requirement(
        "b12_checkboxes",
        "Checkbox seznam se zaškrtnutými i nezaškrtnutými položkami",
        check_checkboxes(2, mixed=True),
    ),
]


def run_checks(path: Path, requirements: list[Requirement]) -> dict:
    exists = path.exists()
    if not exists:
        return {
            "file": str(path),
            "exists": False,
            "requirements": [
                {"id": r.id, "description": r.description, "passed": False, "note": "Soubor neexistuje"}
                for r in requirements
            ],
            "passed": False,
        }

    ctx = FileContext(path.read_text(encoding="utf-8"))
    results = []
    all_passed = True
    for r in requirements:
        try:
            passed = bool(r.check(ctx))
        except Exception:
            passed = False
        results.append({"id": r.id, "description": r.description, "passed": passed})
        all_passed = all_passed and passed

    return {"file": str(path), "exists": True, "requirements": results, "passed": all_passed}


def render_summary_markdown(result: dict) -> str:
    lines = ["# Výsledek kontroly zadání Markdown", ""]
    for task in result["tasks"]:
        lines.append(f"## {task['name']} (`{task['file']}`)")
        lines.append("")
        if not task["exists"]:
            lines.append(f"Soubor `{task['file']}` neexistuje.")
            lines.append("")
            continue
        lines.append("| Stav | Požadavek |")
        lines.append("|------|-----------|")
        for req in task["requirements"]:
            mark = "OK" if req["passed"] else "CHYBA"
            lines.append(f"| {mark} | {req['description']} |")
        lines.append("")
    overall = "Splněno" if result["passed"] else "Nesplněno"
    lines.append(f"**Celkový výsledek: {overall}**")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-readme", default="project_readme.md")
    parser.add_argument("--practice-file", default="it_markdown_practice.md")
    parser.add_argument("--output", default=None, help="Cesta pro uložení JSON výstupu")
    parser.add_argument("--summary-output", default=None, help="Cesta pro uložení markdown shrnutí")
    args = parser.parse_args()

    task_a = run_checks(Path(args.project_readme), REQUIREMENTS_A)
    task_b = run_checks(Path(args.practice_file), REQUIREMENTS_B)

    result = {
        "tasks": [
            {"id": "ukol-a", "name": "Úkol A - pevný scénář", **task_a},
            {"id": "ukol-b", "name": "Úkol B - volné téma", **task_b},
        ],
        "passed": task_a["passed"] and task_b["passed"],
    }

    output_json = json.dumps(result, ensure_ascii=False, indent=2)
    print(output_json)

    if args.output:
        Path(args.output).write_text(output_json, encoding="utf-8")

    if args.summary_output:
        Path(args.summary_output).write_text(render_summary_markdown(result), encoding="utf-8")

    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
