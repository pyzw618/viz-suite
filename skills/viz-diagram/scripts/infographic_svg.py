# -*- coding: utf-8 -*-
"""SVG 海报布局器。由 render_infographic.py 调用；共享折行/图标/颜色工具通过 r 传入。"""
import math

SVG_W, SVG_H = 1200, 1600
SVG_M = 72
BODY_TOP = 216
BODY_BOTTOM = 1500


class SVGCanvas:
    def __init__(self, spec, style, warnings, r):
        self.spec = spec
        self.style = style
        self.colors = style["colors"]
        self.fonts = style["fonts"]
        self.warnings = warnings
        self.r = r
        self.parts = []
        self.defs = []

    def add(self, markup):
        self.parts.append(markup)

    def rect(self, x, y, w, h, fill, stroke="none", sw=0, rx=0, extra=""):
        self.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
                 f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}" rx="{rx}" {extra}/>')

    def line(self, x1, y1, x2, y2, color, width=1, extra=""):
        self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                 f'stroke="{color}" stroke-width="{width}" {extra}/>')

    def text(self, x, y, text, size, color, weight="400", anchor="start",
             font=None, opacity=1.0, extra=""):
        font = font or self.fonts["body"]
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{self.r.esc(font)}" '
                 f'font-size="{size:.1f}" font-weight="{weight}" fill="{color}" '
                 f'text-anchor="{anchor}" opacity="{opacity}" {extra}>{self.r.esc(text)}</text>')

    def text_lines(self, lines, x, y, size, color, weight="400", anchor="start",
                   line_height=1.28, font=None, opacity=1.0):
        font = font or self.fonts["body"]
        for i, line in enumerate(lines):
            self.text(x, y + i * size * line_height, line, size, color, weight, anchor,
                      font=font, opacity=opacity)
        return y + len(lines) * size * line_height

    def text_block(self, text, x, y, width, height, max_size, min_size, color,
                   weight="400", anchor="start", font=None, max_lines=None,
                   line_height=1.28):
        size, lines = self.r.fit_text(text, width, height, max_size, min_size,
                                      line_height, max_lines)
        return self.text_lines(lines, x, y, size, color, weight, anchor, line_height, font)

    def icon(self, name, x, y, size, color):
        inner = self.r.svg_icon_inner(name, self.warnings)
        scale = size / 24
        self.add(f'<g transform="translate({x:.1f},{y:.1f}) scale({scale:.4f})" fill="none" '
                 f'stroke="{color}" stroke-width="2" stroke-linecap="round" '
                 f'stroke-linejoin="round">{inner}</g>')

    def svg(self):
        defs = "".join(self.defs)
        if defs:
            defs = f"<defs>{defs}</defs>"
        title = self.r.esc(self.spec["title"])
        claim = self.r.esc(self.spec["claim"])
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{SVG_W}" height="{SVG_H}" '
                f'viewBox="0 0 {SVG_W} {SVG_H}" role="img" '
                f'aria-labelledby="infographic-title infographic-desc">'
                f'<title id="infographic-title">{title}</title>'
                f'<desc id="infographic-desc">{claim}</desc>'
                f'{defs}{"".join(self.parts)}</svg>')


def svg_texture(cv):
    style = cv.style
    kind = style.get("texture", "none")
    if kind == "none":
        return
    color = cv.colors["ink"] if kind == "rules" else cv.colors["accent"]
    if kind == "rules":
        cv.defs.append('<pattern id="tex" width="32" height="32" patternUnits="userSpaceOnUse">'
                       f'<line x1="0" y1="31.5" x2="32" y2="31.5" stroke="{color}" '
                       f'stroke-opacity="0.06" stroke-width="1"/></pattern>')
    elif kind == "grid":
        cv.defs.append('<pattern id="tex" width="32" height="32" patternUnits="userSpaceOnUse">'
                       f'<path d="M32 0H0V32" fill="none" stroke="{color}" '
                       f'stroke-opacity="0.08" stroke-width="1"/></pattern>')
    else:
        cv.defs.append('<pattern id="tex" width="18" height="18" patternUnits="userSpaceOnUse">'
                       f'<circle cx="2" cy="2" r="1.2" fill="{color}" fill-opacity="0.09"/></pattern>')
    cv.rect(0, 0, SVG_W, SVG_H, "url(#tex)")


def svg_header(cv):
    spec, style, colors = cv.spec, cv.style, cv.colors
    cv.rect(0, 0, SVG_W, SVG_H, colors["bg"])
    svg_texture(cv)
    if style["id"] == "warm":
        cv.rect(SVG_M - 18, 22, SVG_W - 2 * (SVG_M - 18), 180, colors["surface"],
                colors["border"], 1, style.get("radius", 20))
    elif style["id"] == "technical":
        cv.line(SVG_M, 32, SVG_M, 196, colors["accent"], 4)
    elif style["id"] == "mckinsey":
        cv.rect(SVG_M, 30, SVG_W - 2 * SVG_M, 3, colors["accent"])
    elif style["id"] == "academic_blueprint":
        cv.line(SVG_M, 30, SVG_W - SVG_M, 30, colors["accent"], 2)
    else:
        cv.line(SVG_M, 32, SVG_W - SVG_M, 32, colors["accent"], 4)

    y = 52
    x = SVG_M + (14 if style["id"] == "technical" else 0)
    if spec.get("eyebrow"):
        cv.icon(spec.get("icon"), x, y - 14, 18, colors["accent"])
        cv.text(x + 26, y, spec["eyebrow"], style["sizes"]["micro"], colors["accent"],
                "700", font=cv.fonts["label"], extra='letter-spacing="1.4"')
    title_y = y + 16
    title_size, title_lines = cv.r.fit_text(
        spec["title"], SVG_W - 2 * SVG_M - 30, 96, style["sizes"]["title"], 32, 1.10, 2)
    y = cv.text_lines(title_lines, x, title_y + title_size * 0.82, title_size,
                      colors["ink"], "700", font=cv.fonts["display"], line_height=1.10)
    y += 8
    if spec.get("claim"):
        claim_size, claim_lines = cv.r.fit_text(
            spec["claim"], SVG_W - 2 * SVG_M - 60, 56, style["sizes"]["claim"], 18, 1.30, 2)
        cv.rect(x, y + 2, 4, len(claim_lines) * claim_size * 1.30, colors["accent"])
        y = cv.text_lines(claim_lines, x + 16, y + claim_size * 0.92, claim_size,
                          colors["ink"], "400", font=cv.fonts["body"], line_height=1.30)
        y += 6
    meta = "　｜　".join(p for p in [spec.get("subtitle"), spec.get("as_of")] if p)
    if meta:
        cv.text(x, y + 12, meta, style["sizes"]["small"], colors["muted"],
                font=cv.fonts["body"])
        y += 14
    return max(BODY_TOP, y + 20)


def svg_footer(cv):
    colors = cv.colors
    cv.line(SVG_M, 1530, SVG_W - SVG_M, 1530, colors["border"], 1)
    cv.text(SVG_M, 1558, cv.spec["source"], cv.style["sizes"]["micro"], colors["muted"])
    if cv.spec.get("footnote"):
        cv.text(SVG_W - SVG_M, 1558, cv.spec["footnote"], cv.style["sizes"]["micro"],
                colors["muted"], anchor="end")


def svg_card(cv, m, x, y, w, h, big_value=False, compact=False, watermark=False):
    colors, style = cv.colors, cv.style
    pad = 14 if compact else style.get("card_padding", 22)
    rx = style.get("radius", 0)
    cv.rect(x, y, w, h, colors["surface"], colors["border"], style.get("border_width", 1), rx)
    if style["id"] == "editorial":
        cv.rect(x, y, w, 4, colors["accent"])
    elif style["id"] == "technical":
        cv.rect(x, y, 4, h, colors["accent"])
    cursor = y + pad
    icon_size = 28 if compact else 34
    cv.icon(m.get("icon"), x + pad, cursor - 4, icon_size, colors["accent"])
    right_x = x + w - pad
    if m.get("value"):
        value_size = (style["sizes"]["value"] * 0.7) if big_value else (style["sizes"]["small"] * 1.4)
        value = m["value"] + (m.get("unit") or "")
        cv.text(right_x, cursor + value_size * 0.7, value, value_size, colors["ink"], "700",
                anchor="end", font=cv.fonts["display"],
                extra='font-variant-numeric="tabular-nums"')
    cursor += icon_size + 8
    if m.get("kicker"):
        cv.text(x + pad, cursor, m["kicker"], style["sizes"]["micro"], colors["accent"], "700",
                font=cv.fonts["label"], extra='letter-spacing="1.2"')
        cursor += style["sizes"]["micro"] + 8
    if m.get("label") and not m.get("kicker"):
        cv.text(x + pad, cursor, m["label"], style["sizes"]["micro"], colors["muted"], "700",
                font=cv.fonts["label"], extra='letter-spacing="1.0"')
        cursor += style["sizes"]["micro"] + 8
    if m.get("delta"):
        up = not str(m["delta"]).strip().startswith(("-", "↓", "−"))
        d_color = colors.get("positive", "#0F7B4D") if up else colors.get("negative", "#B42318")
        arrow = "↑" if up else "↓"
        cv.text(right_x, cursor - 4, f"{arrow} {m['delta'].lstrip('+-↑↓− ')}", 12, d_color, "700",
                anchor="end", font=cv.fonts["label"])
    title_size, title_lines = cv.r.fit_text(m["title"], w - 2 * pad, 54, 21, 15, 1.25, 2)
    cursor = cv.text_lines(title_lines, x + pad, cursor + title_size * 0.86, title_size,
                           colors["ink"], "700", font=cv.fonts["display"], line_height=1.25)
    cursor += 6
    if m.get("progress") is not None:
        p_val = max(0.0, min(100.0, float(m["progress"])))
        bar_w = w - 2 * pad
        cv.rect(x + pad, cursor, bar_w, 5, colors.get("surface2", "#E5E7EB"), rx=2)
        cv.rect(x + pad, cursor, bar_w * (p_val / 100.0), 5, colors["accent"], rx=2)
        cursor += 10
    body_space = max(12, y + h - pad - cursor)
    body_end = cursor
    if m.get("body"):
        body_size, body_lines = cv.r.fit_text(m["body"], w - 2 * pad, body_space, 16, 11, 1.35, 4)
        body_end = cv.text_lines(body_lines, x + pad, cursor + body_size * 0.92, body_size,
                                 colors["muted"], font=cv.fonts["body"], line_height=1.35)
    if m.get("tags"):
        tag_x = x + pad
        for tag in m["tags"][:3]:
            t_str = str(tag)
            t_w = len(t_str) * 9 + 12
            cv.rect(tag_x, body_end + 6, t_w, 18, colors.get("surface2", "#E5E7EB"), rx=3)
            cv.text(tag_x + t_w / 2, body_end + 18, t_str, 9, colors["muted"], "600",
                    anchor="middle", font=cv.fonts["body"])
            tag_x += t_w + 5
        body_end += 24
    if m.get("items"):
        item_y = body_end + 10
        for item in m["items"][:3]:
            cv.text(x + pad, item_y + 10, "·", 16, colors["accent"], "700")
            line = item["title"] + (("：" + item["body"]) if item.get("body") else "")
            size, lines = cv.r.fit_text(line, w - 2 * pad - 12, 22, 12, 9, 1.3, 1)
            cv.text(x + pad + 10, item_y + 10, lines[0] if lines else "", size,
                    colors["muted"], font=cv.fonts["body"])
            item_y += size * 1.45
    if watermark and h >= 240:
        inner = cv.r.svg_icon_inner(m.get("icon"), cv.warnings)
        ws = min(120, h * 0.34)
        cv.add(f'<g transform="translate({x + w - ws - 18:.1f},{y + h - ws - 18:.1f}) '
               f'scale({ws / 24:.4f})" fill="none" stroke="{colors["accent"]}" '
               f'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" '
               f'opacity="0.07">{inner}</g>')
    return y + h


def svg_list_grid(cv, top, height):
    modules = cv.spec["modules"]
    n = len(modules)
    cols = 2 if n <= 6 else 3
    rows = max(1, math.ceil(n / cols))
    gap = 16
    w = (SVG_W - 2 * SVG_M - gap * (cols - 1)) / cols
    h = (height - gap * (rows - 1)) / rows
    for i, m in enumerate(modules):
        r, c = divmod(i, cols)
        svg_card(cv, m, SVG_M + c * (w + gap), top + r * (h + gap), w, h,
                 big_value=True, watermark=True)


def svg_list_row(cv, top, height):
    modules = cv.spec["modules"]
    gap = 10
    h = (height - gap * (len(modules) - 1)) / max(1, len(modules))
    for i, m in enumerate(modules):
        y = top + i * (h + gap)
        x, w = SVG_M, SVG_W - 2 * SVG_M
        cv.rect(x, y, w, h, cv.colors["surface"], cv.colors["border"], 1,
                cv.style.get("radius", 0))
        cv.icon(m.get("icon"), x + 20, y + 18, 34, cv.colors["accent"])
        size, lines = cv.r.fit_text(m["title"], w - 260, 34, 22, 16, 1.2, 1)
        cv.text_lines(lines, x + 72, y + 30, size, cv.colors["ink"], "700",
                      font=cv.fonts["display"], line_height=1.2)
        if m.get("body"):
            bsize, blines = cv.r.fit_text(m["body"], w - 280, h - 54, 15, 11, 1.35, 2)
            cv.text_lines(blines, x + 72, y + 56 + bsize, bsize, cv.colors["muted"],
                          font=cv.fonts["body"], line_height=1.35)
        if m.get("value"):
            cv.text(x + w - 24, y + h / 2 + 12, m["value"] + (m.get("unit") or ""),
                    cv.style["sizes"]["value"] * 0.5, cv.colors["ink"], "700",
                    anchor="end", font=cv.fonts["display"])


def svg_sequence(cv, top, height):
    modules = cv.spec["modules"]
    n = len(modules)
    gap = 12
    h = (height - gap * (n - 1)) / max(1, n)
    line_x = SVG_M + 28
    cv.line(line_x, top + 34, line_x, top + height - 18, cv.colors["border"], 2)
    for i, m in enumerate(modules):
        y = top + i * (h + gap)
        cv.add(f'<circle cx="{line_x}" cy="{y + 28}" r="27" fill="{cv.colors["accent"]}"/>')
        cv.text(line_x, y + 36, f"{i + 1:02d}", 14, cv.colors["on_accent"], "700",
                anchor="middle", font=cv.fonts["label"])
        svg_card(cv, m, SVG_M + 74, y, SVG_W - 2 * SVG_M - 74, h)


def svg_timeline(cv, top, height):
    modules = cv.spec["modules"]
    n = len(modules)
    gap = 8
    h = (height - gap * (n - 1)) / max(1, n)
    line_x = SVG_M + 190
    cv.line(line_x, top + 12, line_x, top + height - 12, cv.colors["border"], 2)
    for i, m in enumerate(modules):
        y = top + i * (h + gap)
        cv.text(line_x - 24, y + 26, m.get("meta") or m.get("kicker") or "", 14,
                cv.colors["accent"], "700", anchor="end", font=cv.fonts["label"])
        cv.add(f'<circle cx="{line_x}" cy="{y + 20}" r="9" fill="{cv.colors["surface"]}" '
               f'stroke="{cv.colors["accent"]}" stroke-width="4"/>')
        svg_card(cv, m, line_x + 26, y, SVG_W - SVG_M - line_x - 26, h, compact=True)


def svg_pyramid(cv, top, height):
    modules = cv.spec["modules"]
    n = max(1, len(modules))
    gap = 6
    h = (height - gap * (n - 1)) / n
    center = SVG_W / 2
    for i, m in enumerate(modules):
        y = top + i * (h + gap)
        top_w = 300 + (SVG_W - 2 * SVG_M - 300) * i / n
        bottom_w = 300 + (SVG_W - 2 * SVG_M - 300) * (i + 1) / n
        tone = cv.r.mix(cv.colors["surface"], cv.colors["accent"],
                        0.06 + 0.10 * (n - i - 1) / max(1, n - 1))
        cv.add(f'<polygon points="{center - top_w / 2},{y} {center + top_w / 2},{y} '
               f'{center + bottom_w / 2},{y + h} {center - bottom_w / 2},{y + h}" '
               f'fill="{tone}" stroke="{cv.colors["border"]}" stroke-width="1"/>')
        text_x = center - bottom_w / 2 + 38
        cv.text(text_x, y + 24, f"L{i + 1}", 11, cv.colors["accent"], "700",
                font=cv.fonts["label"])
        size, lines = cv.r.fit_text(m["title"], bottom_w - 150, 32, 22, 15, 1.2, 1)
        cv.text_lines(lines, text_x, y + 48, size, cv.colors["ink"], "700",
                      font=cv.fonts["display"], line_height=1.2)
        if m.get("body"):
            bsize, blines = cv.r.fit_text(m["body"], bottom_w - 180, h - 58, 13, 10, 1.3, 2)
            cv.text_lines(blines, text_x, y + 52 + size + bsize, bsize, cv.colors["muted"],
                          font=cv.fonts["body"], line_height=1.3)
        if m.get("value"):
            cv.text(center + bottom_w / 2 - 34, y + h / 2 + 8,
                    m["value"] + (m.get("unit") or ""), cv.style["sizes"]["value"] * 0.38,
                    cv.colors["ink"], "700", anchor="end", font=cv.fonts["display"])


def svg_funnel(cv, top, height):
    modules = cv.spec["modules"]
    n = max(1, len(modules))
    gap = 8
    h = (height - gap * (n - 1)) / n
    max_w = SVG_W - 2 * SVG_M - 40
    for i, m in enumerate(modules):
        y = top + i * (h + gap)
        w = max_w * (1 - 0.5 * i / max(1, n - 1))
        x = (SVG_W - w) / 2
        tone = cv.r.mix(cv.colors["surface"], cv.colors["accent"],
                        0.10 + 0.10 * i / max(1, n - 1))
        cv.rect(x, y, w, h - 12, tone, cv.colors["border"], 1, cv.style.get("radius", 0))
        cv.text(x + 24, y + 28, m["title"], 18, cv.colors["ink"], "700",
                font=cv.fonts["display"])
        if m.get("body"):
            cv.text(x + 24, y + 50, m["body"], 12, cv.colors["muted"], font=cv.fonts["body"])
        if m.get("value"):
            cv.text(x + w - 24, y + 31, m["value"] + (m.get("unit") or ""), 30,
                    cv.colors["ink"], "700", anchor="end", font=cv.fonts["display"])
        if m.get("meta"):
            cv.text(SVG_W / 2, y + h - 1, m["meta"], 12, cv.colors["muted"],
                    anchor="middle", font=cv.fonts["label"])
        if i < n - 1:
            cv.text(SVG_W / 2, y + h + 3, "▼", 12, cv.colors["accent"], anchor="middle")


def svg_quadrant(cv, top, height):
    modules = cv.spec["modules"]
    left, right = SVG_M + 90, SVG_W - SVG_M - 30
    top_y, bottom_y = top + 20, top + height - 60
    cv.rect(SVG_M, top, SVG_W - 2 * SVG_M, height, cv.colors["surface"],
            cv.colors["border"], 1, cv.style.get("radius", 0))
    mid_x, mid_y = (left + right) / 2, (top_y + bottom_y) / 2
    cv.line(mid_x, top_y, mid_x, bottom_y, cv.colors["border"], 1)
    cv.line(left, mid_y, right, mid_y, cv.colors["border"], 1)
    x_label = cv.spec.get("x_label") or "维度 X →"
    y_label = cv.spec.get("y_label") or "维度 Y →"
    x_short = str(cv.spec.get("x_label") or "维度 X").replace("→", "").strip()
    y_short = str(cv.spec.get("y_label") or "维度 Y").replace("→", "").strip()
    for label, lx, ly, anchor in [
        (f"低 {x_short} · 高 {y_short}", left + 12, top_y + 22, "start"),
        (f"高 {x_short} · 高 {y_short}", right - 12, top_y + 22, "end"),
        (f"低 {x_short} · 低 {y_short}", left + 12, bottom_y - 12, "start"),
        (f"高 {x_short} · 低 {y_short}", right - 12, bottom_y - 12, "end"),
    ]:
        cv.text(lx, ly, label, 11, cv.colors["muted"], anchor=anchor, font=cv.fonts["label"])
    cv.text((left + right) / 2, bottom_y + 34, x_label, 12, cv.colors["muted"],
            anchor="middle", font=cv.fonts["label"])
    cv.text(left - 30, (top_y + bottom_y) / 2, y_label, 12, cv.colors["muted"],
            anchor="middle", font=cv.fonts["label"],
            extra=f'transform="rotate(-90 {left - 30:.1f} {(top_y + bottom_y) / 2:.1f})"')
    for m in modules:
        try:
            px = float(m.get("x", 50))
            py = float(m.get("y", 50))
        except (TypeError, ValueError):
            px, py = 50, 50
        px = max(3, min(97, px))
        py = max(3, min(97, py))
        x = left + (right - left) * px / 100
        y = bottom_y - (bottom_y - top_y) * py / 100
        try:
            size = max(9, min(22, 9 + float(m.get("size") or 12)))
        except (TypeError, ValueError):
            size = 14
        cv.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{size}" fill="{cv.colors["accent"]}" '
               f'stroke="{cv.colors["surface"]}" stroke-width="3"/>')
        align = "start" if x < mid_x else "end"
        tx = x + (size + 5 if align == "start" else -size - 5)
        cv.text(tx, y + 4, m["title"], 12, cv.colors["ink"], "700", anchor=align,
                font=cv.fonts["label"])
        if m.get("body"):
            cv.text(tx, y + 20, m["body"], 10, cv.colors["muted"], anchor=align)


def svg_compare(cv, top, height):
    modules = cv.spec["modules"]
    left = [m for m in modules if m.get("side") in ("left", "a", "before", "现状")]
    right = [m for m in modules if m.get("side") in ("right", "b", "after", "目标")]
    if not left and not right:
        mid = (len(modules) + 1) // 2
        left, right = modules[:mid], modules[mid:]
    gap = 20
    panel_w = (SVG_W - 2 * SVG_M - gap * 2 - 54) / 2
    panels = [
        (left, cv.spec["left_label"], "方案 A", SVG_M),
        (right, cv.spec["right_label"], "方案 B", SVG_M + panel_w + gap * 2 + 54),
    ]
    for mods, label, kicker, x in panels:
        cv.rect(x, top, panel_w, height, cv.colors["surface"], cv.colors["border"], 1,
                cv.style.get("radius", 0))
        cv.text(x + 20, top + 28, kicker, 11, cv.colors["muted"], "700",
                font=cv.fonts["label"])
        cv.text(x + 20, top + 58, label, 26, cv.colors["ink"], "700",
                font=cv.fonts["display"])
        row_h = min(160, (height - 110) / max(1, len(mods)))
        y = top + 96 + max(0, (height - 110 - row_h * len(mods)) / 2 - 20)
        for m in mods:
            cv.line(x + 20, y, x + panel_w - 20, y, cv.colors["border"], 1)
            cv.icon(m.get("icon"), x + 20, y + 14, 22, cv.colors["accent2"])
            size, lines = cv.r.fit_text(m["title"], panel_w - 76, 26, 15, 11, 1.2, 1)
            cv.text_lines(lines, x + 52, y + 28, size, cv.colors["ink"], "700",
                          font=cv.fonts["body"], line_height=1.2)
            if m.get("body"):
                bsize, blines = cv.r.fit_text(m["body"], panel_w - 76, row_h - 42, 11, 9, 1.3, 2)
                cv.text_lines(blines, x + 52, y + 44 + bsize, bsize, cv.colors["muted"],
                              font=cv.fonts["body"], line_height=1.3)
            y += row_h
    cx = SVG_W / 2
    cv.add(f'<circle cx="{cx}" cy="{top + height / 2}" r="26" fill="{cv.colors["accent"]}"/>')
    cv.text(cx, top + height / 2 + 5, "VS", 11, cv.colors["on_accent"], "700",
            anchor="middle", font=cv.fonts["label"])


def svg_hierarchy(cv, top, height):
    root = cv.spec["root"]
    children = root.get("children") or []
    root_w, root_h = 380, 84
    root_x = (SVG_W - root_w) / 2
    cv.rect(root_x, top + 6, root_w, root_h, cv.colors["accent"], "none", 0,
            cv.style.get("radius", 0))
    cv.icon(root.get("icon"), root_x + 20, top + 26, 26, cv.colors["on_accent"])
    cv.text(root_x + 58, top + 46, root["title"], 20, cv.colors["on_accent"], "700",
            font=cv.fonts["display"])
    if not children:
        return
    n = len(children)
    gap = 14
    child_w = (SVG_W - 2 * SVG_M - gap * (n - 1)) / n
    child_y = top + 150
    line_y = top + 110
    cv.line(SVG_W / 2, top + 90, SVG_W / 2, line_y, cv.colors["border"], 2)
    cv.line(SVG_M + child_w / 2, line_y, SVG_W - SVG_M - child_w / 2, line_y,
            cv.colors["border"], 2)

    has_sub = any(bool(c.get("children")) for c in children)
    if has_sub:
        tier1_h = 160
        for i, child in enumerate(children):
            x = SVG_M + i * (child_w + gap)
            cv.line(x + child_w / 2, line_y, x + child_w / 2, child_y, cv.colors["border"], 2)
            cv.rect(x, child_y, child_w, tier1_h, cv.colors["surface"], cv.colors["border"], 1,
                    cv.style.get("radius", 0))
            cv.icon(child.get("icon"), x + 16, child_y + 16, 24, cv.colors["accent"])
            size, lines = cv.r.fit_text(child["title"], child_w - 52, 38, 15, 11, 1.2, 2)
            cv.text_lines(lines, x + 48, child_y + 30, size, cv.colors["ink"], "700",
                          font=cv.fonts["body"], line_height=1.2)
            sub_children = child.get("children") or []
            if sub_children:
                sub_y = child_y + tier1_h + 24
                cv.line(x + child_w / 2, child_y + tier1_h, x + child_w / 2, sub_y, cv.colors["border"], 1.5)
                m_sub = len(sub_children)
                sub_h = min(120, (height - 360) / max(1, m_sub))
                for j, sub in enumerate(sub_children):
                    sy = sub_y + j * (sub_h + 8)
                    cv.rect(x + 6, sy, child_w - 12, sub_h, cv.colors.get("surface2", "#F3F4F6"),
                            cv.colors["border"], 1, cv.style.get("radius", 0))
                    cv.text(x + 14, sy + 20, sub.get("title", ""), 12, cv.colors["ink"], "700",
                            font=cv.fonts["body"])
                    if sub.get("body"):
                        bsize, blines = cv.r.fit_text(sub["body"], child_w - 28, sub_h - 28, 10, 8, 1.25, 2)
                        cv.text_lines(blines, x + 14, sy + 36, bsize, cv.colors["muted"],
                                      font=cv.fonts["body"], line_height=1.25)
    else:
        h = max(360, height - 190)
        for i, child in enumerate(children):
            x = SVG_M + i * (child_w + gap)
            cv.line(x + child_w / 2, line_y, x + child_w / 2, child_y, cv.colors["border"], 2)
            cv.rect(x, child_y, child_w, h, cv.colors["surface"], cv.colors["border"], 1,
                    cv.style.get("radius", 0))
            cv.icon(child.get("icon"), x + 16, child_y + 18, 26, cv.colors["accent"])
            size, lines = cv.r.fit_text(child["title"], child_w - 56, 44, 16, 11, 1.2, 2)
            cv.text_lines(lines, x + 50, child_y + 34, size, cv.colors["ink"], "700",
                          font=cv.fonts["body"], line_height=1.2)
            if child.get("body"):
                bsize, blines = cv.r.fit_text(child["body"], child_w - 32, 120, 12, 9, 1.35, 4)
                cv.text_lines(blines, x + 16, child_y + 70, bsize, cv.colors["muted"],
                              font=cv.fonts["body"], line_height=1.35)
            if child.get("items"):
                iy = child_y + 190
                for item in child["items"][:5]:
                    cv.text(x + 16, iy + 10, "·", 16, cv.colors["accent"], "700")
                    line_txt = item["title"] + (("：" + item["body"]) if item.get("body") else "")
                    isize, ilines = cv.r.fit_text(line_txt, child_w - 44, 24, 12, 9, 1.3, 1)
                    cv.text(x + 28, iy + 10, ilines[0] if ilines else "", isize,
                            cv.colors["muted"], font=cv.fonts["body"])
                    iy += isize * 1.5


def svg_mindmap(cv, top, height, cycle=False):
    modules = cv.spec["modules"]
    hub = cv.spec["hub"]
    cx, cy = SVG_W / 2, top + height / 2
    pos = cv.r.radial_positions(len(modules))
    span_x = SVG_W - 2 * SVG_M - 80
    span_y = height - 80
    for i, (px, py) in enumerate(pos):
        x = SVG_M + 40 + span_x * px / 100
        y = top + 40 + span_y * py / 100
        if cycle:
            nx, ny = pos[(i + 1) % len(pos)]
            ex = SVG_M + 40 + span_x * nx / 100
            ey = top + 40 + span_y * ny / 100
            mx, my = (x + ex) / 2, (y + ey) / 2
            cv.add(f'<path d="M{x:.1f} {y:.1f} Q{mx + (cx - mx) * 0.18:.1f} '
                   f'{my + (cy - my) * 0.18:.1f} {ex:.1f} {ey:.1f}" fill="none" '
                   f'stroke="{cv.colors["accent"]}" stroke-width="1.6" opacity="0.55" '
                   f'marker-end="url(#arrow)"/>')
        else:
            cv.add(f'<path d="M{cx:.1f} {cy:.1f} Q{cx + (x - cx) * 0.45:.1f} '
                   f'{cy + (y - cy) * 0.2:.1f} {x:.1f} {y:.1f}" fill="none" '
                   f'stroke="{cv.colors["accent"]}" stroke-width="1.6" opacity="0.55"/>')
        m = modules[i]
        w, h = 230, 104
        cv.rect(x - w / 2, y - h / 2, w, h, cv.colors["surface"], cv.colors["border"], 1,
                cv.style.get("radius", 0))
        cv.icon(m.get("icon"), x - w / 2 + 12, y - h / 2 + 14, 22, cv.colors["accent2"])
        size, lines = cv.r.fit_text(m["title"], w - 52, 30, 14, 10, 1.2, 2)
        cv.text_lines(lines, x - w / 2 + 40, y - h / 2 + 28, size, cv.colors["ink"], "700",
                      font=cv.fonts["body"], line_height=1.2)
        if m.get("body"):
            bsize, blines = cv.r.fit_text(m["body"], w - 24, h - 50, 10, 8, 1.3, 2)
            cv.text_lines(blines, x - w / 2 + 12, y - h / 2 + 58, bsize, cv.colors["muted"],
                          font=cv.fonts["body"], line_height=1.3)
    cv.add(f'<circle cx="{cx}" cy="{cy}" r="88" fill="{cv.colors["accent"]}"/>')
    cv.icon(hub.get("icon"), cx - 15, cy - 42, 30, cv.colors["on_accent"])
    size, lines = cv.r.fit_text(hub["title"], 150, 42, 18, 13, 1.2, 2)
    cv.text_lines(lines, cx, cy + 6, size, cv.colors["on_accent"], "700",
                  anchor="middle", font=cv.fonts["display"], line_height=1.2)


def svg_stat_cards(cv, top, height):
    modules = cv.spec["modules"]
    n = len(modules)
    cols = 2 if n <= 6 else 3
    rows = max(1, math.ceil(n / cols))
    gap = 16
    w = (SVG_W - 2 * SVG_M - gap * (cols - 1)) / cols
    h = (height - gap * (rows - 1)) / rows
    for i, m in enumerate(modules):
        r, c = divmod(i, cols)
        x, y = SVG_M + c * (w + gap), top + r * (h + gap)
        cv.rect(x, y, w, h, cv.colors["surface"], cv.colors["border"], 1,
                cv.style.get("radius", 0))
        cv.icon(m.get("icon"), x + 20, y + 20, 30, cv.colors["accent"])
        cv.text(x + w - 20, y + 28, m.get("label") or "", 11, cv.colors["muted"], "700",
                anchor="end", font=cv.fonts["label"], extra='letter-spacing="1.0"')
        value = m.get("value", "") + (m.get("unit") or "")
        cv.text(x + 20, y + 100, value, 56, cv.colors["ink"], "700",
                font=cv.fonts["display"], extra='font-variant-numeric="tabular-nums"')
        if m.get("delta"):
            up = not str(m["delta"]).strip().startswith(("-", "↓", "−"))
            cv.text(x + 20, y + 128, ("↑ " if up else "↓ ") + m["delta"].lstrip("+-↑↓− "),
                    14, cv.colors["positive"] if up else cv.colors["negative"], "700",
                    font=cv.fonts["label"])
        size, lines = cv.r.fit_text(m["title"], w - 40, 54, 17, 12, 1.25, 2)
        cv.text_lines(lines, x + 20, y + 160, size, cv.colors["ink"], "700",
                      font=cv.fonts["body"], line_height=1.25)
        if m.get("body"):
            bsize, blines = cv.r.fit_text(m["body"], w - 40, h - 190, 12, 9, 1.35, 3)
            cv.text_lines(blines, x + 20, y + 188, bsize, cv.colors["muted"],
                          font=cv.fonts["body"], line_height=1.35)


SVG_LAYOUTS = {
    "list-grid": svg_list_grid,
    "list-row": svg_list_row,
    "sequence-steps": svg_sequence,
    "timeline": svg_timeline,
    "pyramid": svg_pyramid,
    "funnel": svg_funnel,
    "quadrant": svg_quadrant,
    "compare-binary": svg_compare,
    "hierarchy-tree": svg_hierarchy,
    "mindmap": lambda cv, top, height: svg_mindmap(cv, top, height, cycle=False),
    "cycle": lambda cv, top, height: svg_mindmap(cv, top, height, cycle=True),
    "stat-cards": svg_stat_cards,
}


def render_svg(spec, style, warnings, r):
    cv = SVGCanvas(spec, style, warnings, r)
    cv.defs.append('<marker id="arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" '
                   'orient="auto">'
                   f'<path d="M0 0 L6 3 L0 6 z" fill="{cv.colors["accent"]}"/></marker>')
    body_top = svg_header(cv)
    body_height = BODY_BOTTOM - body_top
    SVG_LAYOUTS[spec["layout"]](cv, body_top, body_height)
    svg_footer(cv)
    return cv.svg()
