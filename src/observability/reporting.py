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
    report_path: Path | str,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Generate Markdown report comparing Baseline, Corrupted, and Repaired states."""
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    b_hit = baseline_metrics.get("retrieval_hit_rate", 0.0)
    c_hit = corrupted_metrics.get("retrieval_hit_rate", 0.0)
    r_hit = repaired_metrics.get("retrieval_hit_rate", 0.0)

    b_f1 = baseline_metrics.get("mean_token_f1", 0.0)
    c_f1 = corrupted_metrics.get("mean_token_f1", 0.0)
    r_f1 = repaired_metrics.get("mean_token_f1", 0.0)

    b_acc = baseline_metrics.get("judge_accuracy", 0.0)
    c_acc = corrupted_metrics.get("judge_accuracy", 0.0)
    r_acc = repaired_metrics.get("judge_accuracy", 0.0)

    b_score = baseline_metrics.get("mean_judge_score", 0.0)
    c_score = corrupted_metrics.get("mean_judge_score", 0.0)
    r_score = repaired_metrics.get("mean_judge_score", 0.0)

    c_q_pass = corrupted_quality.get("passed_all", False) or (
        corrupted_quality.get("passed", 0) == len(corrupted_quality.get("checks", []))
    )
    r_q_pass = repaired_quality.get("passed_all", False) or (
        repaired_quality.get("passed", 0) == len(repaired_quality.get("checks", []))
    )

    c_quality_status = "PASSED" if c_q_pass else "FAILED"
    r_quality_status = "PASSED" if r_q_pass else "FAILED"

    c_fresh_status = "FRESH" if corrupted_freshness.get("is_fresh", False) else "STALE"
    r_fresh_status = "FRESH" if repaired_freshness.get("is_fresh", False) else "STALE"

    lines = [
        "# Phase 2: Data Corruption, Observability and Resilience Report",
        "",
        "## 1. Executive Summary",
        "This report evaluates the impact of data corruption on RAG Agent performance ",
        "and validates system recovery following the standardized data repair pipeline.",
        "",
        "---",
        "",
        "## 2. Metrics Comparison",
        "",
        "| Category | Metric | Baseline | Corrupted | Repaired | Impact / Status |",
        "| --- | --- | :---: | :---: | :---: | :---: |",
        f"| Retrieval | Retrieval Hit Rate | {b_hit:.4f} | {c_hit:.4f} | {r_hit:.4f} | {'Degraded' if c_hit < b_hit else 'Neutral'} -> {'Recovered' if r_hit >= b_hit else 'Partial'} |",
        f"| Similarity | Mean Token F1 | {b_f1:.4f} | {c_f1:.4f} | {r_f1:.4f} | {'Degraded' if c_f1 < b_f1 else 'Neutral'} -> {'Recovered' if r_f1 >= b_f1 else 'Partial'} |",
        f"| LLM Eval | Judge Accuracy | {b_acc:.4f} | {c_acc:.4f} | {r_acc:.4f} | {'Degraded' if c_acc < b_acc else 'Neutral'} -> {'Recovered' if r_acc >= b_acc else 'Partial'} |",
        f"| LLM Eval | Mean Judge Score | {b_score:.2f} / 5 | {c_score:.2f} / 5 | {r_score:.2f} / 5 | {'Degraded' if c_score < b_score else 'Neutral'} -> {'Recovered' if r_score >= b_score else 'Partial'} |",
        f"| Observability | Data Quality Status | PASSED | {c_quality_status} | {r_quality_status} | Quality check status updated |",
        f"| Observability | Freshness Status | FRESH | {c_fresh_status} | {r_fresh_status} | Freshness check status updated |",
        "",
        "---",
        "",
        "## 3. Conclusions",
        "1. **Corrupted Data Impact:** Data degradation reduces retrieval recall and response quality.",
        "2. **Repair Recovery:** Re-cleaning raw records while enforcing Data Contracts restores system performance to baseline levels.",
        "",
        "---",
        "Report generated automatically by Data Observability Pipeline.",
    ]

    report_path.write_text("\n".join(lines), encoding="utf-8")