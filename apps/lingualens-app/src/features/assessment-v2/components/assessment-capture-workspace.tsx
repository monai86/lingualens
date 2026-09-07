"use client";

import { useEffect, useMemo, useState } from "react";

import { BrowserAudioRecorder, type RecordingMetadata } from "@/components/browser-audio-recorder";
import {
  AssessmentV2Client,
  type AssessmentV2Assessment,
  type AssessmentV2Child,
  type AssessmentV2Consent,
  type AssessmentV2Capture,
  type AssessmentV2Purpose,
  type AssessmentV2Recording,
  type AssessmentV2Quality,
} from "@/services/assessment-v2-client";
import {
  uploadAssessmentRecording,
  type AssessmentRecordingUploadStage,
} from "@/features/assessment-v2/lib/assessment-recording-upload";

export type AssessmentCaptureClient = Pick<
  AssessmentV2Client,
  | "listChildren"
  | "getChild"
  | "listConsents"
  | "listAssessments"
  | "createConsent"
  | "createAssessment"
  | "selectProtocol"
  | "startCapture"
  | "createRecording"
  | "createUploadIntent"
  | "completeUpload"
  | "getCapture"
  | "getRecordingQuality"
  | "completeCapture"
>;

type AssessmentCaptureWorkspaceProps = {
  client?: AssessmentCaptureClient;
};

type WorkspaceStatus = "loading" | "children" | "setup" | "ready" | "capture" | "complete" | "error";
type UploadStatus = "idle" | "ready" | "uploading" | "uploaded" | "error";
type QualityStatus = "idle" | "checking" | "ready" | "error";

const PURPOSES: Array<{ value: AssessmentV2Purpose; label: string; description: string }> = [
  { value: "initial", label: "การประเมินครั้งแรก", description: "เก็บข้อมูลพื้นฐานเพื่อเริ่มทำความเข้าใจพัฒนาการ" },
  { value: "developmental_follow_up", label: "ติดตามพัฒนาการ", description: "ติดตามการเปลี่ยนแปลงจากการประเมินครั้งก่อน" },
  { value: "post_intervention_follow_up", label: "ติดตามหลังการช่วยเหลือ", description: "ดูข้อมูลประกอบหลังได้รับการช่วยเหลือหรือฝึกทักษะ" },
  { value: "additional_evidence", label: "เก็บหลักฐานเพิ่มเติม", description: "เพิ่มตัวอย่างเมื่อข้อมูลเดิมยังไม่เพียงพอ" },
];

const defaultAssessmentV2Client = new AssessmentV2Client();

export function AssessmentCaptureWorkspace({ client = defaultAssessmentV2Client }: AssessmentCaptureWorkspaceProps) {
  const [status, setStatus] = useState<WorkspaceStatus>("loading");
  const [children, setChildren] = useState<AssessmentV2Child[]>([]);
  const [selectedChild, setSelectedChild] = useState<AssessmentV2Child | null>(null);
  const [consents, setConsents] = useState<AssessmentV2Consent[]>([]);
  const [assessments, setAssessments] = useState<AssessmentV2Assessment[]>([]);
  const [capture, setCapture] = useState<AssessmentV2Capture | null>(null);
  const [purpose, setPurpose] = useState<AssessmentV2Purpose>("initial");
  const [consentConfirmed, setConsentConfirmed] = useState(false);
  const [activeActivityIndex, setActiveActivityIndex] = useState(0);
  const [recordingBlob, setRecordingBlob] = useState<Blob | null>(null);
  const [recordingMetadata, setRecordingMetadata] = useState<RecordingMetadata | null>(null);
  const [recordingIdempotencyKey, setRecordingIdempotencyKey] = useState<string | null>(null);
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>("idle");
  const [uploadStage, setUploadStage] = useState<AssessmentRecordingUploadStage | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [quality, setQuality] = useState<AssessmentV2Quality | null>(null);
  const [qualityStatus, setQualityStatus] = useState<QualityStatus>("idle");
  const [qualityError, setQualityError] = useState<string | null>(null);
  const [completedAssessment, setCompletedAssessment] = useState<AssessmentV2Assessment | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadChildren() {
    setStatus("loading");
    setError(null);
    try {
      setChildren(await client.listChildren());
      setStatus("children");
    } catch {
      setStatus("error");
      setError("ไม่สามารถโหลดรายการเด็กได้");
    }
  }

  useEffect(() => {
    void loadChildren();
  }, [client]);

  async function chooseChild(child: AssessmentV2Child) {
    setBusy(true);
    setError(null);
    try {
      const [loadedChild, loadedConsents, loadedAssessments] = await Promise.all([
        client.getChild(child.id),
        client.listConsents(child.id),
        client.listAssessments(child.id),
      ]);
      setSelectedChild(loadedChild);
      setConsents(loadedConsents);
      setAssessments(loadedAssessments);
      setCompletedAssessment(null);
      setConsentConfirmed(false);
      setStatus("setup");
    } catch {
      setError("ไม่สามารถโหลดข้อมูลสำหรับการประเมินได้");
    } finally {
      setBusy(false);
    }
  }

  const latestClinicalConsent = useMemo(() => {
    return consents
      .filter((consent) => consent.purpose === "clinical_assessment")
      .sort((left, right) => right.version - left.version)[0] ?? null;
  }, [consents]);

  const hasActiveConsent = latestClinicalConsent?.status === "active";
  const selectedPurpose = PURPOSES.find((item) => item.value === purpose) ?? PURPOSES[0];

  async function createAssessment() {
    if (!selectedChild || busy) return;
    if (!hasActiveConsent && !consentConfirmed) return;

    setBusy(true);
    setError(null);
    try {
      if (!hasActiveConsent) {
        const consent = await client.createConsent(selectedChild.id, {
          purpose: "clinical_assessment",
          scope_version: "clinical-v1",
          status: "active",
        });
        setConsents((current) => [consent, ...current]);
      }
      const assessment = await client.createAssessment(selectedChild.id, { purpose });
      const selectedCapture = await client.selectProtocol(assessment.id);
      setCapture(selectedCapture);
      setCompletedAssessment(null);
      setActiveActivityIndex(firstPendingActivityIndex(selectedCapture));
      resetRecordingState();
      setAssessments((current) => [assessment, ...current]);
      setStatus("ready");
    } catch {
      setError("ยังเริ่มการประเมินไม่ได้ กรุณาตรวจ consent และลองใหม่");
    } finally {
      setBusy(false);
    }
  }

  async function beginCapture() {
    if (!capture || busy) return;
    setBusy(true);
    setError(null);
    try {
      const started = await client.startCapture(capture.assessment_id);
      setCapture((current) => current ? { ...current, state: started.state } : current);
      resetRecordingState();
      setStatus("capture");
    } catch {
      setError("ยังเริ่มการบันทึกไม่ได้ กรุณาตรวจ consent และลองใหม่");
    } finally {
      setBusy(false);
    }
  }

  function resetRecordingState() {
    setRecordingBlob(null);
    setRecordingMetadata(null);
    setRecordingIdempotencyKey(null);
    setUploadStatus("idle");
    setUploadStage(null);
    setUploadError(null);
    setQuality(null);
    setQualityStatus("idle");
    setQualityError(null);
  }

  function handleRecordingReady(blob: Blob, metadata: RecordingMetadata) {
    setRecordingBlob(blob);
    setRecordingMetadata(metadata);
    setRecordingIdempotencyKey(createRecordingIdempotencyKey());
    setUploadStatus("ready");
    setUploadStage(null);
    setUploadError(null);
  }

  async function uploadCurrentRecording() {
    const activeActivity = capture?.activities[activeActivityIndex];
    if (!capture || !activeActivity || !recordingBlob || !recordingIdempotencyKey || busy) return;

    setBusy(true);
    setUploadStatus("uploading");
    setUploadError(null);
    try {
      const result = await uploadAssessmentRecording({
        client,
        assessmentId: capture.assessment_id,
        activityCode: activeActivity.activity_code,
        blob: recordingBlob,
        idempotencyKey: recordingIdempotencyKey,
        onStageChange: setUploadStage,
      });
      setCapture((current) => current ? {
        ...current,
        recordings: replaceRecording(current.recordings, result.recording),
      } : current);
      setUploadStatus("uploaded");
      setUploadStage(null);
      setQualityStatus("checking");
    } catch {
      setUploadStatus("error");
      setUploadStage(null);
      setUploadError("อัปโหลดไม่สำเร็จ ไฟล์ยังไม่ถูกทำเครื่องหมายว่าเสร็จสมบูรณ์ กรุณาลองใหม่");
    } finally {
      setBusy(false);
    }
  }

  function continueToNextActivity() {
    if (!capture || uploadStatus !== "uploaded") return;
    setActiveActivityIndex((current) => current + 1);
    resetRecordingState();
  }

  async function completeAssessmentCapture() {
    if (!capture || quality?.status !== "usable" || busy) return;

    setBusy(true);
    setError(null);
    try {
      const assessment = await client.completeCapture(capture.assessment_id);
      setCompletedAssessment(assessment);
      setStatus("complete");
    } catch {
      setError("ยังส่ง assessment เข้า processing ไม่ได้ กรุณารอผลตรวจคุณภาพแล้วลองใหม่");
    } finally {
      setBusy(false);
    }
  }

  function handleRecordingCleared() {
    resetRecordingState();
  }

  const activeActivity = capture?.activities[activeActivityIndex] ?? null;
  const captureId = capture?.assessment_id;
  const activeActivityCode = activeActivity?.activity_code;

  useEffect(() => {
    if (uploadStatus !== "uploaded" || !captureId || !activeActivityCode) return;
    const assessmentId = captureId;
    const activityCode = activeActivityCode;

    let cancelled = false;
    let retryTimer: number | undefined;

    async function pollQuality() {
      try {
        const refreshedCapture = await client.getCapture(assessmentId);
        if (cancelled) return;
        setCapture(refreshedCapture);
        const recording = refreshedCapture.recordings.find((item) => (
          item.activity_code === activityCode
          && (item.upload_state === "verified" || item.upload_state === "uploaded")
        ));
        if (!recording || recording.upload_state !== "verified") {
          retryTimer = window.setTimeout(() => void pollQuality(), 1500);
          return;
        }
        const result = await client.getRecordingQuality(recording.id);
        if (cancelled) return;
        if (result) {
          setQuality(result);
          setQualityStatus("ready");
          setQualityError(null);
          return;
        }
        retryTimer = window.setTimeout(() => void pollQuality(), 1500);
      } catch {
        if (cancelled) return;
        setQualityStatus("error");
        setQualityError("ยังโหลดผลตรวจคุณภาพไม่ได้ ระบบจะลองตรวจสอบให้อัตโนมัติ");
        retryTimer = window.setTimeout(() => void pollQuality(), 3000);
      }
    }

    setQualityStatus("checking");
    void pollQuality();
    return () => {
      cancelled = true;
      if (retryTimer !== undefined) window.clearTimeout(retryTimer);
    };
  }, [activeActivityCode, captureId, client, uploadStatus]);

  if (status === "loading") {
    return <section className="workspace-panel p-6" aria-busy="true"><p>กำลังโหลดรายการเด็ก…</p></section>;
  }

  if (status === "error") {
    return (
      <section className="workspace-panel p-6" role="alert">
        <h1 className="text-xl font-semibold">ไม่สามารถโหลดรายการเด็กได้</h1>
        <p className="mt-2 text-sm text-[color:var(--color-text-muted)]">{error}</p>
        <button type="button" className="mt-4 rounded-lg bg-[color:var(--color-primary)] px-4 py-2 text-sm font-semibold text-white" onClick={() => void loadChildren()}>
          ลองใหม่
        </button>
      </section>
    );
  }

  if (status === "children") {
    return (
      <section className="space-y-5">
        <header>
          <p className="text-sm font-semibold text-[color:var(--color-primary)]">ขั้นตอนที่ 1 จาก 5</p>
          <h1 className="mt-1 text-2xl font-semibold">เริ่มการประเมินพัฒนาการ</h1>
          <p className="mt-2 text-sm text-[color:var(--color-text-muted)]">เลือกเด็กจากรายการที่คุณมีสิทธิ์ดูแล</p>
        </header>
        <div className="workspace-panel divide-y divide-[color:var(--color-border)]">
          {children.length === 0 ? (
            <p className="p-6 text-sm text-[color:var(--color-text-muted)]">ยังไม่มีรายการเด็กที่เข้าถึงได้</p>
          ) : children.map((child) => (
            <div key={child.id} className="flex items-center justify-between gap-4 p-4">
              <div>
                <p className="font-semibold">{child.display_code}</p>
                <p className="mt-1 text-sm text-[color:var(--color-text-muted)]">ภาษาเริ่มต้น: {child.language_context.primary}</p>
              </div>
              <button type="button" className="rounded-lg bg-[color:var(--color-primary)] px-4 py-2 text-sm font-semibold text-white" disabled={busy} onClick={() => void chooseChild(child)}>
                เลือก {child.display_code}
              </button>
            </div>
          ))}
        </div>
      </section>
    );
  }

  if (status === "setup" && selectedChild) {
    return (
      <section className="space-y-5">
        <header>
          <p className="text-sm font-semibold text-[color:var(--color-primary)]">ขั้นตอนที่ 2 จาก 5 · {selectedChild.display_code}</p>
          <h1 className="mt-1 text-2xl font-semibold">ยืนยันข้อมูลก่อนเริ่ม</h1>
          <p className="mt-2 text-sm text-[color:var(--color-text-muted)]">เลือกวัตถุประสงค์และตรวจสอบ consent จากระบบ</p>
        </header>

        {!hasActiveConsent ? (
          <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-amber-950" role="alert">
            <p className="font-semibold">ยังไม่มี consent สำหรับการประเมิน</p>
            <p className="mt-1 text-sm">ต้องยืนยันว่าได้รับ consent ที่เหมาะสมก่อนจึงจะสร้าง assessment ได้</p>
            <label className="mt-4 flex items-start gap-3 text-sm">
              <input type="checkbox" checked={consentConfirmed} onChange={(event) => setConsentConfirmed(event.target.checked)} className="mt-1 h-4 w-4" />
              <span>ยืนยันว่าได้รับ consent แล้ว</span>
            </label>
          </div>
        ) : (
          <div className="rounded-xl border border-emerald-300 bg-emerald-50 p-4 text-emerald-950" role="status">
            <p className="font-semibold">มี consent สำหรับการประเมินแล้ว</p>
            <p className="mt-1 text-sm">ขอบเขต {latestClinicalConsent?.scope_version} · เวอร์ชัน {latestClinicalConsent?.version}</p>
          </div>
        )}

        <div className="workspace-panel p-5">
          <label htmlFor="assessment-purpose" className="text-sm font-semibold">วัตถุประสงค์การประเมิน</label>
          <select id="assessment-purpose" value={purpose} onChange={(event) => setPurpose(event.target.value as AssessmentV2Purpose)} className="mt-2 block w-full rounded-lg border border-[color:var(--color-border)] bg-white px-3 py-3 text-sm">
            {PURPOSES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
          </select>
          <p className="mt-2 text-sm text-[color:var(--color-text-muted)]">{selectedPurpose.description}</p>
        </div>

        {error ? <p className="text-sm text-red-700" role="alert">{error}</p> : null}
        <button type="button" disabled={busy || (!hasActiveConsent && !consentConfirmed)} onClick={() => void createAssessment()} className="rounded-lg bg-[color:var(--color-primary)] px-5 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50">
          {busy ? "กำลังเตรียมการประเมิน…" : hasActiveConsent ? "เริ่มการประเมิน" : "บันทึก consent และเริ่มการประเมิน"}
        </button>

        <section className="workspace-panel p-5" aria-labelledby="assessment-history-heading">
          <h2 id="assessment-history-heading" className="font-semibold">ประวัติการประเมิน</h2>
          {assessments.length === 0 ? <p className="mt-2 text-sm text-[color:var(--color-text-muted)]">ยังไม่มีการประเมินก่อนหน้านี้</p> : (
            <ul className="mt-3 space-y-2 text-sm">
              {assessments.map((assessment) => <li key={assessment.id} className="flex justify-between gap-3"><span>{purposeLabel(assessment.purpose)}</span><span className="text-[color:var(--color-text-muted)]">{stateLabel(assessment.state)}</span></li>)}
            </ul>
          )}
        </section>
      </section>
    );
  }

  if (status === "ready" && capture) {
    return (
      <section className="space-y-5">
        <header>
          <p className="text-sm font-semibold text-[color:var(--color-primary)]">ขั้นตอนที่ 3 จาก 5 · {selectedChild?.display_code}</p>
          <h1 className="mt-1 text-2xl font-semibold">พร้อมบันทึกเสียง</h1>
          <p className="mt-2 text-sm text-[color:var(--color-text-muted)]">ระบบเลือก protocol จากภาษา อายุ และวัตถุประสงค์ที่บันทึกไว้</p>
        </header>
        <div className="workspace-panel p-5">
          <p className="text-sm font-semibold">{capture.protocol?.protocol_version_key}</p>
          <ul className="mt-4 space-y-3">
            {capture.activities.map((activity) => (
              <li key={activity.activity_code} className="rounded-lg border border-[color:var(--color-border)] p-4">
                <div className="flex items-center justify-between gap-3"><span className="font-semibold">{activityLabel(activity.activity_code)}</span><span className="text-sm text-[color:var(--color-text-muted)]">อย่างน้อย {activity.minimum_duration_seconds} วินาที</span></div>
                <p className="mt-1 text-sm text-[color:var(--color-text-muted)]">เป้าหมาย {activity.target_duration_seconds} วินาที {activity.required ? "· กิจกรรมจำเป็น" : "· กิจกรรมเสริม"}</p>
              </li>
            ))}
          </ul>
        </div>
        {error ? <p className="text-sm text-red-700" role="alert">{error}</p> : null}
        <button type="button" disabled={busy} onClick={() => void beginCapture()} className="rounded-lg bg-[color:var(--color-primary)] px-5 py-3 text-sm font-semibold text-white disabled:opacity-50">
          {busy ? "กำลังเตรียมเครื่องบันทึก…" : "เริ่มบันทึกเสียง"}
        </button>
      </section>
    );
  }

  if (status === "complete" && completedAssessment) {
    return (
      <section className="space-y-5">
        <header>
          <p className="text-sm font-semibold text-[color:var(--color-primary)]">ขั้นตอนที่ 5 จาก 5</p>
          <h1 className="mt-1 text-2xl font-semibold">ส่งข้อมูลครบแล้ว</h1>
          <p className="mt-2 text-sm text-[color:var(--color-text-muted)]">ระบบกำลังเตรียมผลการวิเคราะห์เชิงพัฒนาการสำหรับการพิจารณาของนักบำบัด</p>
        </header>
        <div className="rounded-xl border border-emerald-300 bg-emerald-50 p-5 text-emerald-950" role="status">
          <p className="font-semibold">Assessment อยู่ระหว่าง processing</p>
          <p className="mt-1 text-sm">ผลลัพธ์จะต้องผ่านการตรวจสอบและตีความโดยนักบำบัด ไม่ใช่การวินิจฉัยอัตโนมัติ</p>
          <p className="mt-3 text-sm">สถานะปัจจุบัน: {stateLabel(completedAssessment.state)}</p>
        </div>
      </section>
    );
  }

  const activityCount = capture?.activities.length ?? 0;
  const isLastActivity = activeActivityIndex >= activityCount - 1;

  return (
    <section className="space-y-5">
      <header>
        <p className="text-sm font-semibold text-[color:var(--color-primary)]">ขั้นตอนที่ 4 จาก 5 · กิจกรรมที่ {Math.min(activeActivityIndex + 1, activityCount)} จาก {activityCount}</p>
        <h1 className="mt-1 text-2xl font-semibold">บันทึกกิจกรรม</h1>
        <p className="mt-2 text-sm text-[color:var(--color-text-muted)]">อัดเสียงทีละกิจกรรม แล้วอัปโหลดเมื่อพร้อมเพื่อรอตรวจสอบคุณภาพ</p>
      </header>

      {activeActivity ? (
        <>
          <div className="workspace-panel p-5">
            <p className="text-lg font-semibold">{activityLabel(activeActivity.activity_code)}</p>
            <p className="mt-2 text-sm text-[color:var(--color-text-muted)]">
              เป้าหมาย {activeActivity.target_duration_seconds} วินาที · ขั้นต่ำ {activeActivity.minimum_duration_seconds} วินาที
            </p>
            <p className="mt-2 text-sm text-[color:var(--color-text-muted)]">กิจกรรมนี้{activeActivity.required ? "เป็นกิจกรรมจำเป็น" : "เป็นกิจกรรมเสริม"}</p>
          </div>

          <div className="workspace-panel p-5">
            <BrowserAudioRecorder
              key={activeActivity.activity_code}
              initialDurationSeconds={0}
              hadUnsavedRecording={false}
              onMetadataChange={setRecordingMetadata}
              onRecordingReady={handleRecordingReady}
              onRecordingCleared={handleRecordingCleared}
            />
          </div>

          {recordingBlob && uploadStatus !== "uploaded" ? (
            <button
              type="button"
              disabled={busy}
              onClick={() => void uploadCurrentRecording()}
              className="rounded-lg bg-[color:var(--color-primary)] px-5 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
            >
              {busy ? uploadStageLabel(uploadStage) : "อัปโหลดตัวอย่างเสียง"}
            </button>
          ) : null}

          {recordingMetadata?.recordingStatus === "stopped" && uploadStatus === "ready" ? (
            <p className="text-sm text-[color:var(--color-text-muted)]">บันทึกแล้ว {recordingMetadata.durationSeconds} วินาที ตรวจสอบเสียงก่อนอัปโหลดได้</p>
          ) : null}

          {uploadStatus === "uploaded" ? (
            <div className="rounded-xl border border-emerald-300 bg-emerald-50 p-4 text-emerald-950" role="status">
              <p className="font-semibold">อัปโหลดแล้ว รอตรวจสอบคุณภาพ</p>
              <p className="mt-1 text-sm">ไฟล์ถูกส่งเข้ากระบวนการตรวจสอบของระบบแล้ว นักบำบัดจะเห็นผลเมื่อระบบประมวลผลเสร็จ</p>
              {qualityStatus === "ready" && quality ? <p className="mt-3 font-semibold">{qualityLabel(quality.status)}</p> : null}
              {qualityError ? <p className="mt-3 text-sm">{qualityError}</p> : null}
              {quality?.status === "usable" && isLastActivity ? (
                <button type="button" disabled={busy} onClick={() => void completeAssessmentCapture()} className="mt-4 rounded-lg bg-[color:var(--color-primary)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">
                  {busy ? "กำลังส่งข้อมูล…" : "ส่ง assessment เข้า processing"}
                </button>
              ) : null}
              {!isLastActivity ? (
                <button type="button" onClick={continueToNextActivity} className="mt-4 rounded-lg bg-[color:var(--color-primary)] px-4 py-2 text-sm font-semibold text-white">
                  ไปกิจกรรมถัดไป
                </button>
              ) : null}
            </div>
          ) : null}

          {uploadError ? <p className="text-sm text-red-700" role="alert">{uploadError}</p> : null}
          {error ? <p className="text-sm text-red-700" role="alert">{error}</p> : null}
        </>
      ) : (
        <div className="rounded-xl border border-emerald-300 bg-emerald-50 p-4 text-emerald-950" role="status">
          <p className="font-semibold">บันทึกกิจกรรมครบแล้ว</p>
          <p className="mt-1 text-sm">ตัวอย่างเสียงทั้งหมดกำลังรอการตรวจสอบคุณภาพจากระบบ</p>
        </div>
      )}
    </section>
  );
}

function firstPendingActivityIndex(capture: AssessmentV2Capture): number {
  const index = capture.activities.findIndex((activity) => !capture.recordings.some((recording) => (
    recording.activity_code === activity.activity_code
    && (recording.upload_state === "uploaded" || recording.upload_state === "verified")
  )));
  return index === -1 ? capture.activities.length : index;
}

function replaceRecording(recordings: AssessmentV2Recording[], replacement: AssessmentV2Recording): AssessmentV2Recording[] {
  const existingIndex = recordings.findIndex((recording) => recording.id === replacement.id);
  if (existingIndex === -1) return [...recordings, replacement];
  return recordings.map((recording, index) => index === existingIndex ? replacement : recording);
}

function createRecordingIdempotencyKey(): string {
  const randomId = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  return `capture-${randomId}`;
}

function uploadStageLabel(stage: AssessmentRecordingUploadStage | null): string {
  const labels: Record<AssessmentRecordingUploadStage, string> = {
    hashing: "กำลังตรวจสอบไฟล์…",
    creating: "กำลังเตรียมการอัปโหลด…",
    uploading: "กำลังอัปโหลด…",
    finalizing: "กำลังยืนยันการอัปโหลด…",
  };
  return stage ? labels[stage] : "กำลังอัปโหลด…";
}

function qualityLabel(status: AssessmentV2Quality["status"]): string {
  const labels: Record<AssessmentV2Quality["status"], string> = {
    usable: "คุณภาพตัวอย่างผ่านเกณฑ์เบื้องต้น",
    needs_additional_sample: "ตัวอย่างนี้ยังต้องเก็บเพิ่มเติม",
    unavailable: "ยังตรวจสอบคุณภาพตัวอย่างไม่ได้",
    failed: "การตรวจสอบคุณภาพไม่สำเร็จ",
  };
  return labels[status];
}

function purposeLabel(value: AssessmentV2Purpose): string {
  return PURPOSES.find((item) => item.value === value)?.label ?? value;
}

function stateLabel(value: AssessmentV2Assessment["state"]): string {
  const labels: Record<AssessmentV2Assessment["state"], string> = {
    draft: "ฉบับร่าง",
    ready_for_capture: "พร้อมบันทึก",
    capturing: "กำลังบันทึก",
    processing: "กำลังประมวลผล",
    review_required: "รอตรวจสอบ",
    ready_for_clinician: "พร้อมให้นักบำบัดพิจารณา",
    finalized: "เสร็จสิ้น",
    cancelled: "ยกเลิก",
  };
  return labels[value];
}

function activityLabel(value: string): string {
  const labels: Record<string, string> = {
    free_play: "เล่นอิสระ",
    shared_book: "อ่านหนังสือร่วมกัน",
    turn_taking: "ผลัดกันโต้ตอบ",
  };
  return labels[value] ?? value;
}
