from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings, load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.retrieval_probe import evaluate_retrieval
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import audit_index_manifest, build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def _freshness_path(settings: Settings, state: str) -> Path:
    """Baseline giu nguyen `freshness_report.json`; corrupted/repaired ghi file rieng."""
    if state == "baseline":
        return settings.paths.freshness_report
    return settings.paths.quality_dir / f"freshness_report_{state}.json"


def _probe_path(settings: Settings, state: str) -> Path:
    return settings.paths.baseline_metrics.with_name(f"retrieval_probe_{state}.json")


def _judge_integrity(answers_path: Path) -> dict[str, int]:
    """Dem so sample bi `_judge_answer` chuyen sang heuristic vi LLM khong goi duoc.

    Fallback la im lang trong `metrics.py`, nen phai dem lai tu answers moi biet
    `judge_accuracy` co con la LLM judge hay khong.
    """
    answers = read_json(answers_path)
    fallback = sum(1 for item in answers if "Fallback heuristic" in item.get("judge", {}).get("reasoning", ""))
    return {"total": len(answers), "fallback": fallback}


def _write_state_frame(df: pd.DataFrame, csv_path: Path, json_path: Path) -> None:
    write_csv(df, csv_path)
    write_json(json_path, json.loads(df.to_json(orient="records", date_format="iso")))


def evaluate_state(
    settings: Settings,
    df: pd.DataFrame,
    state: str,
    embeddings_path: Path,
    metrics_path: Path,
    answers_path: Path,
) -> dict[str, Any]:
    """Build index rieng cho `state`, evaluate bang test set da khoa, chay quality/freshness.

    Test set khong bao gio duoc sinh lai o day: baseline, corrupted va repaired phai dung
    dung `data/eval/test_set.json` thi so sanh ba trang thai moi cong bang.
    """
    index = LocalEmbeddingIndex.build(df, settings, embeddings_output_path=embeddings_path)
    audit = audit_index_manifest(settings, embeddings_path, df)

    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=metrics_path,
        answers_output_path=answers_path,
    )

    quality = run_data_quality_checks(df, settings, state)
    freshness = build_freshness_report(df, settings, _freshness_path(settings, state))

    probe_path = settings.paths.eval_testset.with_name("test_set_retrieval_probe.json")
    probe: dict[str, Any] | None = None
    if probe_path.exists():
        probe = evaluate_retrieval(read_json(probe_path), index, settings)
        write_json(_probe_path(settings, state), probe)

    return {
        "state": state,
        "rows": len(df),
        "metrics": bundle.summary,
        "quality": quality,
        "freshness": freshness,
        "probe": probe,
        "index_audit": audit,
    }


def main() -> None:
    """Corrupt -> rebuild -> evaluate -> quality/freshness -> repair tu raw -> compare."""
    settings = load_settings()

    print("[1/5] doc baseline clean data ...", flush=True)
    baseline_df = pd.read_csv(settings.paths.clean_csv)
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    baseline_quality = read_json(settings.paths.quality_dir / "baseline_quality.json")
    baseline_freshness = read_json(settings.paths.freshness_report)
    baseline_probe_path = _probe_path(settings, "baseline")
    baseline_probe = read_json(baseline_probe_path) if baseline_probe_path.exists() else None

    print("[2/5] corrupt clean data ...", flush=True)
    corrupted_df = corrupt_clean_dataframe(baseline_df, settings.paths.corruption_log)
    _write_state_frame(corrupted_df, settings.paths.corrupted_clean_csv, settings.paths.corrupted_clean_json)
    corruption_log = read_json(settings.paths.corruption_log)
    print(f"      {corruption_log['rows_before']} -> {corruption_log['rows_after']} rows, "
          f"{len(corruption_log['entries'])} corruption", flush=True)

    print("[3/5] evaluate corrupted ...", flush=True)
    corrupted = evaluate_state(
        settings,
        corrupted_df,
        "corrupted",
        settings.paths.corrupted_embeddings_json,
        settings.paths.corrupted_metrics,
        settings.paths.corrupted_answers,
    )

    print("[4/5] repair tu raw records va evaluate ...", flush=True)
    raw_records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, now_utc())
    _write_state_frame(repaired_df, settings.paths.repaired_clean_csv, settings.paths.repaired_clean_json)
    # Doc lai tu CSV giong het duong di cua baseline. Neu evaluate thang tren dataframe trong bo nho,
    # `published` con la Timestamp va render thanh "...T00:00:00+00:00" thay vi "... 00:00:00+00:00",
    # lam ground truth loai `date` lech -> token_f1 = 0 vi dinh dang, khong phai vi chat luong data.
    repaired_df = pd.read_csv(settings.paths.repaired_clean_csv)
    repaired = evaluate_state(
        settings,
        repaired_df,
        "repaired",
        settings.paths.repaired_embeddings_json,
        settings.paths.repaired_metrics,
        settings.paths.repaired_answers,
    )

    print("[5/5] comparison report ...", flush=True)
    judge_integrity = {
        state: _judge_integrity(path)
        for state, path in (
            ("baseline", settings.paths.baseline_answers),
            ("corrupted", settings.paths.corrupted_answers),
            ("repaired", settings.paths.repaired_answers),
        )
        if path.exists()
    }
    probe_results = {
        "baseline": baseline_probe,
        "corrupted": corrupted["probe"],
        "repaired": repaired["probe"],
    }
    generate_corruption_report(
        settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted["metrics"],
        repaired_metrics=repaired["metrics"],
        corrupted_quality=corrupted["quality"],
        repaired_quality=repaired["quality"],
        corrupted_freshness=corrupted["freshness"],
        repaired_freshness=repaired["freshness"],
        baseline_quality=baseline_quality,
        baseline_freshness=baseline_freshness,
        corruption_log=corruption_log,
        probe_results={key: value for key, value in probe_results.items() if value},
        judge_integrity=judge_integrity,
    )
    for state, value in judge_integrity.items():
        if value["fallback"]:
            print(f"      CANH BAO: {state} co {value['fallback']}/{value['total']} judge la fallback heuristic", flush=True)
    print("      ->", settings.paths.comparison_report, flush=True)

    for state, payload in (("corrupted", corrupted), ("repaired", repaired)):
        summary = {key: payload["metrics"].get(key) for key in
                   ("retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score")}
        print(f"      {state}: rows={payload['rows']} quality={payload['quality']['passed']}"
              f"/{len(payload['quality']['checks'])} fresh={payload['freshness']['is_fresh']} {summary}", flush=True)


if __name__ == "__main__":
    main()
