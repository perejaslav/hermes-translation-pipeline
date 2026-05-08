#!/usr/bin/env python3
"""
Translation Pipeline — Chunking Script

Разбивает source.md на сегменты (chunks) по заголовкам и параграфам.
Каждый chunk = 500-1500 слов.
Сохраняет chunk_map.json и отдельные файлы chunks/chunk_NNN.md.

Usage:
    python chunk.py <project-dir>
"""

import sys
import json
import os
import re
import math


def ensure_dir(d):
    os.makedirs(d, exist_ok=True)


def slugify(text):
    return re.sub(r'[^a-zA-Zа-яА-Я0-9\s-]', '', text).strip().lower().replace(' ', '-')[:40]


def parse_headings(source_text):
    """Разделяет текст на секции по заголовкам Markdown."""
    lines = source_text.split('\n')
    sections = []
    current_section = {'heading': 'preamble', 'level': 0, 'lines': [], 'start_line': 0}
    
    for i, line in enumerate(lines):
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if heading_match:
            if current_section['lines']:
                sections.append(current_section)
            level = len(heading_match.group(1))
            heading = heading_match.group(2).strip()
            current_section = {'heading': heading, 'level': level, 'lines': [], 'start_line': i}
        current_section['lines'].append(line)
    
    if current_section['lines']:
        sections.append(current_section)
    
    return sections


def chunk_section(section, section_index):
    """Разбивает секцию на под-сегменты по параграфам."""
    text = '\n'.join(section['lines'])
    paragraphs = re.split(r'\n\n+', text)
    chunks = []
    current_chunk = []
    current_words = 0
    
    for para in paragraphs:
        para_words = len(para.split())
        
        # Если параграф сам больше max (1500), разбиваем его
        if para_words > 1500:
            if current_chunk:
                chunks.append({
                    'lines': '\n\n'.join(current_chunk),
                    'word_count': current_words,
                    'start_para': len(chunks)
                })
                current_chunk = []
                current_words = 0
            # Разбиваем большой параграф на предложения
            sentences = re.split(r'(?<=[.!?])\s+', para)
            temp_chunk = []
            temp_words = 0
            for sent in sentences:
                sent_words = len(sent.split())
                if temp_words + sent_words > 1500 and temp_words > 500:
                    chunks.append({
                        'lines': ' '.join(temp_chunk),
                        'word_count': temp_words,
                        'start_para': len(chunks)
                    })
                    temp_chunk = []
                    temp_words = 0
                temp_chunk.append(sent)
                temp_words += sent_words
            if temp_chunk:
                chunks.append({
                    'lines': ' '.join(temp_chunk),
                    'word_count': temp_words,
                    'start_para': len(chunks)
                })
            continue
        
        # Если текущий chunk + новый параграф > 1500, финализируем chunk
        if current_words + para_words > 1500 and current_words >= 400:
            chunks.append({
                'lines': '\n\n'.join(current_chunk),
                'word_count': current_words,
                'start_para': len(chunks)
            })
            current_chunk = []
            current_words = 0
        
        current_chunk.append(para)
        current_words += para_words
    
    if current_chunk:
        chunks.append({
            'lines': '\n\n'.join(current_chunk),
            'word_count': current_words,
            'start_para': len(chunks)
        })
    
    return chunks


def extract_terms_from_chunk(text, glossary_terms=None):
    """Извлекает термины из глоссария, встречающиеся в тексте."""
    found = []
    if glossary_terms:
        for term in glossary_terms:
            if term.lower() in text.lower():
                found.append(term)
    return found


def chunk_document(project_dir):
    """Main chunking function."""
    source_path = os.path.join(project_dir, 'source', 'source.md')
    chunks_dir = os.path.join(project_dir, 'chunks')
    foundation_dir = os.path.join(project_dir, 'foundation')
    ensure_dir(chunks_dir)
    
    # Read source
    if not os.path.exists(source_path):
        print(f"ERROR: source.md not found at {source_path}")
        sys.exit(1)
    
    with open(source_path, 'r', encoding='utf-8') as f:
        source_text = f.read()
    
    total_words = len(source_text.split())
    print(f"Source: {total_words} words")
    
    # Load glossary if exists
    glossary_terms = []
    glossary_path = os.path.join(foundation_dir, 'glossary.md')
    if os.path.exists(glossary_path):
        with open(glossary_path, 'r', encoding='utf-8') as f:
            for line in f:
                if '|' in line and not line.startswith('| ---') and not line.startswith('| source'):
                    parts = [p.strip() for p in line.split('|') if p.strip()]
                    if len(parts) >= 2:
                        glossary_terms.append(parts[0])
    
    # Parse sections by headings
    sections = parse_headings(source_text)
    print(f"Found {len(sections)} sections")
    
    # Create chunks
    all_chunks = []
    for si, section in enumerate(sections):
        section_chunks = chunk_section(section, si)
        heading_prefix = section['heading'] if section['heading'] != 'preamble' else ''
        
        for chunk in section_chunks:
            chunk_terms = extract_terms_from_chunk(chunk['lines'], glossary_terms)
            all_chunks.append({
                'heading': heading_prefix,
                'text': chunk['lines'],
                'word_count': chunk['word_count'],
                'terms': chunk_terms
            })
    
    # Limit chunk size if still too big
    final_chunks = []
    for chunk in all_chunks:
        if chunk['word_count'] > 1500:
            # Split by double newlines
            sub_blocks = re.split(r'\n\n+', chunk['text'])
            sub_chunk = []
            sub_words = 0
            for block in sub_blocks:
                bw = len(block.split())
                if sub_words + bw > 1500 and sub_words >= 400:
                    final_chunks.append({
                        'text': '\n\n'.join(sub_chunk),
                        'word_count': sub_words,
                        'heading': chunk['heading'],
                        'terms': chunk['terms']
                    })
                    sub_chunk = []
                    sub_words = 0
                sub_chunk.append(block)
                sub_words += bw
            if sub_chunk:
                final_chunks.append({
                    'text': '\n\n'.join(sub_chunk),
                    'word_count': sub_words,
                    'heading': chunk['heading'],
                    'terms': chunk['terms']
                })
        else:
            final_chunks.append(chunk)
    
    print(f"Created {len(final_chunks)} chunks")
    
    # Build chunk map
    total_words_chunked = sum(c['word_count'] for c in final_chunks)
    chunk_map = {
        'total_chunks': len(final_chunks),
        'total_words_source': total_words,
        'total_words_chunked': total_words_chunked,
        'chunks': []
    }
    
    for i, chunk in enumerate(final_chunks):
        chunk_id = f"chunk_{i+1:03d}"
        prev_id = f"chunk_{i:03d}" if i > 0 else None
        next_id = f"chunk_{i+2:03d}" if i < len(final_chunks) - 1 else None
        
        chunk_info = {
            'id': chunk_id,
            'title': chunk['heading'] if chunk['heading'] else f"Segment {i+1}",
            'chapter': chunk['heading'].split('»')[0].strip() if chunk['heading'] else '',
            'word_count': chunk['word_count'],
            'prev_chunk': prev_id,
            'next_chunk': next_id,
            'terms': chunk['terms']
        }
        chunk_map['chunks'].append(chunk_info)
        
        # Write chunk file
        chunk_path = os.path.join(chunks_dir, f"{chunk_id}.md")
        with open(chunk_path, 'w', encoding='utf-8') as f:
            if chunk['heading']:
                f.write(f"# {chunk['heading']}\n\n")
            f.write(chunk['text'])
        
        print(f"  {chunk_id}: {chunk['word_count']} words ({chunk['heading'] or 'no heading'})")
    
    # Write chunk map
    chunk_map_path = os.path.join(project_dir, 'chunks', 'chunk_map.json')
    with open(chunk_map_path, 'w', encoding='utf-8') as f:
        json.dump(chunk_map, f, ensure_ascii=False, indent=2)
    
    print(f"\nChunk map saved: {chunk_map_path}")
    print(f"Total chunks: {len(final_chunks)}")
    
    return chunk_map


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python chunk.py <project-dir>")
        sys.exit(1)
    chunk_document(sys.argv[1])
