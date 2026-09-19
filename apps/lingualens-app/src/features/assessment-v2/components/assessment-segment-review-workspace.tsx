"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { AssessmentProcessingStatus } from "@/features/assessment-v2/components/assessment-processing-status";
import {
  AssessmentV2Client,
  type AssessmentV2TranscriptRevision,
  type AssessmentV2TranscriptSegmentReplayGrant,
  type AssessmentV2TranscriptSegmentSet,
  type AssessmentV2TranscriptSegmentSpeakerRole,
  type AssessmentV2TranscriptSegmentUncertaintyReason,
} from "@/services/assessment-v2-client";
import {
  activeFilterButtonClass,
  fieldClass,
  formatTime,
  isErrorCode,
  isStaleError,
  labelClass,
  primaryButtonClass,
  sameSegmentValues,
  secondaryButtonClass,
  SegmentAudioPlayer,
  segmentStateLabel,
  speakerLabel,
  toDraftSegments,
  toSegmentPayload,
  TranscriptDraftPanel,
  uncertaintyLabel,
  type SegmentDraft,
} from "@/features/assessment-v2/components/assessment-segment-review-ui";

export type AssessmentSegmentReviewClient = Pick<
  AssessmentV2Client,
  | "getTranscript"
  | "createTranscriptRevision"
  | "attestTranscript"
  | "getCurrentTranscriptSegmentSet"
  | "createTranscriptSegmentSet"
  | "attestTranscriptSegmentSet"
  | "createSegmentReplayGrant"
  | "queueEvidence"
  | "getCurrentEvidenceProcessingRun"
  | "getProcessingRun"
  | "retryProcessingRun"
  | "cancelProcessingRun"
>;

type AssessmentSegmentReviewWorkspaceProps = {
  assessmentId: string;
  client?: AssessmentSegmentReviewClient;
};

const defaultClient = new AssessmentV2Client();

export function AssessmentSegmentReviewWorkspace({
  assessmentId,
  client = defaultClient,
}: AssessmentSegmentReviewWorkspaceProps) {
  const [transcript, setTranscript] = useState<AssessmentV2TranscriptRevision | null>(null);
  const [draftTranscriptContent, setDraftTranscriptContent] = useState("");
  const [segmentSet, setSegmentSet] = useState<AssessmentV2TranscriptSegmentSet | null>(null);
  const [draftSegments, setDraftSegments] = useState<SegmentDraft[]>([]);
  const [selectedSegmentId, setSelectedSegmentId] = useState<string | null>(null);
  const [uncertainOnly, setUncertainOnly] = useState(false);
  const [replayGrants, setReplayGrants] = useState<Record<string, AssessmentV2TranscriptSegmentReplayGrant>>({});
  const [replayLoadingId, setReplayLoadingId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [conflict, setConflict] = useState(false);
  const [segmentUnavailable, setSegmentUnavailable] = useState(false);
  const [transcriptMissing, setTranscriptMissing] = useState(false);
  const [transcriptAttestationConfirmed, setTranscriptAttestationConfirmed] = useState(false);
  const [segmentAttestationConfirmed, setSegmentAttestationConfirmed] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const loadReview = useCallback(async () => {
    setLoading(true);
    setError(null);
    setActionError(null);
    setConflict(false);
    setNotice(null);
    try {
      const currentTranscript = await client.getTranscript(assessmentId);
      setTranscript(currentTranscript);
      setDraftTranscriptContent(currentTranscript.content);
      setTranscriptMissing(false);

      try {
        const currentSegmentSet = await client.getCurrentTranscriptSegmentSet(assessmentId);
        if (
          currentSegmentSet.transcript_revision_id !== currentTranscript.id
          || currentSegmentSet.transcript_content_sha256 !== currentTranscript.content_sha256
        ) {
          setSegmentSet(null);
          setDraftSegments([]);
          setSegmentUnavailable(true);
          setError("ช่วง transcript ไม่ตรงกับ revision ปัจจุบัน จึงยังไม่เปิดให้ตรวจต่อ");
        } else {
          setSegmentSet(currentSegmentSet);
          setDraftSegments(toDraftSegments(currentSegmentSet.segments));
          setSelectedSegmentId(currentSegmentSet.segments[0]?.id ?? null);
          setSegmentUnavailable(false);
        }
      } catch (segmentError) {
        if (isErrorCode(segmentError, "segment_set_not_found")) {
          setSegmentSet(null);
          setDraftSegments([]);
          setSegmentUnavailable(true);
        } else {
          throw segmentError;
        }
      }
    } catch (requestError) {
      if (isErrorCode(requestError, "transcript_not_found")) {
        setTranscript(null);
        setDraftTranscriptContent("");
        setTranscriptMissing(true);
        setSegmentSet(null);
        setDraftSegments([]);
        setSegmentUnavailable(false);
      } else {
        setTranscript(null);
        setSegmentSet(null);
        setDraftSegments([]);
        setError("ไม่สามารถโหลดข้อมูล transcript จาก FastAPI ได้");
      }
    } finally {
      setLoading(false);
    }
  }, [assessmentId, client]);

  useEffect(() => {
    void loadReview();
  }, [loadReview]);

  const visibleSegments = useMemo(
    () => (uncertainOnly ? draftSegments.filter((segment) => segment.uncertainty_reason !== "none") : draftSegments),
    [draftSegments, uncertainOnly],
  );
  const selectedSegment = draftSegments.find((segment) => segment.id === selectedSegmentId) ?? visibleSegments[0] ?? null;
  const transcriptDirty = Boolean(transcript && draftTranscriptContent !== transcript.content);
  const segmentsDirty = Boolean(segmentSet && !sameSegmentValues(draftSegments, segmentSet.segments));
  const transcriptIsDraft = transcript?.review_state === "draft";
  const segmentIsDraft = segmentSet?.review_state === "draft";

  useEffect(() => {
    if (selectedSegment && visibleSegments.some((segment) => segment.id === selectedSegment.id)) return;
    setSelectedSegmentId(visibleSegments[0]?.id ?? null);
  }, [selectedSegment, visibleSegments]);

  function updateSelectedSegment(patch: Partial<SegmentDraft>) {
    if (!selectedSegment) return;
    setDraftSegments((current) => current.map((segment) => (
      segment.id === selectedSegment.id ? { ...segment, ...patch } : segment
    )));
    setNotice(null);
    setActionError(null);
  }

  async function saveTranscriptDraft() {
    if (busy || !draftTranscriptContent.trim() || (transcript && !transcriptDirty)) return;
    setBusy(true);
    setActionError(null);
    setNotice(null);
    try {
      const saved = await client.createTranscriptRevision(assessmentId, {
        source: transcript?.source ?? "asr_draft",
        content: draftTranscriptContent,
        expected_revision: transcript?.revision ?? null,
        expected_version: transcript?.version ?? null,
      });
      setTranscript(saved);
      setDraftTranscriptContent(saved.content);
      setTranscriptMissing(false);
      setTranscriptAttestationConfirmed(false);
      setNotice("บันทึก transcript revision ใหม่แล้ว");
    } catch (requestError) {
      setActionError(isStaleError(requestError)
        ? "ข้อมูล transcript เปลี่ยนแปลงแล้ว กรุณาโหลด revision ล่าสุด"
        : "ยังบันทึก transcript ฉบับร่างไม่ได้ กรุณาลองใหม่");
    } finally {
      setBusy(false);
    }
  }

  async function attestTranscriptDraft() {
    if (!transcript || busy || !transcriptIsDraft || transcriptDirty || !transcriptAttestationConfirmed) return;
    setBusy(true);
    setActionError(null);
    try {
      const attested = await client.attestTranscript(transcript.id, transcript.version);
      setTranscript(attested);
      setDraftTranscriptContent(attested.content);
      setTranscriptAttestationConfirmed(false);
      setNotice("รับรอง transcript แล้ว กรุณาโหลด segment ที่สอดคล้องกับ revision นี้");
      await loadReview();
    } catch (requestError) {
      setActionError(isStaleError(requestError)
        ? "ข้อมูล transcript เปลี่ยนแปลงแล้ว กรุณาโหลด revision ล่าสุด"
        : "ยังรับรอง transcript ไม่ได้ กรุณาลองใหม่");
    } finally {
      setBusy(false);
    }
  }

  async function saveSegments() {
    if (!transcript || !segmentSet || busy || !segmentsDirty) return;
    const invalid = draftSegments.find((segment) => !segment.text.trim() || segment.end_ms <= segment.start_ms);
    if (invalid) {
      setActionError(`กรุณาตรวจช่วงเวลาและข้อความของช่วงที่ ${invalid.ordinal}`);
      return;
    }
    setBusy(true);
    setActionError(null);
    setConflict(false);
    setNotice(null);
    try {
      const saved = await client.createTranscriptSegmentSet(assessmentId, {
        transcript_revision_id: segmentSet.transcript_revision_id,
        source: segmentSet.source,
        recording_id: segmentSet.recording_id,
        expected_revision: segmentSet.revision,
        expected_version: segmentSet.version,
        segments: draftSegments.map(toSegmentPayload),
      });
      const selectedOrdinal = selectedSegment?.ordinal;
      setSegmentSet(saved);
      setDraftSegments(toDraftSegments(saved.segments));
      setSelectedSegmentId(saved.segments.find((segment) => segment.ordinal === selectedOrdinal)?.id ?? saved.segments[0]?.id ?? null);
      setSegmentAttestationConfirmed(false);
      setNotice("บันทึก segment revision ใหม่แล้ว ตรวจสอบอีกครั้งก่อนรับรอง");
    } catch (requestError) {
      if (isStaleError(requestError)) {
        setConflict(true);
        setActionError(null);
      } else {
        setActionError("ยังบันทึก segment revision ไม่ได้ กรุณาตรวจข้อมูลแล้วลองใหม่");
      }
    } finally {
      setBusy(false);
    }
  }

  async function attestSegments() {
    if (!segmentSet || busy || !segmentIsDraft || segmentsDirty || !segmentAttestationConfirmed) return;
    setBusy(true);
    setActionError(null);
    setConflict(false);
    setNotice(null);
    try {
      const attested = await client.attestTranscriptSegmentSet(segmentSet.id, segmentSet.version);
      setSegmentSet(attested);
      setDraftSegments(toDraftSegments(attested.segments));
      setSegmentAttestationConfirmed(false);
      setNotice("รับรอง segment revision แล้ว");
    } catch (requestError) {
      if (isStaleError(requestError)) {
        setConflict(true);
        setActionError(null);
      } else {
        setActionError("ยังรับรอง segment revision ไม่ได้ กรุณาลองใหม่");
      }
    } finally {
      setBusy(false);
    }
  }

  async function requestReplay(segment: SegmentDraft) {
    setReplayLoadingId(segment.id);
    setActionError(null);
    try {
      const grant = await client.createSegmentReplayGrant(segment.id);
      setReplayGrants((current) => ({ ...current, [segment.id]: grant }));
    } catch {
      setActionError("ยังเปิดเสียงช่วงนี้ไม่ได้ กรุณาลองใหม่โดยไม่กระทบ revision ที่บันทึกไว้");
    } finally {
      setReplayLoadingId(null);
    }
  }

  if (loading) {
    return <section className="workspace-panel p-6" aria-busy="true" role="status"><p>กำลังโหลด transcript และช่วงเสียง…</p></section>;
  }

  if (error) {
    return (
      <section className="workspace-panel p-6" role="alert">
        <h1 className="text-xl font-semibold">ไม่สามารถโหลดข้อมูลได้</h1>
        <p className="mt-2 text-sm text-[color:var(--color-text-muted)]">{error}</p>
        <button type="button" className={primaryButtonClass} onClick={() => void loadReview()}>โหลดข้อมูลอีกครั้ง</button>
      </section>
    );
  }

  if (transcriptMissing || !transcript) {
    return (
      <TranscriptDraftPanel
        content={draftTranscriptContent}
        busy={busy}
        error={actionError}
        onChange={setDraftTranscriptContent}
        onSave={() => void saveTranscriptDraft()}
        createMode
      />
    );
  }

  if (segmentUnavailable || !segmentSet) {
    return (
      <section className="space-y-5">
        <header>
          <p className="text-sm font-semibold text-[color:var(--color-accent)]">ขั้นตอนที่ 5 จาก 5</p>
          <h1 className="mt-1 text-2xl font-semibold">เตรียมการทบทวน transcript รายช่วง</h1>
          <p className="mt-2 text-sm text-[color:var(--color-text-muted)]">ระบบจะเปิดการตรวจทีละช่วงเมื่อ FastAPI มี segment ที่ผูกกับ transcript revision ปัจจุบัน</p>
        </header>
        {transcriptIsDraft ? (
          <TranscriptDraftPanel
            content={draftTranscriptContent}
            busy={busy}
            error={actionError}
            onChange={setDraftTranscriptContent}
            onSave={() => void saveTranscriptDraft()}
            onAttest={() => void attestTranscriptDraft()}
            attestationConfirmed={transcriptAttestationConfirmed}
            onAttestationChange={setTranscriptAttestationConfirmed}
          />
        ) : (
          <section className="workspace-panel border-amber-300 bg-amber-50 p-5 text-amber-950" role="status">
            <h2 className="text-lg font-semibold">ยังไม่มี segment สำหรับ revision นี้</h2>
            <p className="mt-2 text-sm">ไม่สร้างเวลาเริ่ม–จบแทนระบบ เพราะจะทำให้ข้อมูลเสียงคลาดเคลื่อน กรุณาให้ pipeline ส่ง segment ที่ตรวจสอบย้อนกลับได้ แล้วโหลดข้อมูลใหม่</p>
            <p className="mt-3 text-xs">transcript revision {transcript.revision} · {transcript.id}</p>
            <button type="button" className={secondaryButtonClass} onClick={() => void loadReview()}>โหลด revision ล่าสุด</button>
          </section>
        )}
        {notice ? <p className="text-sm text-emerald-800" role="status" aria-live="polite">{notice}</p> : null}
      </section>
    );
  }

  const canAttestSegments = segmentIsDraft && !segmentsDirty && segmentAttestationConfirmed && !busy;

  return (
    <section className="space-y-5" data-testid="assessment-segment-review-workspace">
      <header>
        <p className="text-sm font-semibold text-[color:var(--color-accent)]">ขั้นตอนที่ 5 จาก 5</p>
        <h1 className="mt-1 text-2xl font-semibold">ทบทวน transcript รายช่วง</h1>
        <p className="mt-2 max-w-3xl text-sm text-[color:var(--color-text-muted)]">ตรวจเฉพาะช่วงที่ไม่แน่ใจ เปิดฟังเสียงช่วงนั้นเมื่อมีสิทธิ์ แล้วบันทึก revision ใหม่ก่อนรับรอง ข้อมูลนี้เป็นหลักฐานเชิงพรรณนาเพื่อประกอบการพิจารณาของนักบำบัด ไม่ใช่การวินิจฉัยอัตโนมัติ</p>
      </header>

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-sky-200 bg-sky-50 p-4 text-sky-950" role="status">
        <div>
          <p className="font-semibold">สถานะ: {segmentStateLabel(segmentSet.review_state)}</p>
          <p className="mt-1 text-sm">transcript: <span className="font-semibold">{segmentStateLabel(transcript.review_state)}</span></p>
          <p className="mt-1 text-sm">revision {segmentSet.revision} · version {segmentSet.version} · {segmentSet.id}</p>
        </div>
        <p className="text-sm">{draftSegments.length} ช่วง · ไม่แน่ใจ {draftSegments.filter((segment) => segment.uncertainty_reason !== "none").length} ช่วง</p>
      </div>

      {conflict ? (
        <section className="rounded-xl border border-amber-400 bg-amber-50 p-4 text-amber-950" role="alert">
          <p className="font-semibold">ข้อมูล segment เปลี่ยนแปลงแล้ว</p>
          <p className="mt-1 text-sm">มี revision ใหม่จากผู้ใช้อื่นหรือจากระบบ จึงยังไม่เขียนทับข้อมูลนั้น</p>
          <button type="button" className={secondaryButtonClass} onClick={() => void loadReview()}>โหลด revision ล่าสุด</button>
        </section>
      ) : null}

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1.15fr)_minmax(19rem,0.85fr)]">
        <section className="workspace-panel p-4 sm:p-5" aria-labelledby="segment-timeline-heading">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 id="segment-timeline-heading" className="text-lg font-semibold">ลำดับช่วง transcript</h2>
              <p className="mt-1 text-sm text-[color:var(--color-text-muted)]">เลือกช่วงเพื่อแก้ไข ตรวจสอบ speaker และเปิดเสียง</p>
            </div>
            <button
              type="button"
              aria-pressed={uncertainOnly}
              className={uncertainOnly ? activeFilterButtonClass : secondaryButtonClass}
              onClick={() => setUncertainOnly((current) => !current)}
            >
              {uncertainOnly ? "แสดงทุกช่วง" : "แสดงเฉพาะช่วงที่ไม่แน่ใจ"}
            </button>
          </div>
          <ol className="mt-4 space-y-3" aria-label="ลำดับช่วง transcript">
            {visibleSegments.map((segment) => {
              const grant = replayGrants[segment.id];
              const selected = selectedSegment?.id === segment.id;
              return (
                <li key={segment.id}>
                  <article
                    data-selected={selected ? "true" : undefined}
                    className={`rounded-xl border p-4 transition-colors ${selected ? "border-[color:var(--color-accent)] bg-[color:var(--color-accent-soft)]" : "border-[color:var(--color-border)] bg-white"}`}
                  >
                    <div className="flex items-start gap-3">
                      <span className="mt-0.5 flex h-8 min-w-8 items-center justify-center rounded-full border border-[color:var(--color-accent)] text-xs font-semibold text-[color:var(--color-accent-strong)]">{segment.ordinal}</span>
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2 text-xs text-[color:var(--color-text-muted)]">
                          <span>{formatTime(segment.start_ms)}–{formatTime(segment.end_ms)}</span>
                          <span className="rounded-full bg-[color:var(--color-surface-muted)] px-2 py-1 font-semibold">{speakerLabel(segment.speaker_role)}</span>
                          {segment.uncertainty_reason !== "none" ? <span className="rounded-full bg-amber-100 px-2 py-1 font-semibold text-amber-900">ต้องตรวจ: {uncertaintyLabel(segment.uncertainty_reason)}</span> : null}
                        </div>
                        <p className="mt-2 whitespace-pre-wrap text-[length:var(--font-size-transcript)] leading-7 text-[color:var(--color-text-strong)]">{segment.text}</p>
                        {segment.confidence !== null ? <p className="mt-2 text-xs text-[color:var(--color-text-muted)]">ความมั่นใจจากระบบ {Math.round(segment.confidence * 100)}% · ใช้เป็นสัญญาณประกอบ ไม่ใช่ผลวินิจฉัย</p> : null}
                        <div className="mt-3 flex flex-wrap gap-2">
                          <button type="button" className={secondaryButtonClass} onClick={() => setSelectedSegmentId(segment.id)}>แก้ไขช่วงที่ {segment.ordinal}</button>
                          <button type="button" className={secondaryButtonClass} disabled={replayLoadingId === segment.id} onClick={() => void requestReplay(segment)}>
                            {replayLoadingId === segment.id ? "กำลังขอเสียง…" : `เล่นเสียงช่วงที่ ${segment.ordinal}`}
                          </button>
                        </div>
                        {grant?.available && grant.url ? <SegmentAudioPlayer grant={grant} ordinal={segment.ordinal} /> : null}
                        {grant && !grant.available ? <p className="mt-3 text-sm text-amber-900" role="status">เสียงของช่วงนี้ยังไม่พร้อมใช้งาน แต่ยังตรวจและบันทึกข้อความได้</p> : null}
                      </div>
                    </div>
                  </article>
                </li>
              );
            })}
          </ol>
          {visibleSegments.length === 0 ? <p className="mt-4 rounded-lg bg-[color:var(--color-surface-muted)] p-4 text-sm text-[color:var(--color-text-muted)]">ไม่พบช่วงที่ทำเครื่องหมายว่าไม่แน่ใจ</p> : null}
        </section>

        <section className="workspace-panel p-4 sm:p-5" aria-labelledby="segment-editor-heading">
          <h2 id="segment-editor-heading" className="text-lg font-semibold">แก้ไขช่วงที่เลือก</h2>
          {selectedSegment ? (
            <div className="mt-4 space-y-4">
              <div>
                <label className={labelClass} htmlFor={`segment-text-${selectedSegment.id}`}>ข้อความช่วงที่ {selectedSegment.ordinal}</label>
                <textarea id={`segment-text-${selectedSegment.id}`} aria-label={`ข้อความช่วงที่ ${selectedSegment.ordinal}`} value={selectedSegment.text} onChange={(event) => updateSelectedSegment({ text: event.target.value })} rows={5} disabled={busy} className={fieldClass} />
              </div>
              <div>
                <label className={labelClass} htmlFor={`segment-speaker-${selectedSegment.id}`}>บทบาทผู้พูดช่วงที่ {selectedSegment.ordinal}</label>
                <select id={`segment-speaker-${selectedSegment.id}`} aria-label={`บทบาทผู้พูดช่วงที่ ${selectedSegment.ordinal}`} value={selectedSegment.speaker_role} onChange={(event) => updateSelectedSegment({ speaker_role: event.target.value as AssessmentV2TranscriptSegmentSpeakerRole })} disabled={busy} className={fieldClass}>
                  <option value="child">เด็ก</option>
                  <option value="therapist">นักบำบัด</option>
                  <option value="caregiver">ผู้ดูแล</option>
                  <option value="unknown">ยังไม่ทราบ</option>
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div><label className={labelClass} htmlFor={`segment-start-${selectedSegment.id}`}>เริ่ม (ms)</label><input id={`segment-start-${selectedSegment.id}`} aria-label={`เวลาเริ่มช่วงที่ ${selectedSegment.ordinal}`} type="number" min={0} value={selectedSegment.start_ms} onChange={(event) => updateSelectedSegment({ start_ms: Number(event.target.value) })} disabled={busy} className={fieldClass} /></div>
                <div><label className={labelClass} htmlFor={`segment-end-${selectedSegment.id}`}>จบ (ms)</label><input id={`segment-end-${selectedSegment.id}`} aria-label={`เวลาจบช่วงที่ ${selectedSegment.ordinal}`} type="number" min={1} value={selectedSegment.end_ms} onChange={(event) => updateSelectedSegment({ end_ms: Number(event.target.value) })} disabled={busy} className={fieldClass} /></div>
              </div>
              <div>
                <label className={labelClass} htmlFor={`segment-uncertainty-${selectedSegment.id}`}>เหตุผลที่ไม่แน่ใจ</label>
                <select id={`segment-uncertainty-${selectedSegment.id}`} aria-label={`เหตุผลที่ไม่แน่ใจช่วงที่ ${selectedSegment.ordinal}`} value={selectedSegment.uncertainty_reason} onChange={(event) => updateSelectedSegment({ uncertainty_reason: event.target.value as AssessmentV2TranscriptSegmentUncertaintyReason })} disabled={busy} className={fieldClass}>
                  <option value="none">ไม่มี</option>
                  <option value="low_asr_confidence">ความมั่นใจการถอดเสียงต่ำ</option>
                  <option value="unintelligible_audio">ฟังไม่ชัด</option>
                  <option value="speaker_uncertain">ยังไม่แน่ใจผู้พูด</option>
                  <option value="timestamp_uncertain">ยังไม่แน่ใจเวลา</option>
                  <option value="manual_review">ต้องตรวจด้วยคน</option>
                </select>
              </div>
              <div>
                <label className={labelClass} htmlFor={`segment-confidence-${selectedSegment.id}`}>ความมั่นใจจากระบบ (0–1)</label>
                <input id={`segment-confidence-${selectedSegment.id}`} aria-label={`ความมั่นใจช่วงที่ ${selectedSegment.ordinal}`} type="number" min={0} max={1} step={0.01} value={selectedSegment.confidence ?? ""} onChange={(event) => updateSelectedSegment({ confidence: event.target.value === "" ? null : Number(event.target.value) })} disabled={busy} className={fieldClass} />
              </div>
              <button type="button" className={primaryButtonClass} disabled={busy || !segmentsDirty} onClick={() => void saveSegments()}>{busy ? "กำลังบันทึก…" : "บันทึก revision ใหม่"}</button>
              {segmentsDirty ? <p className="text-xs text-amber-900">มีการแก้ไขในหน้านี้ที่ยังไม่บันทึก</p> : null}
            </div>
          ) : <p className="mt-4 text-sm text-[color:var(--color-text-muted)]">เลือกช่วงจากรายการทางซ้ายเพื่อเริ่มตรวจ</p>}
        </section>
      </div>

      {segmentIsDraft ? (
        <section className="workspace-panel p-5" aria-labelledby="segment-attestation-heading">
          <h2 id="segment-attestation-heading" className="text-lg font-semibold">รับรอง segment revision</h2>
          <label className="mt-3 flex min-h-11 items-start gap-3 text-sm"><input type="checkbox" checked={segmentAttestationConfirmed} onChange={(event) => setSegmentAttestationConfirmed(event.target.checked)} disabled={busy || segmentsDirty} className="mt-1 h-4 w-4" /><span>ฉันได้ตรวจสอบทุกช่วง speaker เวลา และข้อความแล้ว และยืนยันว่า revision นี้พร้อมใช้เป็นหลักฐานเชิงพรรณนา</span></label>
          {segmentsDirty ? <p className="mt-3 text-sm text-amber-900">บันทึก revision ใหม่ก่อนจึงจะรับรองได้</p> : null}
          <button type="button" className={secondaryButtonClass} disabled={!canAttestSegments} onClick={() => void attestSegments()}>{busy ? "กำลังรับรอง…" : "รับรอง segment revision"}</button>
        </section>
      ) : null}

      {segmentSet.review_state === "attested" ? (
        <section className="rounded-xl border border-emerald-300 bg-emerald-50 p-5 text-emerald-950" role="status">
          <p className="font-semibold">รับรอง segment revision แล้ว</p>
          <p className="mt-1 text-sm">ระบบสามารถใช้ช่วงที่ตรวจแล้วเป็น input ของ evidence worker ได้</p>
          <div className="mt-4"><AssessmentProcessingStatus assessmentId={assessmentId} client={client} canQueue={!segmentsDirty} /></div>
        </section>
      ) : null}

      {notice ? <p className="text-sm text-emerald-800" role="status" aria-live="polite">{notice}</p> : null}
      {actionError ? <p className="text-sm text-red-800" role="alert">{actionError}</p> : null}
    </section>
  );
}
