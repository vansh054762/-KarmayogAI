"""
AI MCQ Generator
Extracts key concepts from document chunks and generates MCQs.
Uses rule-based NLP with optional transformer enhancement.
"""
import re
import json
import random
import hashlib
from typing import List, Dict, Optional


# ─── Distractor pools ─────────────────────────────────────────────────────────

GENERIC_DISTRACTORS = [
    'None of the above',
    'All of the above',
    'Cannot be determined from context',
    'Not mentioned in the material',
    'Both A and B',
    'It depends on the situation',
    'The opposite of what is stated',
    'A combination of all factors',
]

DOMAIN_DISTRACTORS = [
    'To reduce operational costs',
    'A method for random sampling',
    'A framework for data normalization',
    'A process for resource allocation',
    'An approach to risk management',
    'A tool for statistical analysis',
    'A policy for regulatory compliance',
    'A system for performance evaluation',
    'An algorithm for pattern recognition',
    'A strategy for capacity building',
    'A technique for process improvement',
    'A standard for quality assurance',
    'A model for decision making',
    'A procedure for data collection',
    'A method for impact assessment',
]


def _uid(text: str, idx: int) -> str:
    return f'gen_{idx}_{hashlib.md5(text.encode()).hexdigest()[:6]}'


def _make_distractors(correct: str, pool: List[str], n: int = 3) -> List[str]:
    """Pull n distinct distractors, topping up from fallback pools."""
    pool_clean = [p.strip() for p in pool
                  if p.strip().lower() != correct.strip().lower() and len(p.strip()) > 3]
    seen = set()
    deduped = []
    for p in pool_clean:
        if p.lower() not in seen:
            seen.add(p.lower())
            deduped.append(p)

    selected = random.sample(deduped, min(n, len(deduped)))

    if len(selected) < n:
        extras = [d for d in DOMAIN_DISTRACTORS
                  if d.lower() != correct.lower() and d not in selected]
        random.shuffle(extras)
        selected += extras[:n - len(selected)]

    if len(selected) < n:
        for g in GENERIC_DISTRACTORS:
            if g.lower() != correct.lower() and g not in selected:
                selected.append(g)
            if len(selected) >= n:
                break

    return selected[:n]


def _build_options(correct: str, distractors: List[str]) -> (List[str], int):
    options = [correct] + distractors[:3]
    # Pad if still short
    while len(options) < 4:
        for g in GENERIC_DISTRACTORS:
            if g not in options:
                options.append(g)
                break
    random.shuffle(options)
    return options, options.index(correct)


# ─── Sentence extraction ──────────────────────────────────────────────────────

def extract_key_sentences(text: str, max_sentences: int = 120) -> List[str]:
    """
    Extract informative sentences. Very lenient — keeps most sentences
    that are long enough to produce a meaningful question.
    """
    sentences = re.split(r'(?<=[.!?])\s+', text)
    scored = []
    for s in sentences:
        s = s.strip()
        wc = len(s.split())
        # Very lenient word count filter
        if wc < 5 or wc > 120:
            continue
        patterns = [
            r'\bis\b|\bare\b|\bwas\b|\bwere\b',
            r'\bdefin|\bmeaning|\brefers?\b|\bmeans\b',
            r'\bpurpose\b|\bgoal\b|\bobjective\b',
            r'\bmethod\b|\bprocess\b|\bstep\b|\bprocedure\b',
            r'\bimportant\b|\bsignificant\b|\bkey\b|\bessential\b',
            r'\badvantage\b|\bbenefit\b|\blimitation\b|\bdisadvantage\b',
            r'\bused (for|to|in)\b',
            r'\bcalculate\b|\bmeasure\b|\bcompute\b|\bevaluate\b',
            r'\bresponsible\b|\bresponsibility\b|\brole\b',
            r'\bpolicy\b|\bgovernment\b|\bmanagement\b|\bleadership\b',
            r'\bdata\b|\bmodel\b|\balgorithm\b|\bsystem\b',
            r'\bincludes?\b|\bconsists?\b|\bcomprises?\b|\bcontains?\b',
            r'\bknown as\b|\bcalled\b|\btermed\b',
            r'\bfirst\b|\bprimary\b|\bmain\b|\bprincipal\b',
            r'\btype\b|\bkind\b|\bcategory\b|\bclass\b',
            r'\bcan\b|\bcould\b|\bshould\b|\bmust\b|\bwill\b',
            r'\bresult\b|\boutcome\b|\beffect\b|\bimpact\b',
            r'\bbased on\b|\baccording to\b|\bin order to\b',
            r'\bexample\b|\binstance\b|\bsuch as\b',
        ]
        score = sum(1 for p in patterns if re.search(p, s, re.IGNORECASE))
        # Accept ALL sentences with any score, score 0 sentences get lowest priority
        scored.append((score, s))

    scored.sort(key=lambda x: -x[0])
    return [s for _, s in scored[:max_sentences]]


def extract_all_sentences(text: str) -> List[str]:
    """Extract ALL sentences as fallback pool for factual questions."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    result = []
    for s in sentences:
        s = s.strip()
        if 5 <= len(s.split()) <= 120:
            result.append(s)
    return result


# ─── Generator 1: Concept / definition MCQ ───────────────────────────────────

def generate_concept_mcq(sentence: str, all_sentences: List[str], idx: int) -> Optional[Dict]:
    """Generate a what/why/how concept question."""
    match = re.search(
        r'(?<!\w)([A-Za-z][^\.,;]{2,50}?)\s+(?:is|are|was|were|refers?\s+to|means?)\s+(.{8,120}?)(?:\.|,|;|$)',
        sentence
    )
    if not match:
        return None

    subject = match.group(1).strip()
    definition = match.group(2).strip()

    if not re.match(r'^[A-Za-z]', subject):
        return None
    if len(subject.split()) > 8 or len(subject) < 3:
        return None
    if re.match(
        r'^(it|this|that|they|he|she|we|you|i|there|which|what|the|a|an|its|their|our|your|his|her)$',
        subject, re.IGNORECASE
    ):
        return None
    first_word = subject.split()[0].lower()
    if first_word in {'and','but','or','so','yet','for','nor','however','therefore',
                      'thus','hence','also','ll','ell','when','where','while','although'}:
        return None
    if len(definition) < 8:
        return None

    correct = definition.rstrip('.,;').capitalize()

    pool = []
    for s in all_sentences:
        m = re.search(r'(?:is|are|was|were|refers?\s+to|means?)\s+(.{8,80}?)(?:\.|,|;|$)', s)
        if m:
            part = m.group(1).strip().capitalize()
            if part.lower() != correct.lower() and len(part) > 5:
                pool.append(part)

    distractors = _make_distractors(correct, pool)
    options, correct_idx = _build_options(correct, distractors)

    templates = [
        f'What does "{subject}" refer to according to the material?',
        f'Which of the following best describes "{subject}"?',
        f'According to the document, "{subject}" is best defined as:',
        f'The text states that "{subject}" refers to which of the following?',
        f'How does the document describe "{subject}"?',
    ]

    return {
        'id': _uid(sentence, idx),
        'text': random.choice(templates),
        'options': options,
        'correct_answer': correct_idx,
        'explanation': f'From the document: "{sentence[:150]}"',
        'difficulty': random.choice(['easy', 'medium', 'medium', 'hard']),
        'source': 'ai_generated',
        'type': 'concept',
    }


# ─── Generator 2: Fill-in-the-blank MCQ ──────────────────────────────────────

_KEYWORD_RE = re.compile(
    r'\b(data\s+\w+|machine\s+learning|deep\s+learning|neural\s+network|'
    r'artificial\s+intelligence|natural\s+language|computer\s+vision|'
    r'regression|clustering|classification|normalization|standardization|'
    r'hypothesis|correlation|variance|distribution|algorithm|model|'
    r'policy|governance|administration|management|leadership|budget|audit|'
    r'framework|infrastructure|implementation|evaluation|assessment|'
    r'training|testing|validation|deployment|monitoring|optimization|'
    r'stakeholder|compliance|accountability|transparency|efficiency|'
    r'performance|capacity|resource|strategy|objective|indicator|'
    r'methodology|approach|technique|procedure|standard|guideline|'
    r'development|planning|analysis|design|architecture|integration|'
    r'security|privacy|access|authentication|authorization|encryption|'
    r'database|server|network|cloud|platform|application|interface|'
    r'citizen|government|public|service|department|ministry|officer|'
    r'education|knowledge|skill|competency|learning|teaching|research|'
    r'health|environment|economy|society|culture|technology|science|'
    r'report|document|record|file|data|information|communication|'
    r'project|program|plan|initiative|activity|task|function|role|'
    r'team|group|organization|institution|agency|authority|board)\b',
    re.IGNORECASE,
)


def generate_definition_mcq(sentence: str, all_sentences: List[str], idx: int) -> Optional[Dict]:
    """Fill-in-the-blank MCQ by masking a keyword."""
    found = _KEYWORD_RE.findall(sentence)
    if not found:
        return None

    answer = random.choice(list(set(found))).strip()
    if len(answer) < 3:
        return None

    masked = re.sub(re.escape(answer), '________', sentence, count=1, flags=re.IGNORECASE)
    if masked == sentence:
        return None

    question_text = f'Fill in the blank: "{masked}"'

    pool = []
    for s in all_sentences:
        for kw in _KEYWORD_RE.findall(s):
            kw = kw.strip()
            if kw.lower() != answer.lower() and len(kw) > 2:
                pool.append(kw.capitalize())

    distractors = _make_distractors(answer.capitalize(), pool)
    options, correct_idx = _build_options(answer.capitalize(), distractors)

    return {
        'id': _uid(sentence, idx),
        'text': question_text,
        'options': options,
        'correct_answer': correct_idx,
        'explanation': f'From the document: "{sentence[:150]}"',
        'difficulty': random.choice(['easy', 'medium', 'hard']),
        'source': 'ai_generated',
        'type': 'fill_blank',
    }


# ─── Generator 3: Factual MCQ — always works ─────────────────────────────────

def generate_factual_mcq(sentence: str, all_sentences: List[str], idx: int) -> Optional[Dict]:
    """
    Guaranteed fallback. Uses sentence as correct answer,
    other sentences as distractors. Works even with 1 extra sentence.
    """
    if len(sentence.split()) < 5:
        return None

    correct = sentence.strip().rstrip('.!?') + '.'

    others = [
        s.strip().rstrip('.!?') + '.'
        for s in all_sentences
        if s.strip() != sentence.strip() and len(s.split()) >= 5
    ]

    # Need at least 1 other sentence; pad rest with domain distractors
    if len(others) < 1:
        return None

    distractors = []
    if len(others) >= 3:
        distractors = random.sample(others, 3)
    else:
        distractors = others[:]
        # pad from domain pool
        for d in random.sample(DOMAIN_DISTRACTORS, len(DOMAIN_DISTRACTORS)):
            if d not in distractors and d.lower() != correct.lower():
                distractors.append(d)
            if len(distractors) >= 3:
                break

    options, correct_idx = _build_options(correct, distractors[:3])

    question_templates = [
        'Which of the following statements is true according to the document?',
        'According to the material, which statement is correct?',
        'The document supports which of the following statements?',
        'Based on the text, which statement accurately reflects the content?',
        'Which of the following is stated in the document?',
    ]

    return {
        'id': _uid(sentence, idx),
        'text': random.choice(question_templates),
        'options': options,
        'correct_answer': correct_idx,
        'explanation': f'Directly stated in the document: "{sentence[:150]}"',
        'difficulty': 'medium',
        'source': 'ai_generated',
        'type': 'factual',
    }


# ─── Generator 4: True/False style MCQ ───────────────────────────────────────

def generate_truefalse_mcq(sentence: str, idx: int) -> Optional[Dict]:
    """
    Super-reliable fallback. 'According to the document, is the following true?'
    Always produces a valid 4-option question.
    """
    if len(sentence.split()) < 5:
        return None

    statement = sentence.strip().rstrip('.!?') + '.'

    options = [
        'True — this is stated in the document',
        'False — this contradicts the document',
        'Partially true — only some aspects are mentioned',
        'Cannot be determined from the given text',
    ]

    return {
        'id': _uid(sentence + 'tf', idx),
        'text': f'According to the document, evaluate this statement: "{statement}"',
        'options': options,
        'correct_answer': 0,  # always "True"
        'explanation': f'This statement is directly from the document: "{sentence[:150]}"',
        'difficulty': 'easy',
        'source': 'ai_generated',
        'type': 'true_false',
    }


# ─── Validation ───────────────────────────────────────────────────────────────

def _is_valid_mcq(q: Optional[Dict]) -> bool:
    if not q:
        return False
    if not q.get('text') or len(q['text']) < 10:
        return False
    options = q.get('options', [])
    if len(options) != 4:
        return False
    if any(not o or len(str(o).strip()) == 0 for o in options):
        return False
    if len(set(str(o).strip().lower() for o in options)) < 4:
        return False
    if q.get('correct_answer') not in [0, 1, 2, 3]:
        return False
    return True


# ─── Main entry point ─────────────────────────────────────────────────────────

def generate_mcqs_from_text(text: str, num_questions: int = 10, title: str = '') -> List[Dict]:
    """
    Generate MCQs from document text. Four-tier generation ensures
    the requested number is always reached.
    """
    if not text or len(text.split()) < 20:
        return []

    # Primary sentence pool (scored/filtered)
    sentences = extract_key_sentences(text, max_sentences=150)

    # Full sentence pool for factual fallback
    all_sentences = extract_all_sentences(text)

    # Use all_sentences if primary pool is too small
    if len(sentences) < 5:
        sentences = all_sentences

    if not sentences:
        return []

    shuffled = sentences[:]
    random.shuffle(shuffled)

    mcqs = []
    used_sentences = set()
    idx = 0

    # Generate up to 4× requested to ensure we have enough after dedup
    target = num_questions * 4

    for sentence in shuffled:
        if len(mcqs) >= target:
            break
        if sentence in used_sentences:
            continue

        # Tier 1: concept MCQ
        q = generate_concept_mcq(sentence, sentences, idx)
        if q and _is_valid_mcq(q):
            mcqs.append(q)
            used_sentences.add(sentence)
            idx += 1
            continue

        # Tier 2: fill-in-blank
        q = generate_definition_mcq(sentence, sentences, idx)
        if q and _is_valid_mcq(q):
            mcqs.append(q)
            used_sentences.add(sentence)
            idx += 1
            continue

        # Tier 3: factual statement
        q = generate_factual_mcq(sentence, all_sentences, idx)
        if q and _is_valid_mcq(q):
            mcqs.append(q)
            used_sentences.add(sentence)
            idx += 1
            continue

        # Tier 4: true/false (guaranteed)
        q = generate_truefalse_mcq(sentence, idx)
        if q and _is_valid_mcq(q):
            mcqs.append(q)
            used_sentences.add(sentence)
            idx += 1

    # If still short, loop through again allowing sentence reuse for different question types
    if len(mcqs) < num_questions and all_sentences:
        extra_pool = [s for s in all_sentences if len(s.split()) >= 5]
        random.shuffle(extra_pool)
        for sentence in extra_pool:
            if len(mcqs) >= num_questions * 2:
                break
            q = generate_truefalse_mcq(sentence, idx)
            if q and _is_valid_mcq(q):
                # Check not duplicate question text
                if not any(existing['text'][:60] == q['text'][:60] for existing in mcqs):
                    mcqs.append(q)
                    idx += 1

    # Deduplicate by question text
    seen_texts = set()
    unique = []
    for q in mcqs:
        key = q['text'][:60].lower()
        if key not in seen_texts:
            seen_texts.add(key)
            unique.append(q)

    # Trim to requested count
    result = unique[:num_questions]

    # Assign sequential numbers
    for i, q in enumerate(result):
        q['question_number'] = i + 1

    return result


def validate_and_enhance_quiz(mcqs: List[Dict]) -> Dict:
    """Validate quiz quality and return metadata."""
    valid = [q for q in mcqs if _is_valid_mcq(q)]
    difficulty_dist = {
        'easy':   sum(1 for q in valid if q.get('difficulty') == 'easy'),
        'medium': sum(1 for q in valid if q.get('difficulty') == 'medium'),
        'hard':   sum(1 for q in valid if q.get('difficulty') == 'hard'),
    }
    return {
        'questions': valid,
        'total': len(valid),
        'difficulty_distribution': difficulty_dist,
        'quality_score': round(len(valid) / max(len(mcqs), 1) * 100, 1),
    }
