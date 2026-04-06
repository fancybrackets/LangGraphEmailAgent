#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import os
import statistics
import subprocess
import time
from pathlib import Path
from typing import Any

import requests
from requests.exceptions import RequestException


EXCLUDED_MODELS = {"qwen2.5:7b"}
FALLBACK_MODELS = [
    "llama3.2:1b",
    "llama3.2:3b",
    "qwen2.5:0.5b",
    "qwen2.5:1.5b",
    "qwen2.5:3b",
    "qwen2.5-coder:0.5b",
    "qwen2.5-coder:1.5b",
    "gemma3:4b-it-qat",
    "gemma3:4b",
]


def parse_args() -> argparse.Namespace:
    base_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Benchmark local chat models via FastAPI /chat")
    parser.add_argument("--api-base", default=os.getenv("BENCH_API_BASE", "http://127.0.0.1:8013"))
    parser.add_argument("--prompts", default=str(base_dir / "prompts.json"))
    parser.add_argument("--results", default=str(base_dir / "results.csv"))
    parser.add_argument("--summary", default=str(base_dir / "summary.csv"))
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument(
        "--models",
        default="",
        help="Comma-separated model names. If empty, use /models/catalog (excluding qwen2.5:7b).",
    )
    return parser.parse_args()


def load_prompts(path: str) -> list[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in prompts file: {path} "
            f"(line {exc.lineno}, column {exc.colno}). "
            "Check trailing commas or missing quotes."
        ) from exc
    if isinstance(data, list):
        prompts = data
    else:
        prompts = data.get("prompts", [])
    prompts = [str(p).strip() for p in prompts if str(p).strip()]
    if not prompts:
        raise ValueError(f"No prompts found in {path}")
    return prompts


def fetch_catalog_models(api_base: str, timeout: int) -> list[str]:
    url = f"{api_base.rstrip('/')}/models/catalog"
    res = requests.get(url, timeout=timeout)
    res.raise_for_status()
    payload = res.json()
    catalog = payload.get("catalog", [])
    return [item["name"] for item in catalog if isinstance(item, dict) and item.get("name")]


def fetch_installed_models(api_base: str, timeout: int) -> set[str]:
    url = f"{api_base.rstrip('/')}/models"
    res = requests.get(url, timeout=timeout)
    res.raise_for_status()
    payload = res.json()
    rows = payload.get("models", [])
    return {item["name"] for item in rows if isinstance(item, dict) and item.get("name")}


def resolve_models(api_base: str, timeout: int, models_arg: str) -> list[str]:
    if models_arg.strip():
        models = [m.strip() for m in models_arg.split(",") if m.strip()]
    else:
        try:
            models = fetch_catalog_models(api_base, timeout)
        except Exception:
            models = FALLBACK_MODELS

    filtered = [m for m in models if m not in EXCLUDED_MODELS]
    if not filtered:
        raise ValueError("Model list is empty after filtering.")
    return filtered


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    sorted_values = sorted(values)
    rank = (len(sorted_values) - 1) * p
    lo = math.floor(rank)
    hi = math.ceil(rank)
    if lo == hi:
        return sorted_values[lo]
    return sorted_values[lo] * (hi - rank) + sorted_values[hi] * (rank - lo)


def sample_ollama_usage() -> tuple[float | None, float | None]:
    try:
        proc = subprocess.run(
            ["ps", "-axo", "pid,rss,%cpu,command"],
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        return (None, None)

    if proc.returncode != 0:
        return (None, None)

    total_rss_kb = 0.0
    total_cpu_pct = 0.0
    lines = proc.stdout.splitlines()[1:]
    for line in lines:
        raw = line.strip()
        if not raw:
            continue
        parts = raw.split(None, 3)
        if len(parts) < 4:
            continue
        _, rss_kb, cpu_pct, command = parts
        cmd = command.lower()
        if "ollama" not in cmd:
            continue
        if "run_benchmark.py" in cmd:
            continue
        try:
            total_rss_kb += float(rss_kb)
            total_cpu_pct += float(cpu_pct)
        except ValueError:
            continue

    if total_rss_kb <= 0 and total_cpu_pct <= 0:
        return (None, None)

    return (total_cpu_pct, total_rss_kb / 1024.0)


def run_single_chat(
    api_base: str,
    model: str,
    thread_id: str,
    prompt: str,
    timeout: int,
) -> dict[str, Any]:
    url = f"{api_base.rstrip('/')}/chat"
    payload = {"thread_id": thread_id, "message": prompt, "model": model}

    cpu_before, ram_before = sample_ollama_usage()
    start = time.perf_counter()
    status_code = 0
    reply = ""
    error_message = ""

    try:
        response = requests.post(url, json=payload, timeout=timeout)
        status_code = response.status_code
        data = response.json() if response.content else {}
        if isinstance(data, dict):
            reply = str(data.get("reply", "")).strip()
            if status_code >= 400 and not reply:
                error_message = str(data.get("detail", "")).strip()
    except Exception as exc:  # noqa: BLE001
        error_message = str(exc)

    latency_ms = (time.perf_counter() - start) * 1000.0
    cpu_after, ram_after = sample_ollama_usage()

    cpu_vals = [v for v in [cpu_before, cpu_after] if v is not None]
    ram_vals = [v for v in [ram_before, ram_after] if v is not None]
    cpu_avg = statistics.fmean(cpu_vals) if cpu_vals else None
    ram_avg = statistics.fmean(ram_vals) if ram_vals else None

    success = status_code == 200 and bool(reply)
    error = (400 <= status_code < 600) or status_code == 0

    return {
        "timestamp": dt.datetime.now().isoformat(timespec="seconds"),
        "model": model,
        "thread_id": thread_id,
        "latency_ms": round(latency_ms, 2),
        "status_code": status_code,
        "success": int(success),
        "error": int(error),
        "reply_chars": len(reply),
        "cpu_pct_avg": round(cpu_avg, 2) if cpu_avg is not None else "",
        "ram_mb_avg": round(ram_avg, 2) if ram_avg is not None else "",
        "error_message": error_message,
    }


def write_csv(path: str, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_model: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_model.setdefault(str(row["model"]), []).append(row)

    summary_rows: list[dict[str, Any]] = []
    for model, group in by_model.items():
        total = len(group)
        success_count = sum(int(r["success"]) for r in group)
        error_count = sum(int(r["error"]) for r in group)
        success_latencies = [float(r["latency_ms"]) for r in group if int(r["success"]) == 1]
        ram_vals = [float(r["ram_mb_avg"]) for r in group if str(r["ram_mb_avg"]) != ""]

        avg_latency = statistics.fmean(success_latencies) if success_latencies else None
        p95_latency = percentile(success_latencies, 0.95) if success_latencies else None
        success_rate = (success_count / total * 100.0) if total else 0.0
        error_rate = (error_count / total * 100.0) if total else 0.0
        avg_ram = statistics.fmean(ram_vals) if ram_vals else None

        summary_rows.append(
            {
                "model": model,
                "total_requests": total,
                "avg_latency_ms": round(avg_latency, 2) if avg_latency is not None else "",
                "p95_latency_ms": round(p95_latency, 2) if p95_latency is not None else "",
                "success_rate_pct": round(success_rate, 2),
                "error_rate_pct": round(error_rate, 2),
                "avg_ram_mb": round(avg_ram, 2) if avg_ram is not None else "",
            }
        )
    return sorted(summary_rows, key=lambda x: str(x["model"]))


def main() -> None:
    args = parse_args()
    prompts = load_prompts(args.prompts)
    try:
        models = resolve_models(args.api_base, args.timeout, args.models)
        installed = fetch_installed_models(args.api_base, args.timeout)
    except RequestException as exc:
        raise RuntimeError(
            f"API ulasilamiyor: {args.api_base}. "
            "Once backend'i calistir: "
            "`python -m uvicorn app.main:app --host 127.0.0.1 --port 8013 --env-file .env`"
        ) from exc

    benchmark_models = [m for m in models if m in installed]
    missing_models = [m for m in models if m not in installed]
    if not benchmark_models:
        raise RuntimeError(
            "No installed models found for benchmark. Please download models in /settings first."
        )

    print("Benchmark models:", ", ".join(benchmark_models))
    if missing_models:
        print("Skipped (not installed):", ", ".join(missing_models))
    print(f"Prompt count: {len(prompts)} | Rounds: {args.rounds}")

    rows: list[dict[str, Any]] = []
    total_runs = len(benchmark_models) * len(prompts) * args.rounds
    done = 0

    for model in benchmark_models:
        for round_idx in range(1, args.rounds + 1):
            thread_id = f"bench-{model.replace(':', '_')}-r{round_idx}"
            for prompt_idx, prompt in enumerate(prompts, start=1):
                result = run_single_chat(
                    api_base=args.api_base,
                    model=model,
                    thread_id=thread_id,
                    prompt=prompt,
                    timeout=args.timeout,
                )
                result["round"] = round_idx
                result["prompt_index"] = prompt_idx
                result["prompt"] = prompt
                rows.append(result)

                done += 1
                print(
                    f"[{done}/{total_runs}] model={model} round={round_idx} "
                    f"prompt={prompt_idx} status={result['status_code']} "
                    f"latency_ms={result['latency_ms']}"
                )

    result_fields = [
        "timestamp",
        "model",
        "round",
        "thread_id",
        "prompt_index",
        "prompt",
        "status_code",
        "success",
        "error",
        "latency_ms",
        "reply_chars",
        "cpu_pct_avg",
        "ram_mb_avg",
        "error_message",
    ]
    write_csv(args.results, rows, result_fields)

    summary_rows = summarize(rows)
    summary_fields = [
        "model",
        "total_requests",
        "avg_latency_ms",
        "p95_latency_ms",
        "success_rate_pct",
        "error_rate_pct",
        "avg_ram_mb",
    ]
    write_csv(args.summary, summary_rows, summary_fields)

    print("")
    print(f"Detailed results: {args.results}")
    print(f"Summary: {args.summary}")
    print("")
    print("Thesis table preview:")
    for row in summary_rows:
        print(
            f"- {row['model']}: avg={row['avg_latency_ms']} ms, "
            f"p95={row['p95_latency_ms']} ms, "
            f"success={row['success_rate_pct']}%, "
            f"avg_ram={row['avg_ram_mb']} MB"
        )


if __name__ == "__main__":
    main()
