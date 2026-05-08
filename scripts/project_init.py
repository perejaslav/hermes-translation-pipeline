#!/usr/bin/env python3
"""
Translation Pipeline — Project Init

Создаёт новый проект перевода: структуру директорий, intake.json,
копирует исходный файл, извлекает текст через pandoc.

Usage:
    python project_init.py <project-slug> <source-file> [source-language]
"""

import sys
import json
import os
import re
import shutil
import subprocess
from datetime import datetime


def ensure_dir(d):
    os.makedirs(d, exist_ok=True)


def detect_language(text_path):
    """Определяет язык исходного текста через MiniMax."""
    with open(text_path, 'r', encoding='utf-8') as f:
        text = f.read(2000)
    
    if not text.strip():
        return "unknown"
    
    # Simple char-based detection
    import collections
    chars = text[:500]
    latin = sum(1 for c in chars if 'a' <= c.lower() <= 'z')
    cyrillic = sum(1 for c in chars if 'а' <= c.lower() <= 'я' or c.lower() == 'ё')
    cjk = sum(1 for c in chars if '\u4e00' <= c <= '\u9fff')
    arabic = sum(1 for c in chars if '\u0600' <= c <= '\u06ff')
    total = latin + cyrillic + cjk + arabic
    
    if total == 0:
        return "unknown"
    
    ratios = {
        'en': latin / total,
        'ru': cyrillic / total,
        'zh': cjk / total,
        'ar': arabic / total,
    }
    
    dominant = max(ratios, key=ratios.get)
    if ratios[dominant] > 0.5:
        lang_map = {'en': 'en', 'ru': 'ru', 'zh': 'zh', 'ar': 'ar'}
        return lang_map.get(dominant, 'en')
    
    return 'en'  # default


def extract_text(source_path, output_path):
    """Извлекает текст через pandoc."""
    ext = os.path.splitext(source_path)[1].lower()
    
    if ext in ['.md', '.txt']:
        shutil.copy2(source_path, output_path)
        print(f"  Copied as-is: {ext}")
        return True
    
    # Try pandoc
    try:
        result = subprocess.run(
            ['pandoc', source_path, '-t', 'markdown', '-o', output_path, '--wrap=preserve'],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            print(f"  Extracted via pandoc: {ext}")
            return True
        else:
            print(f"  pandoc error: {result.stderr[:200]}")
            return False
    except FileNotFoundError:
        print("  pandoc not found, trying raw copy")
        try:
            shutil.copy2(source_path, output_path)
            return True
        except:
            return False
    except Exception as e:
        print(f"  Extraction failed: {e}")
        return False


def init_project(slug, source_path, source_language=None):
    """Initialize a new translation project."""
    base_dir = f'/root/apps/translation-pipeline/projects/{slug}'
    
    if os.path.exists(base_dir):
        print(f"ERROR: Project '{slug}' already exists at {base_dir}")
        sys.exit(1)
    
    # Create structure
    dirs = [
        base_dir,
        os.path.join(base_dir, 'source'),
        os.path.join(base_dir, 'foundation'),
        os.path.join(base_dir, 'chunks'),
        os.path.join(base_dir, 'translations', 'draft'),
        os.path.join(base_dir, 'translations', 'final'),
        os.path.join(base_dir, 'quality'),
        os.path.join(base_dir, 'output'),
    ]
    for d in dirs:
        ensure_dir(d)
    
    # Copy source
    src_ext = os.path.splitext(source_path)[1]
    source_copy = os.path.join(base_dir, 'source', f'original{src_ext}')
    shutil.copy2(source_path, source_copy)
    print(f"Source copied: {source_copy}")
    
    # Extract text
    source_md = os.path.join(base_dir, 'source', 'source.md')
    if not extract_text(source_copy, source_md):
        print("WARNING: Text extraction failed, will use original")
        shutil.copy2(source_copy, source_md)
    
    # Detect language
    if not source_language:
        source_language = detect_language(source_md)
        lang_names = {'en': 'en', 'ru': 'ru', 'zh': 'zh', 'ar': 'ar', 'unknown': 'unknown'}
        source_language = lang_names.get(source_language, source_language)
    
    # Count words
    with open(source_md, 'r', encoding='utf-8') as f:
        text = f.read()
    word_count = len(text.split())
    
    # Write intake.json
    intake = {
        "project_name": slug.replace('-', ' ').title(),
        "slug": slug,
        "source_language": source_language,
        "target_language": "ru",
        "source_format": src_ext,
        "source_path": source_copy,
        "word_count_source": word_count,
        "estimated_chunks": max(1, word_count // 800),
        "document_type": "",
        "domain": "",
        "notes": "",
        "created_at": datetime.now().isoformat(),
        "status": "intake"
    }
    
    intake_path = os.path.join(base_dir, 'intake.json')
    with open(intake_path, 'w', encoding='utf-8') as f:
        json.dump(intake, f, ensure_ascii=False, indent=2)
    print(f"Intake: {intake_path}")
    
    # Copy foundation templates
    skill_dir = os.path.expanduser('~/.hermes/skills/software-development/translation-pipeline')
    templates_dir = os.path.join(skill_dir, 'templates')
    foundation_dir = os.path.join(base_dir, 'foundation')
    
    for tmpl in ['glossary.md', 'style.md', 'entities.md']:
        tmpl_path = os.path.join(templates_dir, tmpl)
        if os.path.exists(tmpl_path):
            shutil.copy2(tmpl_path, os.path.join(foundation_dir, tmpl))
    
    print(f"\nProject '{slug}' initialized!")
    print(f"  Path: {base_dir}")
    print(f"  Source language: {source_language}")
    print(f"  Words: {word_count}")
    print(f"  Est. chunks: {intake['estimated_chunks']}")
    print(f"\nNext steps:")
    print(f"  1. Fill foundation/glossary.md")
    print(f"  2. Fill foundation/style.md")
    print(f"  3. Fill foundation/entities.md")
    print(f"  4. Run chunk.py {base_dir}")
    print(f"  5. Run translation")
    print(f"  6. Run quality_gates.py {base_dir}")
    print(f"  7. Run assembly.py {base_dir}")
    
    return base_dir


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python project_init.py <project-slug> <source-file> [source-language]")
        print("  source-language: en, de, fr, es, zh, ja, ko, ar (default: auto-detect)")
        sys.exit(1)
    
    slug = sys.argv[1]
    source = sys.argv[2]
    lang = sys.argv[3] if len(sys.argv) >= 3 else None
    
    if not os.path.exists(source):
        print(f"ERROR: Source file not found: {source}")
        sys.exit(1)
    
    init_project(slug, source, lang)
