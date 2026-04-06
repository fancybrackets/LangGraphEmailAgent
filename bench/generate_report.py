#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import datetime as dt
import html
from pathlib import Path


def parse_args() -> argparse.Namespace:
    base_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Generate benchmark table/chart reports from CSV.")
    parser.add_argument("--summary", default=str(base_dir / "summary.csv"))
    parser.add_argument("--results", default=str(base_dir / "results.csv"))
    parser.add_argument("--out-md", default=str(base_dir / "report.md"))
    parser.add_argument("--out-html", default=str(base_dir / "report.html"))
    return parser.parse_args()


def to_float(value: str) -> float | None:
    raw = str(value).strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def read_csv(path: str) -> list[dict[str, str]]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def fmt_num(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "-"
    return f"{value:.{digits}f}"


def build_markdown(summary_rows: list[dict[str, str]], results_path: str, summary_path: str) -> str:
    lines: list[str] = []
    lines.append("# Benchmark Report")
    lines.append("")
    lines.append(f"- Generated: {dt.datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"- Summary CSV: `{summary_path}`")
    lines.append(f"- Results CSV: `{results_path}`")
    lines.append("")
    lines.append("## Thesis Table")
    lines.append("")
    lines.append("| model | avg latency (ms) | p95 latency (ms) | success rate (%) | avg RAM (MB) |")
    lines.append("|---|---:|---:|---:|---:|")

    for row in summary_rows:
        model = row.get("model", "-")
        avg_latency = fmt_num(to_float(row.get("avg_latency_ms", "")))
        p95_latency = fmt_num(to_float(row.get("p95_latency_ms", "")))
        success_rate = fmt_num(to_float(row.get("success_rate_pct", "")))
        avg_ram = fmt_num(to_float(row.get("avg_ram_mb", "")))
        lines.append(f"| {model} | {avg_latency} | {p95_latency} | {success_rate} | {avg_ram} |")

    lines.append("")
    lines.append("## Extended Table")
    lines.append("")
    lines.append("| model | requests | error rate (%) |")
    lines.append("|---|---:|---:|")
    for row in summary_rows:
        model = row.get("model", "-")
        requests = row.get("total_requests", "-")
        error_rate = fmt_num(to_float(row.get("error_rate_pct", "")))
        lines.append(f"| {model} | {requests} | {error_rate} |")

    lines.append("")
    return "\n".join(lines)


def render_metric_block(
    summary_rows: list[dict[str, str]],
    key: str,
    title: str,
    unit: str,
    scale_max: float | None = None,
) -> str:
    parsed: list[tuple[str, float]] = []
    for row in summary_rows:
        val = to_float(row.get(key, ""))
        if val is not None:
            parsed.append((row.get("model", "-"), val))

    if not parsed:
        return (
            f"<section><h3>{html.escape(title)}</h3>"
            "<p class='empty'>No data available.</p></section>"
        )

    max_value = scale_max if scale_max is not None else max(v for _, v in parsed)
    if max_value <= 0:
        max_value = 1.0

    rows_html: list[str] = []
    for model, value in parsed:
        width = (value / max_value) * 100.0
        rows_html.append(
            "<div class='bar-row'>"
            f"<div class='label'>{html.escape(model)}</div>"
            "<div class='track'>"
            f"<div class='fill' style='width:{width:.2f}%'></div>"
            "</div>"
            f"<div class='value'>{value:.2f} {html.escape(unit)}</div>"
            "</div>"
        )

    return (
        "<section class='metric-card'>"
        f"<h3>{html.escape(title)}</h3>"
        + "".join(rows_html)
        + "</section>"
    )


def build_html(summary_rows: list[dict[str, str]], results_path: str, summary_path: str) -> str:
    table_rows: list[str] = []
    for row in summary_rows:
        model = html.escape(row.get("model", "-"))
        total = html.escape(row.get("total_requests", "-"))
        avg_latency = fmt_num(to_float(row.get("avg_latency_ms", "")))
        p95_latency = fmt_num(to_float(row.get("p95_latency_ms", "")))
        success_rate = fmt_num(to_float(row.get("success_rate_pct", "")))
        error_rate = fmt_num(to_float(row.get("error_rate_pct", "")))
        avg_ram = fmt_num(to_float(row.get("avg_ram_mb", "")))
        table_rows.append(
            "<tr>"
            f"<td>{model}</td>"
            f"<td>{total}</td>"
            f"<td>{avg_latency}</td>"
            f"<td>{p95_latency}</td>"
            f"<td>{success_rate}</td>"
            f"<td>{error_rate}</td>"
            f"<td>{avg_ram}</td>"
            "</tr>"
        )

    metric_avg = render_metric_block(
        summary_rows, key="avg_latency_ms", title="Average Latency", unit="ms"
    )
    metric_p95 = render_metric_block(
        summary_rows, key="p95_latency_ms", title="P95 Latency", unit="ms"
    )
    metric_success = render_metric_block(
        summary_rows, key="success_rate_pct", title="Success Rate", unit="%", scale_max=100.0
    )
    metric_ram = render_metric_block(
        summary_rows, key="avg_ram_mb", title="Average RAM Usage", unit="MB"
    )

    generated = dt.datetime.now().isoformat(timespec="seconds")

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Benchmark Report</title>
  <style>
    :root {{
      --bg: #f5f7fb;
      --card: #ffffff;
      --text: #17223b;
      --muted: #52657a;
      --bar: #2b6cb0;
      --bar-soft: #d9e7f7;
      --border: #dde5ef;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      line-height: 1.5;
    }}
    .wrap {{
      max-width: 1100px;
      margin: 24px auto;
      padding: 0 16px 40px;
    }}
    h1, h2, h3 {{ margin: 0 0 12px; }}
    .meta {{
      color: var(--muted);
      font-size: 14px;
      margin-bottom: 20px;
    }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 12px;
      margin-bottom: 20px;
    }}
    .metric-card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 14px;
    }}
    .bar-row {{
      display: grid;
      grid-template-columns: 170px 1fr 90px;
      gap: 10px;
      align-items: center;
      margin-bottom: 8px;
      font-size: 13px;
    }}
    .track {{
      height: 10px;
      border-radius: 999px;
      background: var(--bar-soft);
      overflow: hidden;
    }}
    .fill {{
      height: 100%;
      background: var(--bar);
    }}
    .value {{
      text-align: right;
      color: var(--muted);
      font-variant-numeric: tabular-nums;
    }}
    .empty {{
      color: var(--muted);
      font-size: 13px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 12px;
      overflow: hidden;
    }}
    th, td {{
      padding: 10px 12px;
      border-bottom: 1px solid var(--border);
      text-align: left;
      font-size: 14px;
      font-variant-numeric: tabular-nums;
    }}
    th {{
      background: #f2f6fc;
      font-weight: 600;
    }}
    tr:last-child td {{
      border-bottom: none;
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Benchmark Report</h1>
    <div class="meta">
      <div>Generated: {html.escape(generated)}</div>
      <div>Summary CSV: {html.escape(summary_path)}</div>
      <div>Results CSV: {html.escape(results_path)}</div>
    </div>

    <div class="metrics">
      {metric_avg}
      {metric_p95}
      {metric_success}
      {metric_ram}
    </div>

    <h2>Summary Table</h2>
    <table>
      <thead>
        <tr>
          <th>Model</th>
          <th>Total Requests</th>
          <th>Avg Latency (ms)</th>
          <th>P95 Latency (ms)</th>
          <th>Success Rate (%)</th>
          <th>Error Rate (%)</th>
          <th>Avg RAM (MB)</th>
        </tr>
      </thead>
      <tbody>
        {''.join(table_rows)}
      </tbody>
    </table>
  </div>
</body>
</html>
"""


def write_text(path: str, content: str) -> None:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")


def main() -> None:
    args = parse_args()
    summary_rows = read_csv(args.summary)
    if not summary_rows:
        raise RuntimeError(
            f"No rows found in summary file: {args.summary}. Run benchmark first."
        )

    md_content = build_markdown(summary_rows, args.results, args.summary)
    html_content = build_html(summary_rows, args.results, args.summary)
    write_text(args.out_md, md_content)
    write_text(args.out_html, html_content)

    print(f"Markdown report: {args.out_md}")
    print(f"HTML report: {args.out_html}")


if __name__ == "__main__":
    main()
