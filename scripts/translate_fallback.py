#!/usr/bin/env python3
"""
Translation Pipeline — Fallback Translator

Прямой последовательный перевод сегментов через MiniMax API.
Используется когда subagents (opencode-go) недоступны.

Usage:
    python translate_fallback.py <project-dir>
"""

import sys
import json
import os
import re
import requests
import time


def load_file(path):
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def call_minimax(prompt, system_prompt=None):
    """Call MiniMax API for translation."""
    api_key = os.environ.get('MINIMAX_API_KEY', '')
    if not api_key:
        # Try to get from hermes config
        try:
            config_path = os.path.expanduser('~/.hermes/config.yaml')
            with open(config_path) as f:
                for line in f:
                    if 'api_key' in line and 'minimax' in line.lower():
                        api_key = line.split(':')[1].strip().strip("'\"")
                        break
        except:
            pass
    
    if not api_key:
        print("ERROR: MINIMAX_API_KEY not found")
        sys.exit(1)
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    response = requests.post(
        "https://api.minimax.io/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": "minimax-4o-flash",
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 4096
        },
        timeout=120
    )
    
    if response.status_code != 200:
        print(f"ERROR: MiniMax API returned {response.status_code}: {response.text[:200]}")
        return None
    
    result = response.json()
    content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
    
    # Clean 幼儿园 blocks
    content = re.sub(r'<sup[^>]*>[^<]*</sup>', '', content)
    content = re.sub(r'<sub[^>]*>[^<]*</sub>', '', content)
    content = re.sub(r'<u>[^<]*</u>', '', content)
    content = re.sub(r'<del[^>]*>[^<]*</del>', '', content)
    content = re.sub(r'<span[^>]*>[^<]*</span>', '', content)
    
    return content.strip()


def build_translation_prompt(chunk_text, glossary_text, style_text, entities_text, chunk_info, src_lang, tgt_lang="русский"):
    """Build translation prompt with all context."""
    prompt_parts = []
    
    prompt_parts.append(f"Переведи следующий текст с {src_lang} на {tgt_lang}.")
    prompt_parts.append("")
    prompt_parts.append("## Глоссарий (обязательно соблюдать)")
    prompt_parts.append(glossary_text if glossary_text else "(нет)")
    prompt_parts.append("")
    prompt_parts.append("## Стиль")
    prompt_parts.append(style_text if style_text else "(нет)")
    prompt_parts.append("")
    prompt_parts.append("## Реестр сущностей")
    prompt_parts.append(entities_text if entities_text else "(нет)")
    prompt_parts.append("")
    
    if chunk_info.get('prev_chunk'):
        prompt_parts.append(f"## Предыдущий сегмент (для контекста)")
        prev_path = chunk_info['prev_path']
        if prev_path and os.path.exists(prev_path):
            prev_text = load_file(prev_path)
            if prev_text:
                prompt_parts.append(prev_text[:500])  # Last 500 chars of prev
        prompt_parts.append("")
    
    if chunk_info.get('next_chunk'):
        prompt_parts.append(f"## Следующий сегмент (для контекста)")
        next_path = chunk_info['next_path']
        if next_path and os.path.exists(next_path):
            next_text = load_file(next_path)
            if next_text:
                prompt_parts.append(next_text[:300])  # First 300 chars of next
        prompt_parts.append("")
    
    prompt_parts.append("## Текст для перевода")
    prompt_parts.append(chunk_text)
    prompt_parts.append("")
    prompt_parts.append("## Требования")
    prompt_parts.append("1. Сохрани всю Markdown-разметку")
    prompt_parts.append("2. Соблюдай глоссарий")
    prompt_parts.append("3. Имена собственные — по реестру")
    prompt_parts.append("4. Естественный русский язык, без калек")
    prompt_parts.append("5. Верни ТОЛЬКО переведённый текст, без пояснений")
    
    return '\n'.join(prompt_parts)


def translate_project(project_dir, src_lang="английский"):
    """Translate all chunks using MiniMax API directly."""
    chunks_dir = os.path.join(project_dir, 'chunks')
    foundation_dir = os.path.join(project_dir, 'foundation')
    draft_dir = os.path.join(project_dir, 'translations', 'draft')
    final_dir = os.path.join(project_dir, 'translations', 'final')
    
    # Load chunk map
    chunk_map_path = os.path.join(chunks_dir, 'chunk_map.json')
    if not os.path.exists(chunk_map_path):
        print("ERROR: chunk_map.json not found. Run chunk.py first.")
        sys.exit(1)
    
    with open(chunk_map_path, 'r', encoding='utf-8') as f:
        chunk_map = json.load(f)
    
    # Determine source language
    intake_path = os.path.join(project_dir, 'intake.json')
    if os.path.exists(intake_path):
        with open(intake_path, 'r', encoding='utf-8') as f:
            intake = json.load(f)
        src_lang = intake.get('source_language', src_lang)
    
    # Load foundation files
    glossary = load_file(os.path.join(foundation_dir, 'glossary.md'))
    style = load_file(os.path.join(foundation_dir, 'style.md'))
    entities = load_file(os.path.join(foundation_dir, 'entities.md'))
    
    # Ensure directories
    for d in [draft_dir, final_dir]:
        os.makedirs(d, exist_ok=True)
    
    total = len(chunk_map['chunks'])
    success = 0
    errors = 0
    
    print(f"Translating {total} chunks via MiniMax fallback...")
    
    for i, chunk in enumerate(chunk_map['chunks']):
        chunk_id = chunk['id']
        chunk_path = os.path.join(chunks_dir, f"{chunk_id}.md")
        
        if not os.path.exists(chunk_path):
            print(f"  [{i+1}/{total}] {chunk_id}: SKIP (chunk file not found)")
            continue
        
        chunk_text = load_file(chunk_path)
        if not chunk_text:
            print(f"  [{i+1}/{total}] {chunk_id}: SKIP (empty)")
            continue
        
        # Prepare context
        chunk_info = {
            'prev_chunk': chunk['prev_chunk'],
            'next_chunk': chunk['next_chunk'],
        }
        if chunk['prev_chunk']:
            chunk_info['prev_path'] = os.path.join(chunks_dir, f"{chunk['prev_chunk']}.md")
        if chunk['next_chunk']:
            chunk_info['next_path'] = os.path.join(chunks_dir, f"{chunk['next_chunk']}.md")
        
        lang_name = {
            'en': 'английского', 'fr': 'французского', 'de': 'немецкого', 
            'es': 'испанского', 'it': 'итальянского', 'zh': 'китайского',
            'ja': 'японского', 'ko': 'корейского', 'ar': 'арабского'
        }.get(src_lang, src_lang)
        
        prompt = build_translation_prompt(chunk_text, glossary, style, entities, chunk_info, lang_name)
        
        print(f"  [{i+1}/{total}] {chunk_id} ({chunk['word_count']} words)...", end=' ', flush=True)
        
        # Call MiniMax
        result = call_minimax(prompt)
        
        if result:
            # Save draft
            draft_path = os.path.join(draft_dir, f"{chunk_id}.md")
            with open(draft_path, 'w', encoding='utf-8') as f:
                f.write(result)
            
            # Same as final for fallback
            final_path = os.path.join(final_dir, f"{chunk_id}.md")
            with open(final_path, 'w', encoding='utf-8') as f:
                f.write(result)
            
            success += 1
            print(f"✅ ({len(result.split())} words)")
        else:
            errors += 1
            print("❌ FAILED")
        
        # Rate limiting
        if i < total - 1:
            time.sleep(0.5)
    
    print(f"\nTranslation complete: {success}/{total} success, {errors} errors")
    
    return {'success': success, 'total': total, 'errors': errors}


if __name__ == '__main__':
    src_lang = "английский"
    if len(sys.argv) < 2:
        print("Usage: python translate_fallback.py <project-dir> [source-language-ru]")
        print("  source-language examples: английский, французский, немецкий, китайский")
        sys.exit(1)
    if len(sys.argv) >= 3:
        src_lang = sys.argv[2]
    translate_project(sys.argv[1], src_lang)
