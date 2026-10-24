#!/usr/bin/env python3
"""Render the end-to-end diagram as a slide-shaped SVG.

The picture a reviewer sees has to fit one 16:9 frame, so the layout is a fixed grid rather than an
automatic graph layout: the request path and the product loop. No numbers live here — the diagram
answers "how does it work", measurements answer "how well".

    python3 scripts/diagram_end_to_end.py
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "diagrams" / "end-to-end.svg"

W, H = 1920, 1080
INK = "#111827"
MUTED = "#4b5563"
LINE = "#6b7280"
FONT = "'Inter','Helvetica Neue',Arial,sans-serif"

STYLES = {
    "bot": ("#eef2ff", "#3730a3", "#1e1b4b", 2, ""),
    "human": ("#fff1e6", "#c2410c", "#7c2d12", 2, ""),
    "kb": ("#ecfdf5", "#047857", "#064e3b", 2, ""),
    "gate": ("#fef9c3", "#a16207", "#713f12", 5, ""),
    "risk": ("#fdf2f8", "#be185d", "#831843", 2, ""),
    "off": ("#f3f4f6", "#6b7280", "#4b5563", 2, "6 6"),
}

TITLE = "Сквозной путь: сообщение → обоснованный ответ или человек"
SUBTITLE = "Путь вопроса и продуктовый контур · модель предлагает — код проверяет"


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(  # noqa: PLR0917 - a drawing helper mirrors SVG attribute order
    x: float,
    y: float,
    lines: list[str],
    size: int,
    color: str = INK,
    weight: int = 400,
    anchor: str = "middle",
) -> str:
    spans = "".join(
        f'<tspan x="{x}" dy="{0 if index == 0 else size + 6}">{esc(line)}</tspan>'
        for index, line in enumerate(lines)
    )
    return (
        f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" '
        f'fill="{color}" text-anchor="{anchor}">{spans}</text>'
    )


def box(  # noqa: PLR0917 - a drawing helper mirrors SVG attribute order
    x: float,
    y: float,
    w: float,
    h: float,
    lines: list[str],
    style: str,
    size: int = 24,
    subtitle: str | None = None,
) -> str:
    fill, stroke, ink, width, dash = STYLES[style]
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    body = (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" ry="16" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{width}"{dash_attr}/>'
    )
    total = len(lines) + (1 if subtitle else 0)
    block = total * (size + 6) - 6
    top = y + h / 2 - block / 2 + size
    out = [body, text(x + w / 2, top, lines, size, ink, 700)]
    if subtitle:
        out.append(text(x + w / 2, top + size + 12, [subtitle], size - 6, MUTED, 400))
    return "".join(out)


def arrow(
    points: list[tuple[float, float]], dashed: bool = False, head: bool = True
) -> str:
    path = " ".join(f'{"M" if index == 0 else "L"}{x},{y}' for index, (x, y) in enumerate(points))
    dash = ' stroke-dasharray="8 7"' if dashed else ""
    tip = ' marker-end="url(#tip)"' if head else ""
    return f'<path d="{path}" fill="none" stroke="{LINE}" stroke-width="3"{dash}{tip}/>'


def band(x: float, y: float, w: float, h: float, label: str) -> str:
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="20" fill="#f8fafc" '
        f'stroke="#e2e8f0"/>' + text(x + 28, y + 38, [label], 19, MUTED, 700, "start")
    )


def build() -> str:
    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
        f'font-family="{FONT}">',
        "<defs>"
        '<marker id="tip" markerWidth="13" markerHeight="11" refX="12" refY="5.5" orient="auto">'
        f'<path d="M0,0 L13,5.5 L0,11 z" fill="{LINE}"/></marker></defs>',
        f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
        text(70, 86, [TITLE], 42, INK, 700, "start"),
        text(70, 132, [SUBTITLE], 23, MUTED, 400, "start"),
    ]

    # --- row 1: the request path -------------------------------------------------------------
    parts.append(band(40, 170, 1840, 380, "ПУТЬ ВОПРОСА"))
    y, h = 250, 170
    mid = y + h / 2
    parts += [
        box(70, y, 150, h, ["Сотрудник", "MAX"], "human"),
        box(254, y, 200, h, ["Вебхук"], "bot", subtitle="дедуп · 200 сразу"),
        box(488, y, 170, h, ["Очередь", "воркер"], "bot"),
        box(692, y, 210, h, ["Поиск"], "kb", subtitle="ACL · вектор+лексика"),
        box(936, y, 170, h, ["Модель"], "bot", subtitle="промпт v7"),
        box(1140, y, 190, h, ["Проверка"], "gate", subtitle="цитата · conf ≥ 0.45"),
        box(1420, 246, 180, 76, ["Ответ с цитатами"], "bot", 18),
        box(1420, 348, 180, 76, ["Человек", "эскалация"], "human", 20),
        box(1640, y, 200, h, ["Доставка"], "bot", subtitle="outbox · 5 попыток"),
    ]
    for x1, x2 in ((220, 254), (454, 488), (658, 692), (902, 936), (1106, 1140)):
        parts.append(arrow([(x1, mid), (x2, mid)]))
    parts.append(arrow([(1330, mid), (1370, mid), (1370, 284), (1420, 284)]))
    parts.append(arrow([(1330, mid), (1370, mid), (1370, 386), (1420, 386)]))
    parts.append(arrow([(1600, 284), (1612, 284), (1612, mid)], head=False))
    parts.append(arrow([(1600, 386), (1612, 386), (1612, mid)], head=False))
    parts.append(arrow([(1612, mid), (1640, mid)]))

    parts.append(box(692, 448, 210, 76, ["База знаний"], "kb", 20, "HR: MD · PDF · OCR"))
    parts.append(arrow([(797, 448), (797, 420)], dashed=True))

    # --- row 2: the product loop --------------------------------------------------------------
    parts.append(band(40, 590, 1840, 300, "ПРОДУКТОВЫЙ КОНТУР"))
    y2, h2 = 650, 170
    parts += [
        box(70, y2, 230, h2, ["Сценарий"], "bot", 26, "шаг онбординга"),
        box(340, y2, 210, h2, ["Пульс-опросы"], "bot", 26),
        box(590, y2, 210, h2, ["Тональность"], "bot", 26, "prompt / jev"),
        box(840, y2, 210, h2, ["Риски"], "risk", 26, "теги · порог 8/10"),
        box(1090, y2, 230, h2, ["Кабинет"], "human", 26, "роли · скоупы SQL"),
        box(1360, y2, 300, h2, ["Рекрутёр отвечает"], "human", 23,
            "ответ идёт тем же outbox"),
    ]
    for x1, x2 in ((300, 340), (550, 590), (800, 840), (1050, 1090), (1320, 1360)):
        parts.append(arrow([(x1, y2 + h2 / 2), (x2, y2 + h2 / 2)]))

    # --- legend -------------------------------------------------------------------------------
    legend_y = 950
    parts.append(
        f'<rect x="40" y="{legend_y - 20}" width="1840" height="76" rx="16" fill="#ffffff" '
        f'stroke="#e2e8f0"/>'
    )
    swatches = [
        ("bot", 70, "бот и очередь"),
        ("kb", 300, "база знаний"),
        ("gate", 520, "проверка обоснованности"),
        ("human", 850, "человек"),
        ("risk", 1040, "риски"),
    ]
    for style, x, name in swatches:
        fill, stroke, _, _, _ = STYLES[style]
        parts.append(
            f'<rect x="{x}" y="{legend_y + 2}" width="24" height="24" rx="7" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="3"/>'
        )
        parts.append(text(x + 34, legend_y + 20, [name], 17, MUTED, 500, "start"))
    parts.append(arrow([(1360, legend_y + 14), (1414, legend_y + 14)]))
    parts.append(text(1424, legend_y + 20, ["работает сегодня"], 17, MUTED, 500, "start"))
    parts.append(arrow([(1590, legend_y + 14), (1644, legend_y + 14)], dashed=True))
    parts.append(text(1654, legend_y + 20, ["измерено, выключено"], 17, MUTED, 500, "start"))

    parts.append(
        text(60, 1044, ["Без цитаты из найденного фрагмента ответ не уходит. "
                        "BM25 и контекстный поиск измерены и выключены осознанно."],
             19, INK, 500, "start")
    )
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build(), encoding="utf-8")
    print(f"diagram: {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
