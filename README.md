# Hermes Translation Pipeline — Archived

**Status:** This repository is a historical reference. Active development moved to [hermes-ru-document-translator](https://github.com/perejaslav/hermes-ru-document-translator).

## Migration

The unified pipeline (v0.2+) combines this repository's methodology with the production infrastructure of hermes-ru-document-translator:

- Foundation stage
- 2-wave translation
- 5 QA gates
- repair/remediation
- backend abstraction layer

**Canonical repo:** https://github.com/perejaslav/hermes-ru-document-translator

---

## What was here (archived reference)

### Architecture

```
Ingestion → Foundation → Chunking → Parallel Translation (2 waves) → Quality Gates → Assembly
```

### Features preserved in canonical repo

- **Foundation** — glossary, style guide, entity register
- **2-wave translation** — draft → refinement
- **5 QA gates** — terminology, integrity, style, fluency, formatting
- **repair/remediation** — chunk-level re-translation

### Project structure (historical)

```
projects/<slug>/
├── source/source.md
├── foundation/{glossary,style,entities}.md
├── chunks/
├── translations/{draft,final}/
├── quality/report.md
└── manuscript.md
```

### Dependencies (historical)

- Hermes Agent with subagent support
- Python 3.10+
- Pandoc
- MiniMax API access

---

## Archived installation instructions

```bash
git clone https://github.com/perejaslav/hermes-translation-pipeline.git
cd hermes-translation-pipeline
cp -r skills/translation-pipeline ~/.hermes/skills/software-development/
cp -r skills/translation-worker ~/.hermes/skills/software-development/
mkdir -p ~/.hermes/scripts/translation-pipeline
cp scripts/*.py ~/.hermes/scripts/translation-pipeline/
```

---

## Archived CLI scripts (fallback mode)

- `translate_fallback.py` — direct MiniMax API translation
- `project_init.py` — project initialization
- `chunk.py` — text segmentation
- `build_foundation.py` — glossary/style/entities
- `quality_gates.py` — quality checks
- `assembly.py` — merge and export

These scripts are not maintained for the unified pipeline scope.

---

**License:** MIT