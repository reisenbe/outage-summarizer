# Outage Summarizer

A small Python tool that turns raw network outage records (CSV) into plain-English summaries using the Claude API, with a different summary for each audience:

- **customer**: a calm, public status-page summary
- **engineer**: an internal operations briefing, with outages sorted by impact, durations of resolved outages, and patterns such as repeated causes or repeated towns

It's based on real-world work: I built and supported the data pipeline behind a large ISP's public outage board. This project explores how an LLM can turn that same kind of data into readable summaries.

## Example

Input (`sample_outages.csv`):

```
outage_id,town,start_time,end_time,customers_affected,cause,status
1002,Levittown,2026-11-21 07:30,,860,Power failure at hub site,Ongoing
1004,Garden City,2026-11-21 10:15,,2100,Under investigation,Ongoing
...
```

Customer version (excerpt):

> We are currently tracking 8 outages today: 4 are ongoing and 4 have been resolved. About 4,530 customers are affected by the ongoing outages.

Engineer version (excerpt):

> **Power failure at hub site:** 2 ongoing outages (1002 Levittown, 1008 Valley Stream), affecting 2,335 customers combined. Worth checking whether these share a hub or upstream power dependency.

## How to run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install anthropic

export ANTHROPIC_API_KEY="your-key"     # keep this in your shell profile, never in the code

python3 outage_summary.py sample_outages.csv             # customer version (default)
python3 outage_summary.py sample_outages.csv engineer    # engineer version
```

The summary goes to stdout and the token usage to stderr, so you can redirect just the summary:

```bash
python3 outage_summary.py sample_outages.csv > status.txt
```

## Design notes

- **Instructions vs. data.** Each audience's instructions are sent as the system prompt. Only the outage data goes in the user message, which keeps the instructions separate from the content they apply to.
- **Adding an audience** means adding one entry to the `INSTRUCTIONS` dictionary. No other code changes.
- **Accuracy.** The prompts tell the model not to invent details such as restoration times. I checked the output totals and durations against the source data, and the model also flagged an inconsistently capitalized cause value ("Storm Damage") as a possible data-entry issue.
- **Thinking blocks.** The model can return a thinking block before its answer, so the script keeps only the text blocks of the reply.
- **Cost and safety.** It uses Claude Haiku 5.5, the lowest-cost model; one run costs a fraction of a cent. `max_tokens` caps the cost of each call. The API key comes from the environment and is never stored in the repository.

## Possible next steps

- Return structured JSON (using a JSON schema) so the summaries can be loaded into a database or dashboard
- Run it on a schedule (cron or Airflow) against live data
- Add an executive-summary audience
