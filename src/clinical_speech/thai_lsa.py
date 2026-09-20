"""Deep Thai Clinical Language Sample Analysis (LSA) Engine.

Extracts developmental, pragmatic, and atypical language markers tailored for
Thai-speaking children in speech-language therapy and developmental assessments.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Sequence


THAI_QUESTION_MARKERS = {
    "อะไร", "ทำไม", "ไหน", "ที่ไหน", "ใคร", "หรือยัง", "ไหม", "มั้ย",
    "กี่", "กี่อัน", "กี่ชิ้น", "กี่ตัว", "หรือเปล่า", "ใช่มั้ย", "ใช่ไหม",
    "หรือ", "หรอ", "เหรอ",
}

THAI_NEGATION_MARKERS = {
    "ไม่", "อย่า", "มิ", "ไม่เอา", "ไม่ได้", "ไม่ใช่", "ไม่ชอบ", "ไม่มี",
}

THAI_PRONOUN_MARKERS = {
    "หนู", "ผม", "เรา", "เธอ", "เขา", "มัน", "คุณ", "คุณแม่", "แม่",
    "คุณพ่อ", "พ่อ", "พี่", "น้อง", "ป้า", "ลุง", "ตา", "ยาย",
}

THAI_POLITE_PARTICLES = {
    "ครับ", "ค่ะ", "ฮะ", "จ้ะ", "จ๊ะ", "คะ",
}


@dataclass(frozen=True)
class ThaiLsaMetrics:
    """Quantitative linguistic metrics for Thai child speech samples."""

    total_child_utterances: int
    total_child_words: int
    unique_words_count: int
    mlu_words: float
    mlu_morphemes: float
    ttr: float
    multi_word_ratio_pct: float
    question_count: int
    question_ratio: float
    negation_count: int
    negation_ratio: float
    pronoun_count: int
    polite_particle_count: int
    echolalia_count: int
    echolalia_ratio: float
    pronoun_reversal_count: int
    turn_taking_count: int
    turn_taking_ratio: float
    turn_taking_latency_sec: float | None = None
    guideline_links: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def tokenize_thai_words(text: str) -> list[str]:
    """Tokenize Thai text into linguistic words using pythainlp or robust regex fallback."""
    raw = str(text or "").strip()
    if not raw:
        return []

    # Clean out CHAT codes and metadata
    raw = re.sub(r"\x15\d+_\d+\x15", " ", raw)
    raw = re.sub(r"\[[^\]]+\]", " ", raw)
    raw = re.sub(r"&\=[A-Za-z0-9ก-๙_-]+", " ", raw)
    raw = re.sub(r"\b(?:xxx|yyy|www)\b", " ", raw)

    try:
        from pythainlp.tokenize import word_tokenize
        tokens = word_tokenize(raw, engine="newmm")
    except Exception:
        # Fallback whitespace & thai word regex splitting
        tokens = re.findall(r"[ก-๙]+|[A-Za-z0-9'-]+", raw)

    cleaned = []
    for tok in tokens:
        c = tok.strip()
        if c and not re.fullmatch(r"[.,!?;:\"'()]+", c):
            cleaned.append(c)
    return cleaned


class ThaiClinicalLSA:
    """Analyzes Thai dialogue transcripts and computes clinical language sample metrics."""

    @classmethod
    def analyze_utterances(
        cls,
        utterances: Sequence[dict[str, Any]],
        child_speaker: str = "CHI",
    ) -> ThaiLsaMetrics:
        """Run comprehensive Thai LSA on a sequence of utterance dictionaries."""
        child_utts: list[dict[str, Any]] = []
        adult_utts: list[dict[str, Any]] = []

        for u in utterances:
            if u.get("speaker") == child_speaker:
                child_utts.append(u)
            else:
                adult_utts.append(u)

        n_child = len(child_utts)
        n_adult = len(adult_utts)

        if n_child == 0:
            return ThaiLsaMetrics(
                total_child_utterances=0,
                total_child_words=0,
                unique_words_count=0,
                mlu_words=0.0,
                mlu_morphemes=0.0,
                ttr=0.0,
                multi_word_ratio_pct=0.0,
                question_count=0,
                question_ratio=0.0,
                negation_count=0,
                negation_ratio=0.0,
                pronoun_count=0,
                polite_particle_count=0,
                echolalia_count=0,
                echolalia_ratio=0.0,
                pronoun_reversal_count=0,
                turn_taking_count=0,
                turn_taking_ratio=0.0,
                guideline_links=[
                    {
                        "construct": "1. Expressive Phrase Length (ไวยากรณ์และความยาวประโยค)",
                        "status": "No Child Utterances",
                        "description": "ยังไม่พบประโยคพูดของเด็กในตัวอย่างบทสนทนานี้",
                    }
                ],
            )

        # Word Tokenization
        child_tokenized: list[list[str]] = []
        all_words: list[str] = []
        multi_word_count = 0

        for u in child_utts:
            txt = u.get("text", "")
            words = tokenize_thai_words(txt)
            child_tokenized.append(words)
            all_words.extend(words)
            if len(words) >= 2:
                multi_word_count += 1

        total_words = len(all_words)
        unique_words = len(set(all_words))
        mlu_w = round(total_words / n_child, 2)
        # Thai morpheme estimation: root words + compounding particles (~1.18 factor)
        mlu_m = round(mlu_w * 1.18, 2)
        ttr = round(unique_words / max(total_words, 1), 2)
        multi_word_pct = round((multi_word_count / n_child) * 100, 1)

        # Questions & Negations
        question_count = 0
        negation_count = 0
        pronoun_count = 0
        polite_particle_count = 0

        for words in child_tokenized:
            has_q = any(w in THAI_QUESTION_MARKERS for w in words)
            has_neg = any(w in THAI_NEGATION_MARKERS for w in words)
            if has_q:
                question_count += 1
            if has_neg:
                negation_count += 1
            pronoun_count += sum(1 for w in words if w in THAI_PRONOUN_MARKERS)
            polite_particle_count += sum(1 for w in words if w in THAI_POLITE_PARTICLES)

        q_ratio = round(question_count / n_child, 2)
        neg_ratio = round(negation_count / n_child, 2)

        # Turn-Taking Dynamics
        turn_taking = min(n_adult, n_child)
        turn_taking_ratio = round(turn_taking / max(n_adult, 1), 2)

        latencies = []
        for prev_u, curr_u in zip(utterances, utterances[1:]):
            if prev_u.get("speaker") != child_speaker and curr_u.get("speaker") == child_speaker:
                p_end = prev_u.get("end_time")
                c_start = curr_u.get("start_time")
                if p_end is not None and c_start is not None and c_start >= p_end:
                    latencies.append(c_start - p_end)
        turn_latency = round(sum(latencies) / len(latencies), 2) if latencies else None

        # Echolalia & Repetition Markers
        echolalia_cnt = 0
        for i in range(1, len(utterances)):
            prev = utterances[i - 1]
            curr = utterances[i]
            if curr.get("speaker") == child_speaker and prev.get("speaker") != child_speaker:
                prev_words = set(tokenize_thai_words(prev.get("text", "")))
                curr_words = set(tokenize_thai_words(curr.get("text", "")))
                if prev_words and curr_words and len(prev_words.intersection(curr_words)) >= min(2, len(curr_words)):
                    echolalia_cnt += 1

        pronoun_rev = sum(
            1 for words in child_tokenized
            if any(p in words for p in ["เธออยาก", "คุณไป", "เธอเอา"])
        )

        # Formulate Clinical Guideline Interpretation Links
        guidelines = [
            {
                "construct": "1. Expressive Phrase Length (ไวยากรณ์และความยาวประโยค)",
                "status": "Multi-word Sentences (3+ words)" if mlu_w >= 3.0 else (
                    "Emerging Multi-word (2-3 words)" if mlu_w >= 2.0 else "Single Words"
                ),
                "description": f"MLU-w อยู่ที่ {mlu_w} คำ/ประโยค (ประโยค 2 คำขึ้นไป {multi_word_pct}%)",
            },
            {
                "construct": "2. Lexical & Vocabulary Diversity (ความหลากหลายของคำศัพท์)",
                "status": "Age Expected (สมวัย)" if ttr >= 0.65 else "Developing Diversity",
                "description": f"TTR {ttr} (คำศัพท์ไม่ซ้ำ {unique_words} คำ จากทั้งหมด {total_words} คำ)",
            },
            {
                "construct": "3. Pragmatic Turn-Taking (การผลัดกันพูดในบทสนทนา)",
                "status": "Responsive (ตอบสนองดี)" if turn_taking_ratio >= 0.7 else "Developing",
                "description": f"Turn-taking ratio {turn_taking_ratio} (โต้ตอบ {turn_taking} ครั้ง, คำถาม {question_count} ครั้ง)",
            },
            {
                "construct": "4. Functional Syntax (คำถาม/คำปฏิเสธ/สรรพนาม)",
                "status": "Present (พบการใช้งาน)" if (question_count > 0 or negation_count > 0) else "Emerging",
                "description": f"พบประโยคคำถาม {question_count} ครั้ง, คำปฏิเสธ {negation_count} ครั้ง, คำสรรพนาม {pronoun_count} ครั้ง",
            },
            {
                "construct": "5. Repetition & Atypical Patterns (การพูดซ้ำ/สรรพนามสลับ)",
                "status": "Low / Monitored" if (echolalia_cnt == 0 and pronoun_rev == 0) else "Observed",
                "description": f"พบ Echolalia {echolalia_cnt} ครั้ง, สลับสรรพนาม {pronoun_rev} ครั้ง",
            },
        ]

        return ThaiLsaMetrics(
            total_child_utterances=n_child,
            total_child_words=total_words,
            unique_words_count=unique_words,
            mlu_words=mlu_w,
            mlu_morphemes=mlu_m,
            ttr=ttr,
            multi_word_ratio_pct=multi_word_pct,
            question_count=question_count,
            question_ratio=q_ratio,
            negation_count=negation_count,
            negation_ratio=neg_ratio,
            pronoun_count=pronoun_count,
            polite_particle_count=polite_particle_count,
            echolalia_count=echolalia_cnt,
            echolalia_ratio=round(echolalia_cnt / n_child, 2),
            pronoun_reversal_count=pronoun_rev,
            turn_taking_count=turn_taking,
            turn_taking_ratio=turn_taking_ratio,
            turn_taking_latency_sec=turn_latency,
            guideline_links=guidelines,
        )
