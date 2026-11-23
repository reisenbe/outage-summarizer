#!/usr/bin/env python3
"""
outage_summary.py - Turn raw outage records into a plain-English status summary
using an LLM (Claude).

Usage:
    python3 outage_summary.py sample_outages.csv            (customer version)
    python3 outage_summary.py sample_outages.csv engineer   (internal version)

Requires:
    pip install anthropic
    export ANTHROPIC_API_KEY="your-key"   (set in your shell, never in this file)
"""

import csv
import os
import sys

import anthropic
from datetime import datetime

# Cheapest current Claude model -- plenty for summarizing a small table.
MODEL = "claude-haiku-5-5"
MAX_OUTPUT_TOKENS = 2000  # room for the model's thinking plus the summary


def read_outages(path):
    """Read the CSV into a list of dicts, one per row (like a Perl hash per line)."""
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


# One set of instructions per audience. To add a new version, add a new entry.
INSTRUCTIONS = {
    "customer": """You are writing the public outage status page for an internet provider.
Write a short, calm, customer-facing summary:
1. One opening sentence with the overall picture (how many outages are ongoing vs. resolved, total customers currently affected).
2. A bulleted list of ONGOING outages by town, with customers affected and cause.
3. One sentence noting resolved outages.
Use plain language. Do not invent restoration times or details that are not in the data.""",

    "engineer": """You are writing an internal outage briefing for the network operations team.
Write a concise technical summary:
1. Totals: ongoing vs. resolved outages, customers currently affected.
2. Ongoing outages ordered by customers affected (largest first), with outage_id, town, start time, and cause.
3. Patterns worth attention: repeated causes or repeated towns.
4. For resolved outages, the duration from the duration_minutes column, shown as hours and minutes. Do not calculate durations yourself.""",
}


def build_prompt(rows, audience):
    """Turn the rows back into plain text and wrap them in instructions."""
    header = ",".join(rows[0].keys())
    lines = [",".join(row.values()) for row in rows]
    data = "\n".join([header] + lines)

    return f"""Here are today's outage records in CSV format. A blank end_time means the outage is still ongoing.

<outages>
{data}
</outages>"""

def add_durations(rows):
    for row in rows:
        if row["end_time"]:  # resolved: has an end time
            start = datetime.strptime(row["start_time"], "%Y-%m-%d %H:%M")
            end = datetime.strptime(row["end_time"], "%Y-%m-%d %H:%M")
            row["duration_minutes"] = str(int((end - start).total_seconds() / 60))
        else:  # ongoing: blank end time
            row["duration_minutes"] = ""
def main():
    if len(sys.argv) not in (2, 3):
        sys.exit(f"Usage: {sys.argv[0]} <outages.csv> [{'|'.join(INSTRUCTIONS)}]")

    # Optional second argument picks the audience; default is customer.
    audience = sys.argv[2] if len(sys.argv) == 3 else "customer"
    if audience not in INSTRUCTIONS:
        sys.exit(f"Unknown audience '{audience}'. Choose one of: {', '.join(INSTRUCTIONS)}")

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set. Add it to your shell profile and open a new terminal.")

    rows = read_outages(sys.argv[1])
    add_durations(rows)
    if not rows:
        sys.exit("No outage records found in the file.")

    client = anthropic.Anthropic()  # picks up ANTHROPIC_API_KEY automatically

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_OUTPUT_TOKENS,
            system=INSTRUCTIONS[audience],
            messages=[{"role": "user", "content": build_prompt(rows, audience)}],
        )
    except anthropic.APIError as e:
        sys.exit(f"API call failed: {e}")

    # The reply is a list of "content blocks". The model may include a
    # "thinking" block (its private reasoning) before the actual answer,
    # so keep only the text blocks.
    summary = "".join(b.text for b in response.content if b.type == "text")
    if not summary:
        sys.exit(f"No text in the reply (stop_reason: {response.stop_reason}). "
                 f"Try raising MAX_OUTPUT_TOKENS.")

    # The summary goes to stdout, so you can redirect it: ... > status.txt
    print(summary)

    # Token usage goes to stderr, so it doesn't end up in the summary file.
    u = response.usage
    print(f"\n[tokens used: {u.input_tokens} in, {u.output_tokens} out]", file=sys.stderr)


if __name__ == "__main__":
    main()
