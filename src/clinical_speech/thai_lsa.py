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

THAI_FILLER_WORDS = {
    "เอ่อ", "อ่า", "แบบ", "คือ", "งะ", "นะฮะ", "เอิ่ม", "เออ",
}

THAI_MOOD_PARTICLES = {
    "นะ", "สิ", "เลย", "หรอก", "ด้วย", "ล่ะ", "เนอะ", "น้า", "ซิ", "อ่ะ",
}

THAI_CONJUNCTIONS = {
    "และ", "หรือ", "แต่", "เพราะ", "ถ้า", "ก็", "แล้ว", "กับ", "จึง",
}

THAI_CONVERSATIONAL_RESPONSES = {
    "ใช่", "ไม่ใช่", "เอา", "ไม่เอา", "ชอบ", "ไม่ชอบ", "ได้", "ไม่ได้",
    "มี", "ไม่มี", "ไป", "ไม่ไป", "ยัง", "หรือยัง", "ครับ", "ค่ะ", "ฮะ",
    "ดี", "ไม่ดี", "อยาก", "ไม่อยาก", "ถูก", "ไม่ถูก",
}

THAI_SECOND_PERSON_PRONOUNS = {"เธอ", "คุณ", "แก", "เอ็ง"}

THAI_DESIRE_AND_STATE_VERBS = {
    "อยาก", "จะ", "เอา", "ชอบ", "หิว", "กลัว", "ปวด", "ไม่เอา", "ไม่อยาก",
    "ไม่ชอบ", "ขอ", "ขอดู", "กิน", "เล่น", "นอน", "กลับ", "ร้อง", "ไป",
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
    filler_word_count: int = 0
    filler_ratio: float = 0.0
    mood_particle_count: int = 0
    conjunction_count: int = 0
    turn_taking_latency_sec: float | None = None
    echolalia_verbatim_count: int = 0
    echolalia_mitigated_count: int = 0
    echolalia_details: list[dict[str, Any]] = field(default_factory=list)
    pronoun_reversal_details: list[dict[str, Any]] = field(default_factory=list)
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


def detect_echolalia(
    adult_text: str,
    child_text: str,
    latency: float | None = None,
) -> tuple[str | None, float]:
    """Detect immediate verbatim or mitigated echolalia from child reply to adult turn.

    Returns:
        (category, similarity_score) where category is 'immediate_verbatim', 'mitigated', or None.
    """
    a_clean = re.sub(r"[^\wก-๙]+", "", str(adult_text or ""))
    c_clean = re.sub(r"[^\wก-๙]+", "", str(child_text or ""))
    if not a_clean or not c_clean:
        return None, 0.0

    # Exclude standard short conversational affirmations/negations
    if c_clean in THAI_CONVERSATIONAL_RESPONSES or c_clean in THAI_POLITE_PARTICLES:
        return None, 0.0

    # 1. Exact verbatim match (at least 3 characters)
    if c_clean == a_clean and len(c_clean) >= 3:
        return "immediate_verbatim", 1.0

    # 2. Verbatim with added or omitted polite particle
    for particle in THAI_POLITE_PARTICLES:
        if c_clean.endswith(particle) and c_clean[:-len(particle)] == a_clean and len(a_clean) >= 3:
            return "immediate_verbatim", 0.95
        if a_clean.endswith(particle) and a_clean[:-len(particle)] == c_clean and len(c_clean) >= 3:
            return "immediate_verbatim", 0.95

    # 3. Substring repetition (child repeats significant part of adult prompt)
    if len(c_clean) >= 6 and (c_clean in a_clean or a_clean in c_clean):
        ratio = min(len(c_clean), len(a_clean)) / max(len(c_clean), len(a_clean))
        if ratio >= 0.75:
            return "immediate_verbatim", round(ratio, 2)
        elif ratio >= 0.45:
            return "mitigated", round(ratio, 2)

    # 4. Token overlap if tokens are available
    c_words = tokenize_thai_words(child_text)
    a_words = tokenize_thai_words(adult_text)
    if c_words and a_words:
        c_set = set(c_words)
        a_set = set(a_words)
        intersection = c_set.intersection(a_set)
        if intersection:
            overlap = len(intersection) / max(len(c_set), 1)
            if overlap >= 0.8 and len(intersection) >= 2:
                return "immediate_verbatim", round(overlap, 2)
            elif overlap >= 0.45 and len(intersection) >= 2:
                return "mitigated", round(overlap, 2)

    return None, 0.0


def detect_thai_pronoun_reversal(text: str, tokens: list[str]) -> list[str]:
    """Detect deictic pronoun reversal instances in Thai child speech.

    Looks for 2nd/3rd person pronouns used in self-referencing contexts (e.g. desire/state verbs).
    """
    flagged: list[str] = []
    # Pattern 1: Token sequences like ["เธอ", "อยาก"], ["คุณ", "จะ"], ["เธอ", "เอา"]
    for i in range(len(tokens) - 1):
        p = tokens[i]
        v = tokens[i + 1]
        if p in THAI_SECOND_PERSON_PRONOUNS and v in THAI_DESIRE_AND_STATE_VERBS:
            flagged.append(f"{p}{v}")

    # Pattern 2: Regex search for fused combinations
    raw = re.sub(r"\s+", "", str(text or ""))
    for p in THAI_SECOND_PERSON_PRONOUNS:
        for v in ["อยาก", "จะเอา", "จะเล่น", "หิวน้ำ", "ปวดฉี่", "ขอดู", "ไม่เอา", "จะไป"]:
            target = f"{p}{v}"
            if target in raw and target not in flagged:
                flagged.append(target)

    return flagged


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
                echolalia_verbatim_count=0,
                echolalia_mitigated_count=0,
                echolalia_details=[],
                pronoun_reversal_count=0,
                pronoun_reversal_details=[],
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

        # Questions, Negations, Pronouns, Particles, Fillers & Conjunctions
        question_count = 0
        negation_count = 0
        pronoun_count = 0
        polite_particle_count = 0
        filler_count = 0
        mood_particle_count = 0
        conjunction_count = 0

        for words in child_tokenized:
            has_q = any(w in THAI_QUESTION_MARKERS for w in words)
            has_neg = any(w in THAI_NEGATION_MARKERS for w in words)
            if has_q:
                question_count += 1
            if has_neg:
                negation_count += 1
            pronoun_count += sum(1 for w in words if w in THAI_PRONOUN_MARKERS)
            polite_particle_count += sum(1 for w in words if w in THAI_POLITE_PARTICLES)
            filler_count += sum(1 for w in words if w in THAI_FILLER_WORDS)
            mood_particle_count += sum(1 for w in words if w in THAI_MOOD_PARTICLES)
            conjunction_count += sum(1 for w in words if w in THAI_CONJUNCTIONS)

        q_ratio = round(question_count / n_child, 2)
        neg_ratio = round(negation_count / n_child, 2)
        filler_ratio = round(filler_count / max(total_words, 1), 2)

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
        echolalia_details: list[dict[str, Any]] = []
        echolalia_verbatim_cnt = 0
        echolalia_mitigated_cnt = 0

        for i in range(1, len(utterances)):
            prev = utterances[i - 1]
            curr = utterances[i]
            if curr.get("speaker") == child_speaker and prev.get("speaker") != child_speaker:
                adult_txt = prev.get("text", "")
                child_txt = curr.get("text", "")
                cat, sim = detect_echolalia(adult_txt, child_txt)
                if cat:
                    if cat == "immediate_verbatim":
                        echolalia_verbatim_cnt += 1
                    elif cat == "mitigated":
                        echolalia_mitigated_cnt += 1
                    echolalia_details.append({
                        "category": cat,
                        "adult_text": adult_txt,
                        "child_text": child_txt,
                        "similarity_score": sim,
                        "child_id": curr.get("id"),
                    })

        echolalia_cnt = echolalia_verbatim_cnt + echolalia_mitigated_cnt

        pronoun_reversal_details: list[dict[str, Any]] = []
        for u, words in zip(child_utts, child_tokenized):
            txt = u.get("text", "")
            matches = detect_thai_pronoun_reversal(txt, words)
            if matches:
                pronoun_reversal_details.append({
                    "utterance_id": u.get("id"),
                    "text": txt,
                    "matched_patterns": matches,
                    "explanation": "พบการใช้สรรพนามบุรุษที่ 2 (เธอ/คุณ) ในบริบทแสดงความต้องการ/สภาวะของตนเอง",
                })
        pronoun_rev = len(pronoun_reversal_details)

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
                "description": f"พบประโยคคำถาม {question_count} ครั้ง, คำปฏิเสธ {negation_count} ครั้ง, คำสรรพนาม {pronoun_count} ครั้ง, คำลงท้าย {polite_particle_count} ครั้ง",
            },
            {
                "construct": "5. Repetition & Atypical Patterns (การพูดซ้ำ/สรรพนามสลับ)",
                "status": "Low / Monitored" if (echolalia_cnt == 0 and pronoun_rev == 0) else "Observed",
                "description": f"พบ Echolalia {echolalia_cnt} ครั้ง (ตรงประโยค {echolalia_verbatim_cnt}, ดัดแปลง {echolalia_mitigated_cnt}), สลับสรรพนาม {pronoun_rev} ครั้ง",
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
            echolalia_verbatim_count=echolalia_verbatim_cnt,
            echolalia_mitigated_count=echolalia_mitigated_cnt,
            echolalia_details=echolalia_details,
            pronoun_reversal_count=pronoun_rev,
            pronoun_reversal_details=pronoun_reversal_details,
            turn_taking_count=turn_taking,
            turn_taking_ratio=turn_taking_ratio,
            filler_word_count=filler_count,
            filler_ratio=filler_ratio,
            mood_particle_count=mood_particle_count,
            conjunction_count=conjunction_count,
            turn_taking_latency_sec=turn_latency,
            guideline_links=guidelines,
        )
