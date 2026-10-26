# /// script
# requires-python = ">=3.10"
# dependencies = ["Pillow>=10"]
# ///
# -*- coding: utf-8 -*-
"""Stage 5 端到端套件校验：12 个任务、输入/输出、路由矩阵与技能覆盖。

只校验已固化产物，不重新渲染；每个任务的复现命令见任务 README。
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TASKS = HERE / "tasks"


def rel(path: str) -> Path:
    return ROOT / path


def main() -> int:
    task_dirs = sorted(p for p in TASKS.iterdir() if p.is_dir())
    matrix = json.loads((HERE / "routing-matrix.json").read_text(encoding="utf-8"))
    by_task = {c["task_id"]: c for c in matrix["cases"]}
    details = []
    missing = []
    statuses = []
    for td in task_dirs:
        task = json.loads((td / "task.json").read_text(encoding="utf-8"))
        task_missing = [p for p in task["inputs"] + task["outputs"] if not rel(p).is_file()]
        missing.extend(task_missing)
        route = task["route"]
        matrix_case = by_task.get(task["id"])
        route_ok = True
        if matrix_case is None:
            route_ok = False
        else:
            expected = matrix_case["expected"]
            route_ok = (expected["primary"] == route["primary"]
                        and expected["scenes"] == route["scenes"]
                        and set(expected["support"]).issubset(set(route["support"]))
                        and not (set(matrix_case["must_not"]) & ({route["primary"]} | set(route["scenes"]))))
        # 读取可用的脚本级 JSON 状态
        evidence = {}
        for name in ("render.json", "audit.json", "lint.json", "layout.json", "capture.json"):
            p = td / name
            if p.is_file():
                try:
                    evidence[name] = json.loads(p.read_text(encoding="utf-8")).get("status", "unknown")
                except json.JSONDecodeError:
                    evidence[name] = "invalid-json"
        ok = not task_missing and route_ok
        statuses.append(ok)
        details.append({"id": task["id"], "title": task["title"], "pass": ok,
                        "route_ok": route_ok, "missing": task_missing,
                        "outputs": len(task["outputs"]), "evidence": evidence})

    coverage = set()
    scene_coverage = set()
    for td in task_dirs:
        route = json.loads((td / "task.json").read_text(encoding="utf-8"))["route"]
        if route["primary"].startswith("viz-"):
            coverage.add(route["primary"])
        scene_coverage.update(route["scenes"])
        coverage.update(s for s in route["support"] if s.startswith("viz-"))
    expected_skills = {"viz-figure", "viz-interactive", "viz-diagram"}
    expected_scenes = {"academic", "bi", "story", "geo"}
    missing_entrypoints = [
        p for p in ("skills/SKILL.md", "skills/viz-figure/SKILL.md",
                    "skills/viz-interactive/SKILL.md", "skills/viz-diagram/SKILL.md")
        if not rel(p).is_file()
    ]
    missing_scene_files = [
        f"skills/shared/assets/scenes/{sc}.json" for sc in sorted(expected_scenes)
        if not rel(f"skills/shared/assets/scenes/{sc}.json").is_file()
    ]
    missing.extend(missing_entrypoints + missing_scene_files)
    missing_skills = sorted((expected_skills - coverage) | (expected_scenes - scene_coverage))
    result = {
        "status": "success" if all(statuses) and not missing and not missing_skills else "partial",
        "tasks": len(task_dirs),
        "passed": sum(statuses),
        "missing": missing,
        "skill_coverage": sorted(coverage),
        "scene_coverage": sorted(scene_coverage),
        "missing_skills": missing_skills,
        "routing": {"cases": len(matrix["cases"]), "negative_cases": len(matrix["negative_cases"]),
                    "task_routes_consistent": all(d["route_ok"] for d in details)},
        "details": details,
    }
    (HERE / "results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                       encoding="utf-8")

    # 4×3 接触表
    picks = [
        ("01", rel("examples/golden-runs/end-to-end/tasks/01-academic-multipanel/outputs/fig-academic-multipanel_300dpi.png")),
        ("02", rel("examples/golden-runs/scene-gate3/bi/shots/index_desktop.png")),
        ("03", rel("examples/golden-runs/end-to-end/tasks/03-retro-infographic/shots/retro_desktop.png")),
        ("04", rel("examples/golden-runs/end-to-end/tasks/04-reverse-rebrand/outputs/branded_300dpi.png")),
        ("05", rel("examples/golden-runs/end-to-end/tasks/05-ugly-chart-fix/outputs/after_300dpi.png")),
        ("06", rel("examples/golden-runs/end-to-end/tasks/06-analysis-to-pdf/outputs/chart_300dpi.png")),
        ("07", rel("examples/golden-runs/scene-gate3/academic/outputs/fig-ab-conversion_300dpi.png")),
        ("08", rel("examples/golden-runs/end-to-end/tasks/08-geo-grid-map/outputs/geo-grid_300dpi.png")),
        ("09", rel("examples/golden-runs/scene-gate3/story/outputs/story-revenue-shift_300dpi.png")),
        ("10", rel("examples/golden-runs/end-to-end/tasks/10-technical-infographic/shots/pipeline_desktop.png")),
        ("11", rel("examples/golden-runs/reverse-benchmark/reverse-output/contact.png")),
        ("12", rel("examples/golden-runs/reverse-benchmark/images/pie_3d.png")),
    ]
    thumbs = []
    for label, path in picks:
        if not path.is_file():
            continue
        im = Image.open(path).convert("RGB")
        tw, th = 300, 200
        thumb = ImageOps.contain(im, (tw, th), Image.LANCZOS)
        tile = Image.new("RGB", (tw, th), "white")
        tile.paste(thumb, ((tw - thumb.width) // 2, (th - thumb.height) // 2))
        thumbs.append((label, tile, th))
    if thumbs:
        cols, gap, label_h = 4, 12, 24
        rows = (len(thumbs) + cols - 1) // cols
        cell_w = 300 + gap
        cell_h = max(h for _, _, h in thumbs) + label_h + gap
        font = ImageFont.truetype(r"C:/Windows/Fonts/msyh.ttc", 16)
        sheet = Image.new("RGB", (cols * cell_w + gap, rows * cell_h + gap), "white")
        draw = ImageDraw.Draw(sheet)
        for i, (label, im, h) in enumerate(thumbs):
            x = gap + (i % cols) * cell_w
            y = gap + (i // cols) * cell_h
            sheet.paste(im, (x, y))
            draw.text((x, y + h + 4), f"任务 {label}", fill="black", font=font)
        sheet.save(HERE / "contact.png")
    print(json.dumps({k: result[k] for k in ("status", "tasks", "passed", "missing", "skill_coverage", "scene_coverage", "missing_skills", "routing")},
                     ensure_ascii=False, indent=2))
    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
