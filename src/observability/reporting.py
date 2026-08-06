from __future__ import annotations

from pathlib import Path
from typing import Any

from core.utils import now_utc, write_text

METRIC_LABELS = {
    "samples": "So sample",
    "retrieval_hit_rate": "Retrieval hit rate",
    "mean_token_f1": "Mean token F1",
    "judge_accuracy": "Judge accuracy",
    "mean_judge_score": "Mean judge score",
}


def _format_value(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.3f}"
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value) if value else "-"
    return str(value)


def _kv_table(payload: dict[str, Any], labels: dict[str, str] | None = None) -> list[str]:
    labels = labels or {}
    lines = ["| Field | Value |", "| --- | --- |"]
    for key, value in payload.items():
        if isinstance(value, (dict, list)) and key not in {"failed_checks"}:
            continue
        lines.append(f"| `{labels.get(key, key)}` | {_format_value(value)} |")
    return lines


def _quality_section(quality: dict[str, Any]) -> list[str]:
    checks = quality.get("checks", [])
    status = "PASS" if quality.get("success") else "FAIL"
    lines = [
        f"- Ket qua tong: **{status}** ({quality.get('passed', '?')}/{len(checks)} check pass)",
        f"- Total rows: {_format_value(quality.get('total_rows'))}",
        f"- Report: `{quality.get('report_path', 'n/a')}`",
        "",
        "| Check | Ket qua | Observed | Expected | Chi tiet |",
        "| --- | --- | --- | --- | --- |",
    ]
    for check in checks:
        mark = "PASS" if check.get("success") else "**FAIL**"
        lines.append(
            f"| `{check.get('name')}` | {mark} | {_format_value(check.get('observed'))} "
            f"| {check.get('expected', '')} | {check.get('details', '')} |"
        )
    return lines


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Viet markdown report cho baseline phase tu artifact that.

    Moi con so trong report deu doc tu payload duoc truyen vao (metrics/quality/freshness JSON),
    khong hard-code, de report luon khop artifact.
    """
    lines: list[str] = [
        "# Phase 1 - Baseline Report",
        "",
        f"Generated at: {now_utc().isoformat()}",
        "",
        "## 1. Source & scope",
        "",
        *_kv_table(source_summary),
        "",
        "## 2. Evaluation metrics",
        "",
        *_kv_table({key: metrics.get(key) for key in METRIC_LABELS if key in metrics}, METRIC_LABELS),
        "",
    ]

    ragas = metrics.get("ragas")
    if isinstance(ragas, dict):
        if "skipped" in ragas:
            lines += [f"> Ragas: skipped - {ragas['skipped']}", ""]
        elif "error" in ragas:
            lines += [f"> Ragas: error - {ragas['error']}", ""]
        else:
            lines += _kv_table(ragas) + [""]

    lines += [
        "## 3. Data quality",
        "",
        *_quality_section(quality),
        "",
        "## 4. Freshness",
        "",
        *_kv_table(freshness),
        "",
        "## 5. Evidence & limitations",
        "",
        "- Metrics doc tu artifact JSON do evaluator ghi ra; report nay khong tinh lai so lieu.",
        "- Kiem tra `judge.reasoning` trong answers: neu la fallback heuristic thi `judge_accuracy` "
        "khong phai LLM judge.",
        "- Test set duoc khoa va dung lai nguyen ven cho corrupted/repaired.",
        "",
    ]

    write_text(Path(report_path), "\n".join(lines))


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """TODO(student): viet markdown report so sanh baseline/corrupted/repaired."""
    raise NotImplementedError("Student task: implement corruption comparison report.")
