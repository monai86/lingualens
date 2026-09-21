"""Unit tests for ThaiClinicalLSA engine."""

from __future__ import annotations

import pytest

from src.clinical_speech.thai_lsa import ThaiClinicalLSA, tokenize_thai_words


def test_tokenize_thai_words():
    words = tokenize_thai_words("น้องพีร์ เล่น รถ สี แดง สนุก ครับ")
    assert len(words) >= 4
    assert any("รถ" in w for w in words)
    assert any("แดง" in w for w in words)


def test_thai_lsa_analysis_rich_dialogue():
    utterances = [
        {"id": "u-1", "speaker": "INV", "text": "น้องพีร์อยากเล่นอะไรครับ", "start_time": 1.0, "end_time": 3.0},
        {"id": "u-2", "speaker": "CHI", "text": "หนู อยาก เล่น รถ แดง ครับ", "start_time": 3.5, "end_time": 5.5},
        {"id": "u-3", "speaker": "INV", "text": "รถสีแดงวิ่งเร็วไหม", "start_time": 6.0, "end_time": 8.0},
        {"id": "u-4", "speaker": "CHI", "text": "ไม่ เร็ว ครับ ทำไม ช้า", "start_time": 8.5, "end_time": 11.0},
    ]

    metrics = ThaiClinicalLSA.analyze_utterances(utterances)

    assert metrics.total_child_utterances == 2
    assert metrics.total_child_words > 4
    assert metrics.mlu_words >= 2.0
    assert metrics.ttr > 0.5
    assert metrics.multi_word_ratio_pct == 100.0

    # Questions & Negations detected
    assert metrics.question_count >= 1  # "ทำไม"
    assert metrics.negation_count >= 1  # "ไม่"
    assert metrics.pronoun_count >= 1   # "หนู"
    assert metrics.polite_particle_count >= 1 # "ครับ"
    assert metrics.turn_taking_count == 2
    assert len(metrics.guideline_links) == 5


def test_thai_lsa_empty_utterances():
    metrics = ThaiClinicalLSA.analyze_utterances([])
    assert metrics.total_child_utterances == 0
    assert metrics.total_child_words == 0
    assert metrics.mlu_words == 0.0
    assert len(metrics.guideline_links) == 1


def test_thai_lsa_pragmatic_markers_and_fillers():
    utterances = [
        {"id": "u-1", "speaker": "INV", "text": "น้องชอบเล่นอะไรอีกไหมครับ", "start_time": 1.0, "end_time": 3.0},
        {"id": "u-2", "speaker": "CHI", "text": "เอ่อ หนู ชอบ บล็อกไม้ นะ ครับ เพราะ สนุก ดี", "start_time": 3.5, "end_time": 7.0},
        {"id": "u-3", "speaker": "INV", "text": "สร้างเป็นบ้านได้ไหม", "start_time": 7.5, "end_time": 9.0},
        {"id": "u-4", "speaker": "CHI", "text": "ได้ สิ และ มี หลังคา ด้วย", "start_time": 9.5, "end_time": 12.0},
    ]

    metrics = ThaiClinicalLSA.analyze_utterances(utterances)
    assert metrics.filler_word_count >= 1  # "เอ่อ"
    assert metrics.filler_ratio > 0.0
    assert metrics.mood_particle_count >= 2  # "นะ", "สิ", "ด้วย"
    assert metrics.conjunction_count >= 2   # "เพราะ", "และ"
    assert metrics.polite_particle_count >= 1  # "ครับ"


def test_detect_echolalia_verbatim_and_mitigated():
    from src.clinical_speech.thai_lsa import detect_echolalia

    # Verbatim repetition
    cat, sim = detect_echolalia("น้องอยากกินอะไร", "น้องอยากกินอะไร")
    assert cat == "immediate_verbatim"
    assert sim >= 0.8

    # Mitigated repetition with added particle
    cat2, sim2 = detect_echolalia("รถไฟสีแดง", "รถไฟสีแดงครับ")
    assert cat2 in ("immediate_verbatim", "mitigated")

    # Regular conversational response (not echolalia)
    cat3, sim3 = detect_echolalia("ชอบกินไอศกรีมไหม", "ชอบ")
    assert cat3 is None
    assert sim3 == 0.0

    cat4, sim4 = detect_echolalia("เอาของเล่นไหมครับ", "ไม่เอา")
    assert cat4 is None


def test_detect_thai_pronoun_reversal():
    from src.clinical_speech.thai_lsa import detect_thai_pronoun_reversal, tokenize_thai_words

    text1 = "เธอ อยาก กิน ขนม"
    toks1 = tokenize_thai_words(text1)
    reversals1 = detect_thai_pronoun_reversal(text1, toks1)
    assert len(reversals1) >= 1
    assert any("เธอ" in r for r in reversals1)

    text2 = "คุณ จะ ไป ไหน"
    toks2 = tokenize_thai_words(text2)
    reversals2 = detect_thai_pronoun_reversal(text2, toks2)
    assert len(reversals2) >= 1

    # Normal self-reference (not reversed)
    text3 = "หนู อยาก กิน ขนม ครับ"
    toks3 = tokenize_thai_words(text3)
    reversals3 = detect_thai_pronoun_reversal(text3, toks3)
    assert len(reversals3) == 0


def test_thai_lsa_echolalia_and_pronoun_reversal_integration():
    utterances = [
        {"id": "u-1", "speaker": "INV", "text": "น้องอยากเล่นอะไรครับ", "start_time": 1.0, "end_time": 3.0},
        {"id": "u-2", "speaker": "CHI", "text": "น้องอยากเล่นอะไรครับ", "start_time": 3.2, "end_time": 5.0}, # Verbatim echolalia
        {"id": "u-3", "speaker": "INV", "text": "ดูรถไฟสิ", "start_time": 6.0, "end_time": 7.5},
        {"id": "u-4", "speaker": "CHI", "text": "เธอ อยาก เล่น รถไฟ", "start_time": 8.0, "end_time": 10.0}, # Pronoun reversal ("เธออยาก")
    ]

    metrics = ThaiClinicalLSA.analyze_utterances(utterances)
    assert metrics.echolalia_count >= 1
    assert metrics.echolalia_verbatim_count >= 1
    assert len(metrics.echolalia_details) >= 1
    assert metrics.pronoun_reversal_count >= 1
    assert len(metrics.pronoun_reversal_details) >= 1
    assert any(g["construct"].startswith("5. Repetition") for g in metrics.guideline_links)


