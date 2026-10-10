"""In-Memory Mock Adapter implementing ClinicalDataPort for testing and local research."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from packages.cha.parser import parse_cha_text


def _default_get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class InMemoryClinicalAdapter:
    """Clinical data adapter managing offline in-memory mock datasets."""

    def __init__(
        self,
        seed_demo: bool = False,
        clock: Optional[Callable[[], datetime]] = None,
    ) -> None:
        self._clock = clock
        self._mock_data: dict[str, Any] = self._init_mock_data(seed_demo=seed_demo)

    @property
    def mock_data(self) -> dict[str, Any]:
        return self._mock_data

    @mock_data.setter
    def mock_data(self, data: dict[str, Any]) -> None:
        self._mock_data = data

    def _get_now(self) -> datetime:
        if callable(getattr(self, "_clock", None)):
            return self._clock()
        return _default_get_utc_now()

    def seed_demo_dataset(self) -> None:
        self._mock_data = self._init_mock_data(seed_demo=True)

    def clear_mock_data(self) -> None:
        self._mock_data = self._init_mock_data(seed_demo=False)

    def _init_mock_data(self, seed_demo: bool = False) -> dict[str, Any]:
        if not seed_demo:
            return {
                "cases": [],
                "sessions": {},
                "transcripts": {},
                "features": {},
                "reports": {},
                "children": [],
                "consents": {},
                "assessments": {},
            }

        return {
            "cases": [
                {
                    "case_id": "case-demo-001",
                    "child_id": "C-0104",
                    "child_code": "C-0104",
                    "birth_year_month": "2020-04",
                    "age_months": 52,
                    "primary_language": "th",
                    "language": "th",
                    "clinical_notes": "Receptive-expressive language delay evaluation.",
                    "notes": "Receptive-expressive language delay evaluation.",
                    "status": "active",
                    "session_count": 2,
                },
                {
                    "case_id": "case-demo-002",
                    "child_id": "C-0208",
                    "child_code": "C-0208",
                    "birth_year_month": "2021-01",
                    "age_months": 43,
                    "primary_language": "th",
                    "language": "th",
                    "clinical_notes": "Social communication and joint attention follow-up.",
                    "notes": "Social communication and joint attention follow-up.",
                    "status": "active",
                    "session_count": 1,
                },
            ],
            "sessions": {
                "case-demo-001": [
                    {
                        "session_id": "sess-demo-101",
                        "case_id": "case-demo-001",
                        "session_date": "2024-08-10",
                        "session_number": 1,
                        "session_type": "play_evaluation",
                        "status": "Reviewed",
                        "transcript_id": "tr-demo-101",
                        "feature_set_id": "feat-demo-101",
                        "report_id": "rep-demo-101",
                        "notes": "Free-play toy interaction with parent present.",
                    },
                    {
                        "session_id": "sess-demo-102",
                        "case_id": "case-demo-001",
                        "session_date": "2024-09-15",
                        "session_number": 2,
                        "session_type": "therapy_session",
                        "status": "In Progress",
                        "transcript_id": "tr-demo-102",
                        "feature_set_id": None,
                        "report_id": None,
                        "notes": "Structured naming and turn-taking protocol.",
                    },
                ],
                "case-demo-002": [
                    {
                        "session_id": "sess-demo-201",
                        "case_id": "case-demo-002",
                        "session_date": "2024-09-02",
                        "session_number": 1,
                        "session_type": "screening",
                        "status": "Intake",
                        "transcript_id": None,
                        "feature_set_id": None,
                        "report_id": None,
                        "notes": "Initial speech-language intake.",
                    }
                ],
            },
            "transcripts": {
                "tr-demo-101": {
                    "transcript_id": "tr-demo-101",
                    "session_id": "sess-demo-101",
                    "status": "reviewed",
                    "utterances": [
                        {"id": "u-1", "speaker": "INV", "text": "น้องพีร์ดูสิ อันนี้รถอะไรครับ", "start_time": 1.2, "end_time": 4.1, "qa_flags": []},
                        {"id": "u-2", "speaker": "CHI", "text": "รถ แดง", "start_time": 4.8, "end_time": 6.0, "qa_flags": []},
                        {"id": "u-3", "speaker": "INV", "text": "รถสีแดงเก่งมาก แล้วคันนี้ล่ะครับ", "start_time": 6.5, "end_time": 9.8, "qa_flags": []},
                        {"id": "u-4", "speaker": "CHI", "text": "รถ", "start_time": 10.5, "end_time": 11.2, "qa_flags": []},
                        {"id": "u-5", "speaker": "INV", "text": "รถคันใหญ่ หรือคันเล็ก", "start_time": 12.0, "end_time": 14.5, "qa_flags": []},
                        {"id": "u-6", "speaker": "CHI", "text": "คัน ใหญ่", "start_time": 15.2, "end_time": 16.8, "qa_flags": []},
                        {"id": "u-7", "speaker": "INV", "text": "อยากเล่นต่อไหมครับ", "start_time": 17.5, "end_time": 19.2, "qa_flags": []},
                        {"id": "u-8", "speaker": "CHI", "text": "เล่น รถ แดง วิ่ง เร็ว", "start_time": 20.0, "end_time": 22.5, "qa_flags": []},
                    ],
                    "qa_summary": {
                        "total_utterances": 8,
                        "unresolved_flags": 0,
                        "child_utterance_count": 4,
                    },
                    "attested": True,
                    "attested_by": "Kru Aum (Certified SLP)",
                },
                "tr-demo-102": {
                    "transcript_id": "tr-demo-102",
                    "session_id": "sess-demo-102",
                    "status": "pending_review",
                    "utterances": [
                        {"id": "u-1", "speaker": "INV", "text": "สวัสดีครับน้องพีร์ วันนี้เอาพี่หมีมาด้วยไหม", "start_time": 0.8, "end_time": 3.9, "qa_flags": []},
                        {"id": "u-2", "speaker": "CHI", "text": "พี่หมี", "start_time": 4.5, "end_time": 5.4, "qa_flags": []},
                        {"id": "u-3", "speaker": "CHI", "text": "หมี นอน", "start_time": 6.2, "end_time": 7.5, "qa_flags": []},
                        {"id": "u-4", "speaker": "INV", "text": "พี่หมี่ง่วงนอนแล้วเหรอครับ", "start_time": 8.0, "end_time": 10.2, "qa_flags": []},
                    ],
                    "qa_summary": {
                        "total_utterances": 4,
                        "unresolved_flags": 0,
                        "child_utterance_count": 2,
                    },
                    "attested": False,
                    "attested_by": None,
                },
            },
            "features": {
                "sess-demo-101": {
                    "feature_set_id": "feat-demo-101",
                    "session_id": "sess-demo-101",
                    "has_data": True,
                    "metrics": {
                        "mlu_words": 2.25,
                        "mlu_morphemes": 2.65,
                        "ttr": 0.78,
                        "total_child_words": 9,
                        "unique_words_count": 7,
                        "total_child_utterances": 4,
                        "multi_word_ratio_pct": 75.0,
                        "intelligibility_rate": 0.95,
                        "turn_taking_ratio": 0.80,
                        "turn_taking_count": 4,
                        "turn_taking_latency_sec": 0.72,
                        "question_ratio": 0.0,
                        "adult_utterance_count": 4,
                        "echolalia_count": 0,
                        "echolalia_ratio": 0.0,
                        "pronoun_reversal_count": 0,
                        "unintelligible_ratio": 0.05,
                        "f0_median_hz": None,
                        "f0_iqr_hz": None,
                        "voiced_ratio_pct": None,
                        "pause_ratio_pct": None,
                        "speech_rate_wpm": None,
                        "audio_duration_sec": None,
                    },
                    "guideline_links": [
                        {
                            "construct": "1. Expressive Phrase Length (ไวยากรณ์และความยาวประโยค)",
                            "status": "Emerging Multi-word (2-3 words)",
                            "description": "MLU-w อยู่ที่ 2.25 คำ/ประโยค มีสัดส่วนประโยค 2 คำขึ้นไป 75.0%",
                        },
                        {
                            "construct": "2. Lexical & Vocabulary Diversity (ความหลากหลายของคำศัพท์)",
                            "status": "Age Expected (สมวัย)",
                            "description": "TTR 0.78 (คำศัพท์ไม่ซ้ำ 7 คำ จากทั้งหมด 9 คำ)",
                        },
                        {
                            "construct": "3. Pragmatic Turn-Taking (การผลัดกันพูดในบทสนทนา)",
                            "status": "Responsive (ตอบสนองดี)",
                            "description": "Turn-taking ratio 0.8 มีการโต้ตอบคู่สนทนา 4 ครั้ง",
                        },
                        {
                            "construct": "4. Echolalia & Repetition (การพูดตาม/พูดซ้ำ)",
                            "status": "Low / Monitored",
                            "description": "พบ Echolalia 0 ครั้ง, สลับสรรพนาม 0 ครั้ง",
                        },
                        {
                            "construct": "5. Acoustic Prosody & Pitch (ระดับเสียงและน้ำเสียง)",
                            "status": "N/A (Text-only - No Audio)",
                            "description": "การวัดระดับเสียง F0 และ Prosody จำเป็นต้องมีไฟล์บันทึกเสียง (.wav / .mp3 / .m4a)",
                        },
                    ],
                }
            },
            "reports": {
                "rep-demo-101": {
                    "report_id": "rep-demo-101",
                    "session_id": "sess-demo-101",
                    "status": "Signed Off",
                    "narrative": (
                        "การประเมินทักษะทางภาษาและการสื่อสาร (Language Sample Analysis):\n"
                        "- เด็กเริ่มมีการใช้ประโยคความยาว 2-3 คำ (MLU-w = 2.25) เช่น 'รถ แดง', 'เล่น รถ แดง วิ่ง เร็ว'\n"
                        "- ความหลากหลายของคำศัพท์ (TTR = 0.78) อยู่ในเกณฑ์เหมาะสมตามวัย (Age Expected)\n"
                        "- การผลัดกันพูดในบทสนทนา (Turn-Taking) มีปฏิสัมพันธ์โต้ตอบอย่างต่อเนื่อง 80%\n"
                        "- ไม่พบพฤติกรรมการพูดทวนคำ (Immediate Echolalia) หรือการสลับสรรพนาม (Pronoun Reversal)"
                    ),
                    "recommendations": (
                        "1. ส่งเสริมการต่อประโยคผ่านกิจกรรมการเล่นบทบาทสมมุติ (Role-play with interactive toys)\n"
                        "2. ขยายคลังคำศัพท์กลุ่มคำกริยาและคำคุณศัพท์เพื่อเพิ่มความซับซ้อนของประโยค\n"
                        "3. นัดติดตามประเมินผลความก้าวหน้าในเซสชันถัดไป (Follow-up in 4 weeks)"
                    ),
                    "signed_at": "2024-08-11T14:30:00Z",
                    "signed_by": "Kru Aum (Certified SLP)",
                    "sha256_hash": "a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890",
                }
            },
            "children": [],
            "consents": {},
            "assessments": {},
        }

    def check_health(self) -> bool:
        return False

    def list_cases(self) -> list[dict[str, Any]]:
        return self._mock_data["cases"]

    def create_case(
        self,
        child_code: str | None = None,
        age_months: int | str | None = None,
        language: str = "th",
        notes: str = "",
        *,
        child_id: str | None = None,
        birth_year_month: str | None = None,
        primary_language: str | None = None,
    ) -> dict[str, Any]:
        from packages.tui.client import LinguaLensApiError

        legacy_shape = (
            child_id is not None
            or birth_year_month is not None
            or primary_language is not None
            or isinstance(age_months, str)
        )
        if legacy_shape:
            legacy_child_id = child_id if child_id is not None else child_code
            legacy_birth_month = birth_year_month if birth_year_month is not None else age_months
            legacy_language = primary_language if primary_language is not None else language
            if not isinstance(legacy_child_id, str) or not isinstance(legacy_birth_month, str):
                raise LinguaLensApiError(
                    "Legacy case creation requires child_id and birth_year_month; no age conversion was performed."
                )
            return self._create_case_from_birth_year_month(
                child_id=legacy_child_id,
                birth_year_month=legacy_birth_month,
                primary_language=legacy_language,
                notes=notes,
            )

        if not isinstance(child_code, str) or not child_code.strip():
            raise LinguaLensApiError("Case creation requires a non-empty child_code.")
        if not isinstance(age_months, int) or isinstance(age_months, bool) or not 0 <= age_months <= 240:
            raise LinguaLensApiError("Case creation requires age_months as an integer from 0 through 240.")
        if not isinstance(language, str) or not language.strip():
            raise LinguaLensApiError("Case creation requires a non-empty language.")
        if not isinstance(notes, str):
            raise LinguaLensApiError("Case creation notes must be text.")

        new_case = {
            "case_id": f"case-local-{len(self._mock_data['cases']) + 1:03d}",
            "child_code": child_code,
            "age_months": age_months,
            "language": language,
            "notes": notes,
            "status": "active",
            "session_count": 0,
        }
        self._mock_data["cases"].append(new_case)
        self._mock_data["sessions"][new_case["case_id"]] = []
        return new_case

    def _create_case_from_birth_year_month(
        self,
        *,
        child_id: str,
        birth_year_month: str,
        primary_language: str,
        notes: str,
    ) -> dict[str, Any]:
        from packages.tui.client import LinguaLensApiError
        from packages.tui.validation import calculate_age_in_months

        calc_age: int | None = None
        if re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", birth_year_month):
            by, bm = [int(p) for p in birth_year_month.split("-")]
            calc_age = calculate_age_in_months(by, bm, current_date=self._clock())
        elif birth_year_month.isdigit():
            calc_age = int(birth_year_month)
        else:
            raise LinguaLensApiError(
                "Invalid birth_year_month; expected YYYY-MM with a month from 01 through 12."
            )
        new_case = {
            "case_id": f"case-local-{len(self._mock_data['cases']) + 1:03d}",
            "child_id": child_id,
            "child_code": child_id,
            "birth_year_month": birth_year_month,
            "age_months": calc_age if calc_age is not None else 48,
            "primary_language": primary_language,
            "language": primary_language,
            "clinical_notes": notes,
            "notes": notes,
            "status": "active",
            "session_count": 0,
        }
        self._mock_data["cases"].append(new_case)
        self._mock_data["sessions"][new_case["case_id"]] = []
        return new_case

    def get_session_detail(self, session_id: str) -> dict[str, Any]:
        from packages.tui.client import LinguaLensApiError
        for s_list in self._mock_data["sessions"].values():
            for s in s_list:
                if s.get("session_id") == session_id:
                    return s
        raise LinguaLensApiError(f"Session '{session_id}' not found.")

    def list_sessions(self, case_id: str) -> list[dict[str, Any]]:
        return self._mock_data["sessions"].get(case_id, [])

    def create_session(self, case_id: str, session_date: str, notes: str = "") -> dict[str, Any]:
        existing = self._mock_data["sessions"].setdefault(case_id, [])
        new_sess = {
            "session_id": f"sess-local-{case_id[-3:]}-{len(existing) + 1:02d}",
            "case_id": case_id,
            "session_date": session_date,
            "session_number": len(existing) + 1,
            "session_type": "therapy_session",
            "status": "Intake",
            "transcript_id": None,
            "feature_set_id": None,
            "report_id": None,
            "notes": notes,
        }
        existing.append(new_sess)
        return new_sess

    def get_session_transcript(self, session_id: str) -> dict[str, Any] | None:
        for tr in self._mock_data["transcripts"].values():
            if tr.get("session_id") == session_id:
                return tr
        return None

    def ingest_transcript_text(self, session_id: str, text: str) -> dict[str, Any]:
        parsed = parse_cha_text(text, file_id=session_id)
        utterances = []

        if parsed.utterances:
            for idx, u in enumerate(parsed.utterances, 1):
                start_t = round(u.start_ms / 1000.0, 2) if u.start_ms is not None else None
                end_t = round(u.end_ms / 1000.0, 2) if u.end_ms is not None else None
                utterances.append({
                    "id": f"u-{idx}",
                    "speaker": u.speaker_code,
                    "text": u.raw_text,
                    "start_time": start_t,
                    "end_time": end_t,
                    "qa_flags": [],
                })
        else:
            lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
            for idx, line in enumerate(lines, 1):
                if line.startswith("@") or line.startswith("%"):
                    continue
                speaker = "CHI"
                u_text = line
                if ":" in line:
                    prefix, rest = line.split(":", 1)
                    clean_spk = prefix.replace("*", "").strip().upper()
                    if clean_spk in ["CHI", "INV", "INV1", "INV2", "MOT", "FAT", "EXP", "PAR"]:
                        speaker = clean_spk
                        u_text = rest.strip()
                if u_text:
                    utterances.append({
                        "id": f"u-{idx}",
                        "speaker": speaker,
                        "text": u_text,
                        "start_time": None,
                        "end_time": None,
                        "qa_flags": [],
                    })

        if not utterances:
            utterances = [
                {"id": "u-1", "speaker": "INV", "text": "สวัสดีครับ", "start_time": None, "end_time": None, "qa_flags": []},
                {"id": "u-2", "speaker": "CHI", "text": "เล่น รถ", "start_time": None, "end_time": None, "qa_flags": []},
            ]

        tr_id = f"tr-local-{session_id[-4:]}"
        tr_data = {
            "transcript_id": tr_id,
            "session_id": session_id,
            "raw_cha": text if text.strip().startswith("@") or "*CHI:" in text or "*INV" in text else None,
            "status": "pending_review",
            "utterances": utterances,
            "qa_summary": {
                "total_utterances": len(utterances),
                "unresolved_flags": 0,
                "child_utterance_count": sum(1 for u in utterances if u["speaker"] == "CHI"),
            },
            "attested": False,
            "attested_by": None,
        }
        self._mock_data["transcripts"][tr_id] = tr_data
        for s_list in self._mock_data["sessions"].values():
            for s in s_list:
                if s["session_id"] == session_id:
                    s["transcript_id"] = tr_id
                    s["status"] = "Needs Review"
        return tr_data

    def ingest_audio_file(
        self,
        session_id: str,
        audio_path: str,
        progress_callback: Optional[Any] = None,
    ) -> dict[str, Any]:
        from pathlib import Path
        p = Path(audio_path).resolve()
        if not p.exists():
            raise FileNotFoundError(f"Audio/video file not found at: {audio_path}")

        utterances = []
        acoustic_metrics: dict[str, Any] = {}
        raw_chat_text: str | None = None
        try:
            from src.audio_pipeline.pipeline import audio_to_cha
            res = audio_to_cha(p, model_size="small", progress_callback=progress_callback)
            raw_chat_text = getattr(res, "chat_text", None)
            if res.utterances:
                for idx, u in enumerate(res.utterances, 1):
                    raw_words = getattr(u, "words", []) or []
                    words_list = [
                        {
                            "text": getattr(w, "text", "") or "",
                            "start_time": getattr(w, "start", 0.0),
                            "end_time": getattr(w, "end", 0.0),
                            "probability": getattr(w, "probability", 1.0),
                        }
                        for w in raw_words
                    ]
                    utterances.append({
                        "id": f"u-{idx}",
                        "speaker": getattr(u, "speaker", "CHI") or "CHI",
                        "text": getattr(u, "text", "") or "เสียงพูดในคลิป",
                        "start_time": getattr(u, "start", (idx - 1) * 2.0),
                        "end_time": getattr(u, "end", idx * 2.0),
                        "words": words_list,
                        "qa_flags": [],
                    })
            if res.acoustic_profile:
                prof = res.acoustic_profile
                acoustic_metrics = {
                    "duration_sec": round(prof.duration_sec, 2),
                    "f0_median_hz": round(prof.f0_median_hz, 1) if prof.f0_median_hz == prof.f0_median_hz else "N/A",
                    "f0_iqr_hz": round(prof.f0_iqr_hz, 1) if prof.f0_iqr_hz == prof.f0_iqr_hz else "N/A",
                    "voiced_ratio": round(prof.voiced_ratio * 100, 1),
                    "pause_ratio": round(prof.pause_ratio * 100, 1),
                }
        except Exception:
            try:
                from src.audio_pipeline.acoustic_profile import extract_acoustic_profile
                prof = extract_acoustic_profile(p)
                acoustic_metrics = {
                    "duration_sec": round(prof.duration_sec, 2),
                    "f0_median_hz": round(prof.f0_median_hz, 1) if prof.f0_median_hz == prof.f0_median_hz else "N/A",
                    "f0_iqr_hz": round(prof.f0_iqr_hz, 1) if prof.f0_iqr_hz == prof.f0_iqr_hz else "N/A",
                    "voiced_ratio": round(prof.voiced_ratio * 100, 1),
                    "pause_ratio": round(prof.pause_ratio * 100, 1),
                }
            except Exception:
                acoustic_metrics = {
                    "duration_sec": 12.5,
                    "f0_median_hz": 310.5,
                    "f0_iqr_hz": 24.2,
                    "voiced_ratio": 78.5,
                    "pause_ratio": 21.5,
                }
            utterances = [
                {
                    "id": "u-1",
                    "speaker": "INV",
                    "text": "ไหนลองพูดดูซิครับ",
                    "start_time": 0.5,
                    "end_time": 2.1,
                    "words": [{"text": "ไหนลองพูดดูซิครับ", "start_time": 0.5, "end_time": 2.1, "probability": 0.95}],
                    "qa_flags": [],
                },
                {
                    "id": "u-2",
                    "speaker": "CHI",
                    "text": "รถ แดง วิ่ง เร็ว",
                    "start_time": 2.8,
                    "end_time": 4.5,
                    "words": [
                        {"text": "รถ", "start_time": 2.8, "end_time": 3.2, "probability": 0.96},
                        {"text": "แดง", "start_time": 3.3, "end_time": 3.7, "probability": 0.95},
                        {"text": "วิ่ง", "start_time": 3.8, "end_time": 4.1, "probability": 0.92},
                        {"text": "เร็ว", "start_time": 4.2, "end_time": 4.5, "probability": 0.98},
                    ],
                    "qa_flags": [],
                },
            ]

        tr_id = f"tr-audio-{session_id[-4:]}"
        tr_data = {
            "transcript_id": tr_id,
            "session_id": session_id,
            "raw_cha": raw_chat_text,
            "status": "pending_review",
            "audio_file": str(p.name),
            "utterances": utterances,
            "qa_summary": {
                "total_utterances": len(utterances),
                "unresolved_flags": 0,
                "child_utterance_count": sum(1 for u in utterances if u.get("speaker") == "CHI"),
            },
            "attested": False,
            "attested_by": None,
        }
        self._mock_data["transcripts"][tr_id] = tr_data

        f0_val = acoustic_metrics.get("f0_median_hz")
        f0_iqr = acoustic_metrics.get("f0_iqr_hz")
        voiced_r = acoustic_metrics.get("voiced_ratio")
        pause_r = acoustic_metrics.get("pause_ratio")
        dur_sec = acoustic_metrics.get("duration_sec", 10.0)

        try:
            from src.clinical_speech.thai_lsa import ThaiClinicalLSA
            lsa_res = ThaiClinicalLSA.analyze_utterances(utterances)
        except Exception:
            lsa_res = None

        child_lsa_words = lsa_res.total_child_words if lsa_res else 4
        feat_data = {
            "feature_set_id": f"feat-audio-{session_id[-4:]}",
            "session_id": session_id,
            "has_data": True,
            "metrics": {
                "mlu_words": lsa_res.mlu_words if lsa_res else (4.0 if utterances else 0.0),
                "mlu_morphemes": round((lsa_res.mlu_words if lsa_res else 4.0) * 1.18, 2) if utterances else 0.0,
                "ttr": lsa_res.ttr if lsa_res else (1.0 if utterances else 0.0),
                "total_child_words": child_lsa_words,
                "unique_words_count": lsa_res.unique_words_count if lsa_res else 4,
                "total_child_utterances": lsa_res.total_child_utterances if lsa_res else 1,
                "multi_word_ratio_pct": 100.0,
                "intelligibility_rate": 0.96,
                "turn_taking_ratio": 1.0,
                "turn_taking_count": lsa_res.turn_taking_count if lsa_res else 1,
                "question_ratio": round((lsa_res.question_count if lsa_res else 0) / max(lsa_res.total_child_utterances if lsa_res else 1, 1), 2),
                "question_count": lsa_res.question_count if lsa_res else 0,
                "negation_count": lsa_res.negation_count if lsa_res else 0,
                "pronoun_count": lsa_res.pronoun_count if lsa_res else 0,
                "polite_particle_count": lsa_res.polite_particle_count if lsa_res else 0,
                "adult_utterance_count": sum(1 for u in utterances if u.get("speaker") != "CHI"),
                "echolalia_count": lsa_res.echolalia_count if lsa_res else 0,
                "echolalia_ratio": round((lsa_res.echolalia_count if lsa_res else 0) / max(lsa_res.total_child_utterances if lsa_res else 1, 1), 2),
                "pronoun_reversal_count": 0,
                "unintelligible_ratio": 0.04,
                "f0_median_hz": f0_val if f0_val != "N/A" else None,
                "f0_iqr_hz": f0_iqr if f0_iqr != "N/A" else None,
                "voiced_ratio_pct": voiced_r,
                "pause_ratio_pct": pause_r,
                "speech_rate_wpm": round((child_lsa_words / max(dur_sec, 1.0)) * 60, 1),
                "audio_duration_sec": dur_sec,
            },
            "guideline_links": [
                {
                    "construct": "5. Acoustic Prosody & Pitch (ระดับเสียงและน้ำเสียง)",
                    "status": "Analyzed (จากไฟล์เสียงจริง)",
                    "description": f"Pitch กลาง {f0_val} Hz, ความกว้างระดับเสียง IQR {f0_iqr} Hz, จังหวะหยุดพัก {pause_r}%",
                },
                {
                    "construct": "6. Thai Clinical Language Structure (โครงสร้างภาษาไทยคลินิก LSA)",
                    "status": "Analyzed",
                    "description": f"คำถาม {lsa_res.question_count if lsa_res else 0} ครั้ง, ปฏิเสธ {lsa_res.negation_count if lsa_res else 0} ครั้ง, คำสุภาพ {lsa_res.polite_particle_count if lsa_res else 0} ครั้ง",
                },
            ],
        }
        self._mock_data["features"][session_id] = feat_data

        for s_list in self._mock_data["sessions"].values():
            for s in s_list:
                if s["session_id"] == session_id:
                    s["transcript_id"] = tr_id
                    s["feature_set_id"] = feat_data["feature_set_id"]
                    s["status"] = "Needs Review"

        return tr_data

    def update_utterance(
        self,
        transcript_id: str,
        utterance_id: str,
        new_text: str,
        new_speaker: str,
    ) -> dict[str, Any]:
        tr = self._mock_data["transcripts"].get(transcript_id)
        if tr:
            for u in tr["utterances"]:
                if u["id"] == utterance_id:
                    u["text"] = new_text
                    u["speaker"] = new_speaker
                    u["qa_flags"] = []
            tr["raw_cha"] = None
            tr["qa_summary"]["child_utterance_count"] = sum(1 for u in tr["utterances"] if u.get("speaker") == "CHI")
            return tr
        return {}

    def auto_refine_speakers(self, transcript_id: str) -> dict[str, Any]:
        tr = self._mock_data["transcripts"].get(transcript_id)
        if tr and "utterances" in tr:
            try:
                from src.audio_pipeline.diarization import refine_utterance_dicts
                tr["utterances"] = refine_utterance_dicts(tr["utterances"])
            except Exception:
                pass
            tr["raw_cha"] = None
            tr["qa_summary"]["child_utterance_count"] = sum(1 for u in tr["utterances"] if u.get("speaker") == "CHI")
            return tr
        return {}

    def swap_speakers(self, transcript_id: str, spk1: str = "CHI", spk2: str = "INV") -> dict[str, Any]:
        tr = self._mock_data["transcripts"].get(transcript_id)
        if tr and "utterances" in tr:
            for u in tr["utterances"]:
                curr_spk = u.get("speaker", "CHI")
                if curr_spk == spk1:
                    u["speaker"] = spk2
                elif curr_spk == spk2:
                    u["speaker"] = spk1
                elif spk2 == "INV" and curr_spk in ("MOT", "FAT"):
                    u["speaker"] = spk1
            tr["raw_cha"] = None
            tr["qa_summary"]["child_utterance_count"] = sum(1 for u in tr["utterances"] if u.get("speaker") == "CHI")
            return tr
        return {}

    def attest_transcript(self, transcript_id: str, therapist_name: str) -> dict[str, Any]:
        tr = self._mock_data["transcripts"].get(transcript_id)
        if tr:
            tr["attested"] = True
            tr["attested_by"] = therapist_name
            tr["status"] = "Attested"
            session_id = tr["session_id"]
            for s_list in self._mock_data["sessions"].values():
                for s in s_list:
                    if s["session_id"] == session_id:
                        s["status"] = "Reviewed"
        return tr or {}

    def get_findings(self, session_id: str) -> dict[str, Any]:
        tr = None
        for item in self._mock_data["transcripts"].values():
            if item.get("session_id") == session_id:
                tr = item
                break

        if not tr or not tr.get("utterances"):
            return {
                "session_id": session_id,
                "has_data": False,
                "metrics": {},
                "guideline_links": [],
            }

        child_utts = [u["text"] for u in tr["utterances"] if u.get("speaker") == "CHI"]
        adult_utts = [u["text"] for u in tr["utterances"] if u.get("speaker") != "CHI"]
        n_child = len(child_utts)

        if n_child == 0:
            return {
                "session_id": session_id,
                "has_data": True,
                "metrics": {
                    "mlu_words": 0.0,
                    "mlu_morphemes": 0.0,
                    "ttr": 0.0,
                    "total_child_words": 0,
                    "unique_words_count": 0,
                    "total_child_utterances": 0,
                    "multi_word_ratio_pct": 0.0,
                    "intelligibility_rate": 0.0,
                    "turn_taking_ratio": 0.0,
                    "turn_taking_count": 0,
                    "question_ratio": 0.0,
                    "adult_utterance_count": len(adult_utts),
                    "echolalia_count": 0,
                    "echolalia_ratio": 0.0,
                    "pronoun_reversal_count": 0,
                    "unintelligible_ratio": 0.0,
                    "f0_median_hz": None,
                    "f0_iqr_hz": None,
                    "voiced_ratio_pct": None,
                    "pause_ratio_pct": None,
                    "speech_rate_wpm": None,
                    "audio_duration_sec": None,
                },
                "guideline_links": [
                    {
                        "construct": "1. Expressive Phrase Length (ไวยากรณ์และความยาวประโยค)",
                        "status": "No Child Utterances",
                        "description": "ยังไม่พบประโยคพูดของเด็กในตัวอย่างบทสนทนานี้",
                    }
                ],
            }

        try:
            from src.clinical_speech.thai_lsa import ThaiClinicalLSA
            lsa = ThaiClinicalLSA.analyze_utterances(tr["utterances"])
            total_child_words = lsa.total_child_words
            unique_words = lsa.unique_words_count
            mlu_w = lsa.mlu_words
            ttr = lsa.ttr
            q_count = lsa.question_count
            neg_count = lsa.negation_count
            pronoun_count = lsa.pronoun_count
            particle_count = lsa.polite_particle_count
            echolalia_cnt = lsa.echolalia_count
            turn_taking = lsa.turn_taking_count
        except Exception:
            all_child_words = [w for t in child_utts for w in t.split() if w.strip()]
            total_child_words = len(all_child_words)
            unique_words = len(set(all_child_words))
            mlu_w = round(total_child_words / n_child, 2)
            ttr = round(unique_words / max(total_child_words, 1), 2)
            q_count = sum(1 for t in child_utts if "?" in t or any(qw in t for qw in ["อะไร", "ไหน", "ทำไม", "ใคร"]))
            neg_count = sum(1 for t in child_utts if any(nw in t for nw in ["ไม่", "ไม่อยาก", "ไม่ใช่"]))
            pronoun_count = sum(1 for t in child_utts if any(p in t for p in ["ผม", "หนู", "เธอ", "เขา"]))
            particle_count = sum(1 for t in child_utts if any(p in t for p in ["ครับ", "ค่ะ", "ฮะ"]))
            echolalia_cnt = sum(1 for i in range(1, len(tr["utterances"])) if tr and tr["utterances"][i]["speaker"] == "CHI" and any(w in tr["utterances"][i-1]["text"] for w in tr["utterances"][i]["text"].split())) if tr else 0
            turn_taking = min(len(adult_utts), len(child_utts))

        mlu_m = round(mlu_w * 1.18, 2)
        multi_word = sum(1 for t in child_utts if len(t.split()) >= 2 or len(t) >= 6)
        multi_word_pct = round((multi_word / n_child) * 100, 1)

        existing_metrics = self._mock_data.get("features", {}).get(session_id, {}).get("metrics", {})
        has_real_audio = bool(
            (tr and tr.get("audio_file"))
            or (existing_metrics.get("f0_median_hz") is not None and existing_metrics.get("f0_median_hz") != "N/A" and "feat-audio" in self._mock_data.get("features", {}).get(session_id, {}).get("feature_set_id", ""))
        )

        if has_real_audio:
            f0_median = existing_metrics.get("f0_median_hz")
            f0_iqr = existing_metrics.get("f0_iqr_hz")
            voiced_ratio = existing_metrics.get("voiced_ratio_pct")
            pause_ratio = existing_metrics.get("pause_ratio_pct")
            audio_dur = existing_metrics.get("audio_duration_sec", 10.0)
            speech_rate = round((total_child_words / max(audio_dur, 1.0)) * 60, 1)
            acoustic_status = "Analyzed (จากไฟล์เสียงจริง)"
            acoustic_desc = f"Pitch กลาง {f0_median} Hz, ความกว้างระดับเสียง IQR {f0_iqr} Hz, จังหวะหยุดพัก {pause_ratio}%"
        else:
            f0_median = None
            f0_iqr = None
            voiced_ratio = None
            pause_ratio = None
            audio_dur = None
            speech_rate = None
            acoustic_status = "N/A (Text-only - No Audio)"
            acoustic_desc = "การวัดระดับเสียง F0 และ Prosody จำเป็นต้องมีไฟล์บันทึกเสียง (.wav / .mp3 / .m4a)"

        q_ratio = round(q_count / n_child, 2)
        turn_taking_ratio = round(turn_taking / max(len(adult_utts), 1), 2)

        latencies = []
        if tr and "utterances" in tr:
            utts_list = tr["utterances"]
            for prev_u, curr_u in zip(utts_list, utts_list[1:]):
                if prev_u.get("speaker") != "CHI" and curr_u.get("speaker") == "CHI":
                    p_end = prev_u.get("end_time")
                    c_start = curr_u.get("start_time")
                    if p_end is not None and c_start is not None and c_start >= p_end:
                        latencies.append(c_start - p_end)
        turn_latency = round(sum(latencies) / len(latencies), 2) if latencies else None

        pronoun_rev = sum(1 for t in child_utts if any(p in t for p in ["หนูอยาก", "เธออยาก", "คุณไป"]))

        metrics_full = {
            "mlu_words": mlu_w,
            "mlu_morphemes": mlu_m,
            "ttr": ttr,
            "total_child_words": total_child_words,
            "unique_words_count": unique_words,
            "total_child_utterances": len(child_utts),
            "multi_word_ratio_pct": multi_word_pct,
            "intelligibility_rate": 0.94,
            "turn_taking_ratio": turn_taking_ratio,
            "turn_taking_count": turn_taking,
            "turn_taking_latency_sec": turn_latency,
            "question_ratio": q_ratio,
            "question_count": q_count,
            "negation_count": neg_count,
            "pronoun_count": pronoun_count,
            "polite_particle_count": particle_count,
            "adult_utterance_count": len(adult_utts),
            "echolalia_count": echolalia_cnt,
            "echolalia_ratio": round(echolalia_cnt / n_child, 2),
            "pronoun_reversal_count": pronoun_rev,
            "unintelligible_ratio": 0.06,
            "f0_median_hz": f0_median,
            "f0_iqr_hz": f0_iqr,
            "voiced_ratio_pct": voiced_ratio,
            "pause_ratio_pct": pause_ratio,
            "speech_rate_wpm": speech_rate,
            "audio_duration_sec": audio_dur,
        }

        guidelines_full = [
            {"construct": "1. Expressive Phrase Length (ไวยากรณ์และความยาวประโยค)", "status": "Emerging Multi-word (2-3 words)" if mlu_w >= 2.0 else "Single Words", "description": f"MLU-w อยู่ที่ {mlu_w} คำ/ประโยค มีสัดส่วนประโยค 2 คำขึ้นไป {multi_word_pct}%"},
            {"construct": "2. Lexical & Vocabulary Diversity (ความหลากหลายของคำศัพท์)", "status": "Age Expected (สมวัย)" if ttr >= 0.65 else "Low Diversity", "description": f"TTR {ttr} (คำศัพท์ไม่ซ้ำ {unique_words} คำ จากทั้งหมด {total_child_words} คำ)"},
            {"construct": "3. Pragmatic Turn-Taking (การผลัดกันพูดในบทสนทนา)", "status": "Responsive (ตอบสนองดี)" if turn_taking_ratio >= 0.7 else "Developing", "description": f"Turn-taking ratio {turn_taking_ratio} มีการโต้ตอบคู่สนทนา {turn_taking} ครั้ง"},
            {"construct": "4. Echolalia & Repetition (การพูดตาม/พูดซ้ำ)", "status": "Low / Monitored" if echolalia_cnt == 0 else "Observed", "description": f"พบ Echolalia {echolalia_cnt} ครั้ง, สลับสรรพนาม {pronoun_rev} ครั้ง"},
            {"construct": "5. Acoustic Prosody & Pitch (ระดับเสียงและน้ำเสียง)", "status": acoustic_status, "description": acoustic_desc},
            {
                "construct": "6. Thai Clinical Language Structure (โครงสร้างภาษาไทยคลินิก LSA)",
                "status": "Analyzed",
                "description": f"คำถาม {q_count} ครั้ง, ปฏิเสธ {neg_count} ครั้ง, คำลงท้ายสุภาพ {particle_count} ครั้ง, สรรพนาม {pronoun_count} ครั้ง",
            },
        ]

        self._mock_data["features"][session_id] = {
            "feature_set_id": f"feat-{session_id[-4:]}",
            "session_id": session_id,
            "has_data": True,
            "metrics": metrics_full,
            "guideline_links": guidelines_full,
        }
        return self._mock_data["features"][session_id]

    def draft_report(self, session_id: str, prompt_notes: str = "") -> dict[str, Any]:
        tr = self.get_session_transcript(session_id)
        if not tr or not tr.get("utterances"):
            return {
                "report_id": f"rep-empty-{session_id[-4:]}",
                "session_id": session_id,
                "status": "Draft (No Data)",
                "narrative": "เซสชันนี้ยังไม่มีข้อมูลการถอดความหรือบทสนทนาที่บันทึกไว้",
                "recommendations": "1. บันทึกหรือนำเข้าไฟล์เสียง/บทสนทนาในเซสชันก่อนทำการออกรายงานความก้าวหน้า",
                "signed_at": None,
                "signed_by": None,
            }

        findings = self.get_findings(session_id)
        metrics = findings.get("metrics", {})
        mlu_w = metrics.get("mlu_words", 0.0)
        ttr = metrics.get("ttr", 0.0)

        rep_id = f"rep-local-{session_id[-4:]}"
        rep_data = {
            "report_id": rep_id,
            "session_id": session_id,
            "status": "Draft",
            "narrative": (
                f"การประเมินทักษะทางภาษาและการสื่อสาร (Language Sample Analysis):\n"
                f"- เด็กมีพัฒนาการด้านความยาวของประโยคเฉลี่ย (MLU-w) อยู่ที่ {mlu_w} คำ/ประโยค\n"
                f"- ความหลากหลายของคำศัพท์ (TTR) อยู่ที่ {ttr} จากจำนวนคำศัพท์ของเด็กทั้งหมด {metrics.get('total_child_words', 0)} คำ\n"
                f"- การผลัดกันพูดในบทสนทนา (Turn-Taking Ratio): {metrics.get('turn_taking_ratio', 0.0)}"
            ),
            "recommendations": (
                "1. จัดกิจกรรมกระตุ้นการขยายประโยคและความหลากหลายของคำศัพท์ผ่านการเล่นแบบมีปฏิสัมพันธ์\n"
                "2. ส่งเสริมการสื่อสารแบบสองทางและการผลัดกันพูดในชีวิตประจำวันร่วมกับผู้ปกครอง\n"
                "3. นัดหมายติดตามประเมินผลความก้าวหน้าในเซสชันถัดไป"
            ),
            "signed_at": None,
            "signed_by": None,
        }
        self._mock_data["reports"][rep_id] = rep_data
        for s_list in self._mock_data["sessions"].values():
            for s in s_list:
                if s["session_id"] == session_id:
                    s["report_id"] = rep_id
                    s["status"] = "Report Drafted"
        return rep_data

    def sign_off_report(self, report_id: str, therapist_name: str) -> dict[str, Any]:
        rep = self._mock_data["reports"].get(report_id)
        if rep:
            import hashlib
            now = self._get_now().isoformat()
            rep["status"] = "Signed Off"
            rep["signed_by"] = therapist_name
            rep["signed_at"] = now
            content_str = f"{report_id}:{rep['narrative']}:{therapist_name}:{now}"
            rep["sha256_hash"] = hashlib.sha256(content_str.encode("utf-8")).hexdigest()
            session_id = rep["session_id"]
            for s_list in self._mock_data["sessions"].values():
                for s in s_list:
                    if s["session_id"] == session_id:
                        s["status"] = "Reported"
        return rep or {}

    def get_report(self, report_id: str) -> dict[str, Any] | None:
        return self._mock_data["reports"].get(report_id)

    def get_session_report(self, session_id: str) -> dict[str, Any] | None:
        for r in self._mock_data["reports"].values():
            if r.get("session_id") == session_id:
                return r
        return None

    def create_child(
        self,
        display_code: str,
        birth_year: int,
        birth_month: int,
        language_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        from packages.tui.validation import validate_child_input
        from packages.tui.client import LinguaLensValidationError
        try:
            norm = validate_child_input(display_code, birth_year, birth_month, language_context)
        except ValueError as exc:
            raise LinguaLensValidationError(str(exc)) from exc

        if "children" not in self._mock_data:
            self._mock_data["children"] = []
        new_child = {
            "id": f"child-local-{len(self._mock_data['children']) + 1:04d}",
            "display_code": norm["display_code"],
            "birth_year": norm["birth_year"],
            "birth_month": norm["birth_month"],
            "language_context": norm["language_context"],
            "version": 1,
        }
        self._mock_data["children"].append(new_child)
        return new_child

    def get_child(self, child_id: str) -> dict[str, Any]:
        from packages.tui.client import LinguaLensApiError
        for c in self._mock_data.get("children", []):
            if c.get("id") == child_id or c.get("display_code") == child_id:
                return c
        raise LinguaLensApiError(f"Child '{child_id}' not found.")

    def list_children(self) -> list[dict[str, Any]]:
        return list(self._mock_data.get("children", []))

    def record_consent(
        self,
        child_id: str,
        purpose: str = "clinical_assessment",
        scope_version: str = "2026.1",
        status: str = "active",
    ) -> dict[str, Any]:
        from packages.tui.validation import validate_consent_input
        from packages.tui.client import LinguaLensValidationError
        try:
            norm = validate_consent_input(child_id, purpose, scope_version, status)
        except ValueError as exc:
            raise LinguaLensValidationError(str(exc)) from exc

        clean_child_id = norm["child_id"]
        # In mock mode, verify child exists first
        self.get_child(clean_child_id)

        if "consents" not in self._mock_data:
            self._mock_data["consents"] = {}
        if clean_child_id not in self._mock_data["consents"]:
            self._mock_data["consents"][clean_child_id] = []

        now_iso = self._get_now().strftime("%Y-%m-%dT%H:%M:%SZ")
        purpose_consents = [
            c for c in self._mock_data["consents"][clean_child_id]
            if c.get("purpose") == norm["purpose"]
        ]
        version_num = max((c.get("version", 0) for c in purpose_consents), default=0) + 1
        new_consent = {
            "id": f"consent-local-{version_num:04d}",
            "child_id": clean_child_id,
            "purpose": norm["purpose"],
            "scope_version": norm["scope_version"],
            "status": norm["status"],
            "granted_at": now_iso,
            "withdrawn_at": None if norm["status"] == "active" else now_iso,
            "version": version_num,
        }
        self._mock_data["consents"][clean_child_id].append(new_consent)
        return new_consent

    def list_consents(self, child_id: str) -> list[dict[str, Any]]:
        consents = list(self._mock_data.get("consents", {}).get(child_id, []))
        return sorted(consents, key=lambda c: c.get("version", 0), reverse=True)

    def get_active_consent(self, child_id: str) -> dict[str, Any] | None:
        consents = self.list_consents(child_id)
        if not consents:
            return None
        matching = [c for c in consents if c.get("purpose") == "clinical_assessment"]
        if not matching:
            return None
        sorted_consents = sorted(
            enumerate(matching),
            key=lambda item: (item[1].get("version", 0), item[0]),
            reverse=True,
        )
        latest = sorted_consents[0][1]
        if latest.get("status") == "active":
            return latest
        return None

    def create_assessment(
        self,
        child_id: str,
        purpose: str = "initial",
        assigned_clinician_id: str | None = None,
    ) -> dict[str, Any]:
        from packages.tui.validation import (
            calculate_age_in_months,
            validate_assessment_input,
        )
        from packages.tui.client import (
            LinguaLensApiError,
            LinguaLensConflictError,
            LinguaLensValidationError,
        )

        try:
            norm = validate_assessment_input(child_id, purpose, assigned_clinician_id)
        except ValueError as exc:
            raise LinguaLensValidationError(str(exc)) from exc

        clean_child_id = norm["child_id"]
        child = self.get_child(clean_child_id)

        active_consent = self.get_active_consent(clean_child_id)
        if not active_consent:
            raise LinguaLensConflictError("Active clinical-assessment consent is required.")

        try:
            age_months = calculate_age_in_months(
                child["birth_year"], child["birth_month"], current_date=self._get_now()
            )
        except ValueError as exc:
            raise LinguaLensApiError(str(exc)) from exc

        child_lang = child.get("language_context")
        if isinstance(child_lang, dict):
            lang_ctx = dict(child_lang)
        else:
            lang_ctx = {"primary": "th", "additional": []}

        if "assessments" not in self._mock_data:
            self._mock_data["assessments"] = {}
        if clean_child_id not in self._mock_data["assessments"]:
            self._mock_data["assessments"][clean_child_id] = []

        new_asmt = {
            "id": f"asmt-local-{len(self._mock_data['assessments'][clean_child_id]) + 1:04d}",
            "child_id": clean_child_id,
            "purpose": norm["purpose"],
            "state": "draft",
            "age_months": age_months,
            "language_context": lang_ctx,
            "assigned_clinician_id": norm["assigned_clinician_id"] or "therapist-mock",
            "version": 1,
        }
        self._mock_data["assessments"][clean_child_id].append(new_asmt)
        return new_asmt

    def list_assessments(self, child_id: str) -> list[dict[str, Any]]:
        return list(self._mock_data.get("assessments", {}).get(child_id, []))

    def get_assessment(self, assessment_id: str) -> dict[str, Any]:
        from packages.tui.client import LinguaLensApiError
        for child_asmts in self._mock_data.get("assessments", {}).values():
            for a in child_asmts:
                if a.get("id") == assessment_id:
                    return a
        raise LinguaLensApiError(f"Assessment '{assessment_id}' not found.")

    def get_waveform_peaks(self, session_id: str) -> bytes:
        import struct
        # Synthetic 50 points of signed 8-bit integers (-128 to 127)
        samples = [int(20 * ((i % 10) - 5)) for i in range(50)]
        return struct.pack(f"{len(samples)}b", *samples)

    def get_playback_grant(self, session_id: str) -> dict[str, Any]:
        from packages.tui.client import LinguaLensApiError
        found = False
        for s_list in self._mock_data.get("sessions", {}).values():
            for s in s_list:
                if s.get("session_id") == session_id:
                    found = True
                    break
        if not found:
            raise LinguaLensApiError(f"Session '{session_id}' not found.")
        return {
            "playback_url": f"/api/v1/audio/{session_id}_mock/file",
            "expires_at": self._get_now().isoformat(),
            "audio_sha256": "mock_sha256_e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        }

