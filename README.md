# Hermes Translation Pipeline

Многостадийный пайплайн для перевода длинных и сложных документов (книги, статьи, техническая документация, научные работы) с любого языка на русский. Работает как скилл для [Hermes Agent](https://hermes-agent.nousresearch.com).

Архитектура: **Ingestion → Foundation → Chunking → Parallel Translation → Quality Gates → Assembly**.

## Возможности

- **Ingestion** — извлечение текста из PDF, DOCX, EPUB, MD, HTML, TXT (через Pandoc)
- **Foundation** — автоматическое построение глоссария, стилистических правил и реестра сущностей
- **Chunking** — сегментация на блоки 500–1500 слов с контекстными переходами
- **Parallel Translation** — перевод через координированных субагентов (2 волны: черновик → доработка)
- **Quality Gates** — 5 стадий проверки: терминология, целостность, стиль, плавность, форматирование
- **Assembly** — склейка, финальная валидация, экспорт

## Установка в Hermes Agent

### Вариант 1: Через CLI (рекомендуется)

```bash
# Клонировать репозиторий
git clone https://github.com/perejaslav/hermes-translation-pipeline.git
cd hermes-translation-pipeline

# Установить скиллы
cp -r skills/translation-pipeline ~/.hermes/skills/software-development/
cp -r skills/translation-worker ~/.hermes/skills/software-development/

# Установить скрипты (для fallback-режима)
mkdir -p ~/.hermes/scripts/translation-pipeline
cp scripts/*.py ~/.hermes/scripts/translation-pipeline/

# Установить шаблоны
cp -r templates ~/.hermes/skills/software-development/translation-pipeline/
```

### Вариант 2: Через Hermes Agent (если скилл зарегистрирован)

```bash
hermes skill install translation-pipeline
hermes skill install translation-worker
```

### Зависимости

- **Hermes Agent** (любая версия с поддержкой субагентов)
- **Python 3.10+** (для скриптов fallback)
- **Pandoc** (для конвертации PDF/DOCX/EPUB): `apt install pandoc`
- **Доступ к API:** MiniMax (основной провайдер для переводов)
- **Доступ к субагентам:** для параллельного перевода (рекомендуется)

## Структура репозитория

```
hermes-translation-pipeline/
├── README.md
├── LICENSE
├── skills/
│   ├── translation-pipeline/     # Основной скилл-оркестратор
│   │   └── SKILL.md
│   └── translation-worker/       # Скилл для субагента-переводчика
│       └── SKILL.md
├── scripts/                      # Python-скрипты для fallback-режима
│   ├── translate_fallback.py     # Прямой перевод через MiniMax API
│   ├── project_init.py           # Инициализация проекта
│   ├── chunk.py                  # Сегментация текста
│   ├── build_foundation.py       # Построение глоссария и стиля
│   ├── quality_gates.py          # Проверки качества
│   └── assembly.py               # Склейка и экспорт
└── templates/                    # Шаблоны для foundation
    ├── intake.json
    ├── glossary.md
    ├── entities.md
    └── style.md
```

## Pipeline (подробно)

```
Исходный документ
       ↓
┌──────────────────┐
│  1. Ingestion    │  — извлечение, определение языка, NER
└──────────────────┘
       ↓
┌──────────────────┐
│  2. Foundation   │  — глоссарий, стиль, реестр сущностей
└──────────────────┘
       ↓
┌──────────────────┐
│  3. Chunking     │  — сегментация на блоки 500–1500 слов
└──────────────────┘
       ↓
┌──────────────────┐
│  4. Translation  │  — параллельный перевод субагентами
│  (2 волны)       │    волна 1: черновик, волна 2: доработка
└──────────────────┘
       ↓
┌──────────────────┐
│  5. Quality Gates│  — термины, целостность, стиль, плавность
└──────────────────┘
       ↓
┌──────────────────┐
│  6. Assembly     │  — склейка, финальная проверка, экспорт
└──────────────────┘
       ↓
  Готовый перевод
```

## Использование в Hermes Agent

После установки скиллов можно запускать перевод через Telegram или CLI:

**Telegram:** скажите «запусти перевод книги» или «переведи документ» — Hermes активирует пайплайн.

**CLI:** используйте `delegate_task` с подключёнными скиллами `translation-pipeline` и `translation-worker`.

## Структура проекта перевода

```
/root/apps/translation-pipeline/projects/<slug>/
├── intake.json              # метаданные проекта
├── source/
│   └── source.md            # извлечённый текст
├── foundation/
│   ├── glossary.md          # глоссарий
│   ├── style.md             # стиль
│   └── entities.md          # сущности
├── chunks/                  # сегменты
├── translations/
│   ├── draft/               # черновики
│   └── final/               # финальные переводы
├── quality/
│   └── report.md            # отчёт проверок
├── manuscript.md            # полный перевод
└── output/                  # экспорт
```

## Fallback-режим

При недоступности субагентов (opencode-go 404) пайплайн автоматически переключается на последовательный перевод через MiniMax API напрямую. Скрипты в `scripts/` обеспечивают этот режим.

## Лицензия

MIT
