# JobRadar

**A private, local-first job-search assistant: it scans public job boards on demand, filters senior roles by region and relevance, and scores each posting against your own profile with a local LLM — no cloud API, no automatic applications.**

## What it does

- **On-demand scanning** of freehire, Himalayas, Jobicy and enabled official ATS boards (`./jr run`). No background service.
- **Two-stage filtering** by title keywords, excluded roles and location (countries, cities, remote eligibility).
- **Offline HTML dashboard** with per-column sorting, Excel-style multi-value filters, city / country split, posting age, "newly discovered" toggle and CSV export.
- **LLM fit evaluation via local [Ollama](https://ollama.com)** (default `qwen3:8b`), driven by a versioned Markdown prompt; drafts an application package only when the verdict is *APPLY*.
- **Application tracking** in SQLite: exact statuses, notes, history import and export.
- **Watch-list** of title phrases (`watch-add`, `watch-list`, `watch-remove`).

## Quick start (macOS)

```bash
./installer.sh                        # creates .venv and installs requirements
cp profile.example.json profile.json  # fill in your own profile
cp config.example.json config.json    # set regions, keywords, sources
ollama pull qwen3:8b && ./jr doctor   # check the local model and RAM
./jr run                              # scan, build and open the dashboard
./jr evaluate '<source>:<job-id>'     # LLM fit evaluation for one posting
```

Your personal files (`profile.json`, `config.json`, the active prompt, `data/` and `output/`) are excluded from the repository by `.gitignore`. Put your own evaluation prompt in `prompts/ACTIVE.md` or load one with `./jr prompt-set <file.md>`.

## Tech stack

Python (standard library CLI) · SQLite · Ollama (local LLM) · python-docx · ReportLab · pypdf

Further documentation in Turkish: [README_TR.md](README_TR.md), [ARCHITECTURE_TR.md](ARCHITECTURE_TR.md), [SOURCES_RESEARCH_TR.md](SOURCES_RESEARCH_TR.md).
