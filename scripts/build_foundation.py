#!/usr/bin/env python3
"""
Translation Pipeline — Foundation Builder

Запускает MiniMax-проход для извлечения терминов, сущностей,
и анализа стиля исходного документа.

Usage:
    python build_foundation.py <project-dir>
"""

import sys
import json
import os
import re
import requests


def load_file(path):
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def call_minimax(prompt):
    """Call MiniMax API."""
    # Same as in translate_fallback.py
    api_key = os.environ.get('MINIMAX_API_KEY', '')
    if not api_key:
        config_path = os.path.expanduser('~/.hermes/config.yaml')
        if os.path.exists(config_path):
            with open(config_path) as f:
                for line in f:
                    if 'api_key' in line and 'minimax' in line.lower():
                        api_key = line.split(':')[1].strip().strip("'\"")
                        break
    
    if not api_key:
        print("ERROR: MINIMAX_API_KEY not found")
        sys.exit(1)
    
    response = requests.post(
        "https://api.minimax.io/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": "minimax-4o-flash",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 4096
        },
        timeout=120
    )
    
    if response.status_code != 200:
        print(f"ERROR: MiniMax API returned {response.status_code}")
        return None
    
    result = response.json()
    content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
    
    # Clean 幼儿园 blocks
    content = re.sub(r'<(sup|sub|u|del|span)[^>]*>[^<]*</\1>', '', content)
    
    return content.strip()


def extract_terms(text, lang):
    """Extract key terms using MiniMax."""
    prompt = f"""Проанализируй следующий текст на {"русском" if lang == "ru" else "иностранном"} языке и извлеки ключевые термины и понятия, которые требуют внимательного перевода на русский.

Для каждого термина укажи:
1. Исходный термин (как в тексте)
2. Предполагаемый перевод на русский
3. Домен/область
4. Примечание (контекст использования)

Формат: каждая строка через | разделитель
Значение 1 | Значение 2 | Значение 3 | Значение 4

Только таблица, без пояснений.

Текст:
{text[:6000]}
"""
    return call_minimax(prompt)


def extract_entities(text, lang):
    """Extract named entities using MiniMax."""
    prompt = f"""Извлеки из текста имена собственные (люди, места, организации, события, даты) на {"русском" if lang == "ru" else "иностранном"} языке.

Для каждой сущности укажи:
1. Оригинальное написание
2. Предполагаемый перевод на русский
3. Тип (person, location, organization, event, date, other)
4. Примечание

Формат: каждая строка через | разделитель
Значение 1 | Значение 2 | Значение 3 | Значение 4

Только таблица, без пояснений.

Текст:
{text[:6000]}
"""
    return call_minimax(prompt)


def build_foundation(project_dir):
    """Build or enhance foundation files."""
    source_path = os.path.join(project_dir, 'source', 'source.md')
    foundation_dir = os.path.join(project_dir, 'foundation')
    
    if not os.path.exists(source_path):
        print("ERROR: source/source.md not found")
        sys.exit(1)
    
    text = load_file(source_path)
    if not text:
        print("ERROR: Empty source")
        sys.exit(1)
    
    # Get language from intake
    lang = 'en'
    intake_path = os.path.join(project_dir, 'intake.json')
    if os.path.exists(intake_path):
        with open(intake_path) as f:
            intake = json.load(f)
        lang = intake.get('source_language', 'en')
    
    # Extract terms
    print("Extracting terms...")
    terms_result = extract_terms(text[:10000], lang)
    if terms_result:
        terms_path = os.path.join(foundation_dir, 'glossary_raw.md')
        with open(terms_path, 'w', encoding='utf-8') as f:
            f.write("# Raw Glossary (Auto-Extracted)\n\n")
            f.write("| source | target | domain | notes |\n")
            f.write("|--------|--------|--------|-------|\n")
            f.write(terms_result)
        print(f"  Terms saved: {terms_path}")
    else:
        print("  ⚠️ Term extraction failed")
    
    # Extract entities
    print("Extracting named entities...")
    entities_result = extract_entities(text[:10000], lang)
    if entities_result:
        entities_path = os.path.join(foundation_dir, 'entities_raw.md')
        with open(entities_path, 'w', encoding='utf-8') as f:
            f.write("# Raw Entities (Auto-Extracted)\n\n")
            f.write("| original | target | type | notes |\n")
            f.write("|----------|--------|------|-------|\n")
            f.write(entities_result)
        print(f"  Entities saved: {entities_path}")
    else:
        print("  ⚠️ Entity extraction failed")
    
    print("\nFoundation enhancement complete!")
    print("Review and refine the auto-extracted files before translation.")
    print(f"  Edit: {foundation_dir}/glossary.md")
    print(f"  Edit: {foundation_dir}/style.md")
    print(f"  Edit: {foundation_dir}/entities.md")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python build_foundation.py <project-dir>")
        sys.exit(1)
    build_foundation(sys.argv[1])
