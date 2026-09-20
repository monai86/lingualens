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
