#!/usr/bin/env python3
"""
Translation Pipeline — Assembly Script

Собирает финальный перевод из сегментов в единый документ.
Проверяет структуру, заголовки, целостность.
Сохраняет manuscript.md и экспортирует в /root/outputs/.

Usage:
    python assembly.py <project-dir>
"""

import sys
import json
import os
import re
import shutil
from datetime import datetime


def ensure_dir(d):
    os.makedirs(d, exist_ok=True)


def load_file(path):
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def assemble(project_dir):
    """Assemble final manuscript from chunks."""
    chunks_dir = os.path.join(project_dir, 'chunks')
    final_dir = os.path.join(project_dir, 'translations', 'final')
    draft_dir = os.path.join(project_dir, 'translations', 'draft')
    
    # Load chunk map
    chunk_map_path = os.path.join(chunks_dir, 'chunk_map.json')
    if not os.path.exists(chunk_map_path):
        print("ERROR: chunk_map.json not found. Run chunk.py first.")
        sys.exit(1)
    
    with open(chunk_map_path, 'r', encoding='utf-8') as f:
        chunk_map = json.load(f)
    
    # Use final if available, else draft
    source_dir = final_dir if os.path.exists(final_dir) and os.listdir(final_dir) else draft_dir
    
    if not os.path.exists(source_dir) or not os.listdir(source_dir):
        print("ERROR: No translations found. Run translation first.")
        sys.exit(1)
    
    # Assemble in order
    manuscript_parts = []
    total_words = 0
    missing_chunks = []
    empty_chunks = []
    
    for chunk in chunk_map['chunks']:
        chunk_id = chunk['id']
        chunk_path = os.path.join(source_dir, f"{chunk_id}.md")
        
        if not os.path.exists(chunk_path):
            # Try to find by id prefix
            alt_path = os.path.join(source_dir, f"{chunk_id}.md")
            if not os.path.exists(alt_path):
                missing_chunks.append(chunk_id)
                continue
            chunk_path = alt_path
        
        text = load_file(chunk_path)
        if not text or text.strip() == '':
            empty_chunks.append(chunk_id)
            continue
        
        manuscript_parts.append(text)
        total_words += len(text.split())
    
    if missing_chunks:
        print(f"WARNING: Missing chunks: {missing_chunks}")
    
    if empty_chunks:
        print(f"WARNING: Empty chunks: {empty_chunks}")
    
    manuscript = '\n\n'.join(manuscript_parts)
    
    # Count words
    print(f"Manuscript: {total_words} words, {len(manuscript_parts)} chunks assembled")
    
    # Save manuscript.md
    manuscript_path = os.path.join(project_dir, 'manuscript.md')
    with open(manuscript_path, 'w', encoding='utf-8') as f:
        f.write(manuscript)
    print(f"Saved: {manuscript_path}")
    
    # Copy to /root/outputs/
    outputs_dir = '/root/outputs'
    ensure_dir(outputs_dir)
    project_name = os.path.basename(project_dir.rstrip('/'))
    output_path = os.path.join(outputs_dir, f"{project_name}-translation.md")
    
    # Try to get original filename
    intake_path = os.path.join(project_dir, 'intake.json')
    if os.path.exists(intake_path):
        try:
            with open(intake_path, 'r', encoding='utf-8') as f:
                intake = json.load(f)
            src_name = os.path.basename(intake.get('source_path', ''))
            if src_name:
                base = re.sub(r'\.[^.]+$', '', src_name)
                output_path = os.path.join(outputs_dir, f"{base}-ru.md")
        except:
            pass
    
    shutil.copy2(manuscript_path, output_path)
    print(f"Exported to outputs: {output_path}")
    
    # Also save to output subdir
    output_dir = os.path.join(project_dir, 'output')
    ensure_dir(output_dir)
    output_local = os.path.join(output_dir, 'translated_document.md')
    shutil.copy2(manuscript_path, output_local)
    
    return {
        'manuscript_path': manuscript_path,
        'output_path': output_path,
        'total_words': total_words,
        'total_chunks': len(manuscript_parts),
        'missing_chunks': missing_chunks,
        'empty_chunks': empty_chunks
    }


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python assembly.py <project-dir>")
        sys.exit(1)
    result = assemble(sys.argv[1])
    print(f"\nDone. Manuscript at: {result['output_path']}")
