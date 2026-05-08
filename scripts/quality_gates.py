#!/usr/bin/env python3
"""
Translation Pipeline — Quality Gates

Проверяет качество перевода по 5 gates:
  G1: Терминология (глоссарий соблюдён?)
  G2: Целостность (все сегменты переведены?)
  G3: Единство стиля (LLM-проход)
  G4: Плавность (читаемость на русском)
  G5: Форматирование (разметка не сломана)

Usage:
    python quality_gates.py <project-dir>
"""

import sys
import json
import os
import re


def ensure_dir(d):
    os.makedirs(d, exist_ok=True)


def load_file(path):
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def gate1_terminology(project_dir, report_lines):
    """G1: Проверка соблюдения глоссария."""
    glossary_path = os.path.join(project_dir, 'foundation', 'glossary.md')
    translations_dir = os.path.join(project_dir, 'translations', 'final')
    
    if not os.path.exists(glossary_path):
        report_lines.append("## G1: Terminology Audit — ⚠️ SKIP (нет глоссария)")
        return True
    
    # Parse glossary
    glossary = {}
    content = load_file(glossary_path)
    for line in content.split('\n'):
        if '|' in line and not line.startswith('| ---') and not line.startswith('| source'):
            parts = [p.strip() for p in line.split('|') if p.strip()]
            if len(parts) >= 2:
                glossary[parts[0].lower()] = parts[1]
    
    if not glossary:
        report_lines.append("## G1: Terminology Audit — ⚠️ SKIP (глоссарий пуст)")
        return True
    
    violations = 0
    checked = 0
    
    for fname in sorted(os.listdir(translations_dir)):
        if not fname.endswith('.md'):
            continue
        text = load_file(os.path.join(translations_dir, fname))
        if not text:
            continue
        
        # Check if source terms appear untranslated in the target text
        # (crude check — looks for English source terms in Russian translation)
        text_lower = text.lower()
        for src_term, tgt_term in glossary.items():
            if len(src_term.split()) >= 1:
                checked += 1
                # If source term (Latin) appears in translation and it's not already the target
                if re.match(r'^[a-zA-Z]', src_term):
                    found_src = text_lower.count(src_term.lower())
                    # Target term should appear instead
                    found_tgt = text_lower.count(tgt_term.lower())
                    if found_src > 0:
                        violations += 1
                        if violations <= 10:  # cap report
                            report_lines.append(f"  ❌ '{src_term}' → '{tgt_term}' в {fname}: найдено '{src_term}' ({found_src}x), целевой '{tgt_term}' ({found_tgt}x)")
    
    if violations == 0:
        report_lines.append(f"## G1: Terminology Audit — ✅ PASS (проверено {checked} терминов)")
    else:
        report_lines.append(f"## G1: Terminology Audit — ⚠️ {violations} нарушений (из {checked} проверенных)")
    
    return violations == 0


def gate2_completeness(project_dir, report_lines):
    """G2: Проверка целостности — все ли сегменты переведены."""
    chunks_dir = os.path.join(project_dir, 'chunks')
    draft_dir = os.path.join(project_dir, 'translations', 'draft')
    final_dir = os.path.join(project_dir, 'translations', 'final')
    
    chunk_map_path = os.path.join(chunks_dir, 'chunk_map.json')
    if not os.path.exists(chunk_map_path):
        report_lines.append("## G2: Completeness — ❌ FAIL (нет chunk_map.json)")
        return False
    
    with open(chunk_map_path, 'r', encoding='utf-8') as f:
        chunk_map = json.load(f)
    
    total = chunk_map['total_chunks']
    drafts = len([f for f in os.listdir(draft_dir) if f.endswith('.md')]) if os.path.exists(draft_dir) else 0
    finals = len([f for f in os.listdir(final_dir) if f.endswith('.md')]) if os.path.exists(final_dir) else 0
    
    report_lines.append(f"## G2: Completeness Check")
    report_lines.append(f"  Всего chunks: {total}")
    report_lines.append(f"  Черновиков: {drafts}")
    report_lines.append(f"  Финальных: {finals}")
    
    all_complete = (finals == total)
    if all_complete:
        report_lines.append("  ✅ PASS — все сегменты переведены и в финале")
    else:
        missing = total - finals
        report_lines.append(f"  ❌ FAIL — отсутствует {missing} сегментов")
    
    return all_complete


def gate3_style_consistency(project_dir, report_lines):
    """G3: Единство стиля — проверка согласованности стиля по всем сегментам."""
    final_dir = os.path.join(project_dir, 'translations', 'final')
    style_path = os.path.join(project_dir, 'foundation', 'style.md')
    
    if not os.path.exists(final_dir):
        report_lines.append("## G3: Style Consistency — ❌ FAIL (нет финальных переводов)")
        return False
    
    issues = []
    
    # Check for common style issues
    translations = []
    for fname in sorted(os.listdir(final_dir)):
        if fname.endswith('.md'):
            text = load_file(os.path.join(final_dir, fname))
            if text:
                translations.append({'file': fname, 'text': text})
    
    all_text = '\n'.join(t['text'] for t in translations)
    
    # Check for English paragraphs left untranslated
    en_paragraphs = 0
    for para in all_text.split('\n\n'):
        en_words = len(re.findall(r'\b[a-zA-Z]{3,}\b', para))
        ru_words = len(re.findall(r'\b[а-яА-ЯёЁ]{3,}\b', para))
        total = en_words + ru_words
        if total > 10 and en_words / total > 0.5:
            en_paragraphs += 1
    
    if en_paragraphs > 0:
        issues.append(f"Найдено {en_paragraphs} параграфов с преобладанием английского (непереведённые куски?)")
    
    # Check for mixed ты/Вы
    ты_count = len(re.findall(r'\bты\b', all_text, re.IGNORECASE))
    вы_count_formal = len(re.findall(r'\bВы\b', all_text))
    if ты_count > 0 and вы_count_formal > 0:
        issues.append(f"Смешение 'ты' ({ты_count}) и 'Вы' ({вы_count_formal}) — возможно, несогласованность")
    
    # Check for obvious AI-isms in Russian
    ai_patterns = [
        (r'является\s+[а-яА-ЯёЁ]+\w+\s+[а-яА-ЯёЁ]+\w+', 'канцелярит ("является ...")'),
        (r'в\s+данном\s+контексте', 'калька ("в данном контексте")'),
        (r'следует\s+отметить', 'калька ("следует отметить")'),
        (r'важно\s+подчеркнуть', 'калька ("важно подчеркнуть")'),
        (r'необходимо\s+учитывать', 'калька ("необходимо учитывать")'),
    ]
    ai_issue_count = 0
    for pattern, desc in ai_patterns:
        count = len(re.findall(pattern, all_text, re.IGNORECASE))
        if count > 2:
            ai_issue_count += count
            issues.append(f"Калька/канцелярит: '{desc}' ({count} раз)")
    
    # Check for consistent chapter headings
    headings = re.findall(r'^#\s+(.+)$', all_text, re.MULTILINE)
    
    report_lines.append(f"## G3: Style Consistency")
    
    if not issues:
        report_lines.append("  ✅ PASS — стиль согласован, замечаний нет")
    else:
        report_lines.append(f"  ⚠️ Найдено {len(issues)} замечаний:")
        for issue in issues:
            report_lines.append(f"  • {issue}")
    
    return len(issues) == 0


def gate4_fluency(project_dir, report_lines):
    """G4: Плавность — проверка читаемости русского текста."""
    final_dir = os.path.join(project_dir, 'translations', 'final')
    if not os.path.exists(final_dir):
        report_lines.append("## G4: Fluency — ❌ FAIL (нет финальных переводов)")
        return False
    
    issues = []
    
    all_text = ''
    for fname in sorted(os.listdir(final_dir)):
        if fname.endswith('.md'):
            text = load_file(os.path.join(final_dir, fname))
            if text:
                all_text += text + '\n'
    
    sentences = re.split(r'(?<=[.!?])\s+', all_text)
    long_sentences = 0
    for s in sentences:
        words = len(s.split())
        if words > 40:
            long_sentences += 1
    
    if long_sentences > 5:
        issues.append(f"{long_sentences} предложений длиннее 40 слов — стоит разбить")
    
    # Check for foreign punctuation
    typographic_issues = len(re.findall(r' \([^)]+\)\s*\(', all_text))  # nested parens
    if typographic_issues > 3:
        issues.append(f"Вложенные скобки ({typographic_issues}) — перегружает текст")
    
    # Check for quote consistency
    quotes_en = len(re.findall(r'"[^"]*"', all_text))
    quotes_ru = len(re.findall(r'«[^»]*»', all_text))
    quotes_ru2 = len(re.findall(r'„[^“]*“', all_text))
    
    report_lines.append(f"## G4: Fluency")
    report_lines.append(f"  Предложений всего: {len(sentences)}")
    report_lines.append(f"  Длинных (>40 слов): {long_sentences}")
    report_lines.append(f"  Кавычки: английские \"\" {quotes_en}, русские «» {quotes_ru}, немецкие „“ {quotes_ru2}")
    
    if not issues:
        report_lines.append("  ✅ PASS — текст читаемый, естественный")
    else:
        report_lines.append(f"  ⚠️ {len(issues)} замечаний по читаемости:")
        for issue in issues:
            report_lines.append(f"  • {issue}")
    
    return len(issues) == 0


def gate5_formatting(project_dir, report_lines):
    """G5: Сохранение форматирования Markdown."""
    source_path = os.path.join(project_dir, 'source', 'source.md')
    manuscript_path = os.path.join(project_dir, 'manuscript.md')
    
    if not os.path.exists(manuscript_path):
        manuscript_path = os.path.join(project_dir, 'translations', 'final')
        if os.path.isdir(manuscript_path):
            report_lines.append("## G5: Format Preservation — ⚠️ SKIP (manuscript.md не собран)")
            return True
    
    issues = []
    
    if os.path.isfile(manuscript_path):
        text = load_file(manuscript_path)
    else:
        # Check individual files instead
        final_dir = manuscript_path
        text = ''
        for fname in sorted(os.listdir(final_dir)):
            if fname.endswith('.md'):
                t = load_file(os.path.join(final_dir, fname))
                if t:
                    text += t + '\n'
    
    # Check broken links
    broken_links = 0
    for match in re.finditer(r'\[([^\]]*)\]\(([^)]*)\)', text):
        url = match.group(2).strip()
        if not url or url.isspace():
            broken_links += 1
    
    if broken_links > 0:
        issues.append(f"{broken_links} битых ссылок")
    
    # Check unclosed code blocks
    code_fences = len(re.findall(r'```', text))
    if code_fences % 2 != 0:
        issues.append("Непарные блоки кода (```)")
    
    # Check for unclosed inline code
    inline_codes = len(re.findall(r'(?<!`)`(?!`)([^`]*)`(?!`)', text))
    
    report_lines.append(f"## G5: Format Preservation")
    if source_path and os.path.exists(source_path):
        src = load_file(source_path)
        src_headings = len(re.findall(r'^#+\s+', src, re.MULTILINE))
        tgt_headings = len(re.findall(r'^#+\s+', text, re.MULTILINE))
        report_lines.append(f"  Заголовки: исходник {src_headings}, перевод {tgt_headings}")
    
    if not issues:
        report_lines.append("  ✅ PASS — форматирование сохранено")
    else:
        report_lines.append(f"  ⚠️ {len(issues)} замечаний по форматированию:")
        for issue in issues:
            report_lines.append(f"  • {issue}")
    
    return len(issues) == 0


def run_quality_gates(project_dir):
    """Run all 5 quality gates and produce a report."""
    quality_dir = os.path.join(project_dir, 'quality')
    ensure_dir(quality_dir)
    
    report_lines = [
        "# Quality Report",
        f"Project: {project_dir}",
        f"Timestamp: {__import__('datetime').datetime.now().isoformat()}",
        "",
        "---",
        ""
    ]
    
    gates = [
        ("G1", gate1_terminology),
        ("G2", gate2_completeness),
        ("G3", gate3_style_consistency),
        ("G4", gate4_fluency),
        ("G5", gate5_formatting),
    ]
    
    results = {}
    for name, func in gates:
        try:
            result = func(project_dir, report_lines)
            results[name] = result
        except Exception as e:
            report_lines.append(f"## {name} — ❌ ERROR: {e}")
            results[name] = False
        report_lines.append("")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    report_lines.append("---")
    report_lines.append(f"## Итог: {passed}/{total} gates пройдено")
    if passed == total:
        report_lines.append("✅ Все проверки пройдены — перевод готов к сборке!")
    else:
        failed = [k for k, v in results.items() if not v]
        report_lines.append(f"❌ Не пройдены: {', '.join(failed)}")
        report_lines.append("Рекомендуется доработка перед сборкой.")
    
    report = '\n'.join(report_lines)
    report_path = os.path.join(quality_dir, 'report.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"Quality report: {report_path}")
    print(f"Gates: {passed}/{total} passed")
    
    return results


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python quality_gates.py <project-dir>")
        sys.exit(1)
    run_quality_gates(sys.argv[1])
