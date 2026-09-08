"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

import {
  AssessmentV2Client,
  type AssessmentV2DevelopmentalDomain,
  type AssessmentV2DomainProfile,
  type AssessmentV2EvidenceProfile,
} from "@/services/assessment-v2-client";

export type AssessmentEvidenceClient = Pick<AssessmentV2Client, "getEvidence">;

type AssessmentEvidenceWorkspaceProps = {
  assessmentId: string;
  client?: AssessmentEvidenceClient;
};

const defaultClient = new AssessmentV2Client();

export function AssessmentEvidenceWorkspace({
  assessmentId,
  client = defaultClient,
}: AssessmentEvidenceWorkspaceProps) {
  const [profile, setProfile] = useState<AssessmentV2EvidenceProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const loadEvidence = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      setProfile(await client.getEvidence(assessmentId));
    } catch {
      setProfile(null);
      setError(true);
    } finally {
      setLoading(false);
    }
  }, [assessmentId, client]);

  useEffect(() => {
    void loadEvidence();
  }, [loadEvidence]);

  if (loading) {
    return (
      <section className="workspace-panel p-6" aria-busy="true">
        <p>กำลังโหลดผลหลักฐาน…</p>
      </section>
    );
  }

  if (error || !profile) {
    return (
      <section className="workspace-panel p-6" role="alert">
        <h1 className="text-xl font-semibold">ไม่สามารถโหลดผลหลักฐานได้</h1>
        <p className="mt-2 text-sm text-[color:var(--color-text-muted)]">
          ระบบยังอ่านผลจาก FastAPI ไม่ได้ ผลลัพธ์จะไม่ถูกสร้างขึ้นในเบราว์เซอร์
        </p>
        <button
          type="button"
          className="mt-4 rounded-lg bg-[color:var(--color-primary)] px-4 py-2 text-sm font-semibold text-white"
          onClick={() => void loadEvidence()}
        >
          ลองใหม่
        </button>
      </section>
    );
  }

  const isStale = profile.state === "stale";

  return (
    <section className="space-y-5">
      <header>
        <p className="text-sm font-semibold text-[color:var(--color-primary)]">ขั้นตอนที่ 5 จาก 5</p>
        <h1 className="mt-1 text-2xl font-semibold">โปรไฟล์พัฒนาการเชิงพรรณนา</h1>
        <p className="mt-2 text-sm text-[color:var(--color-text-muted)]">
          แสดงสิ่งที่วัดได้ แหล่งข้อมูล และข้อจำกัด เพื่อประกอบการพิจารณาของนักบำบัด
        </p>
      </header>

      {isStale ? (
        <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-amber-950" role="alert">
          <p className="font-semibold">ข้อมูลเดิมไม่เป็นปัจจุบัน</p>
          <p className="mt-1 text-sm">ต้องทบทวน transcript หรือประมวลผลใหม่ก่อนใช้ผลนี้ประกอบการพิจารณา</p>
          <Link
            href={`/assessments/${encodeURIComponent(assessmentId)}/transcript`}
            className="mt-3 inline-flex rounded-lg border border-amber-800 px-3 py-2 text-sm font-semibold"
          >
            เปิดหน้า transcript review
          </Link>
        </div>
      ) : null}

      <div className="rounded-xl border border-sky-200 bg-sky-50 p-4 text-sky-950" role="status">
        <p className="font-semibold">สถานะข้อมูล: {evidenceStateLabel(profile.state)}</p>
        <p className="mt-1 text-sm">ผลนี้เป็น decision support เท่านั้น และต้องอ่านร่วมกับข้อมูลทางคลินิกอื่น</p>
      </div>

      <section className="workspace-panel p-5" aria-labelledby="developmental-domains-heading">
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <h2 id="developmental-domains-heading" className="text-lg font-semibold">ประเด็นพัฒนาการตามโดเมน</h2>
          <span className="text-sm text-[color:var(--color-text-muted)]">ข้อมูลจาก run เวอร์ชัน {profile.version}</span>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {profile.domains.map((domain) => <DomainCard key={domain.domain} domain={domain} />)}
        </div>
      </section>

      <section className="workspace-panel p-5" aria-labelledby="measured-features-heading">
        <h2 id="measured-features-heading" className="text-lg font-semibold">ฟีเจอร์ที่สกัดได้</h2>
        {profile.features.length === 0 ? (
          <p className="mt-3 text-sm text-[color:var(--color-text-muted)]">ยังไม่มีค่าที่ใช้ได้ในช่องนี้</p>
        ) : (
          <dl className="mt-4 grid gap-3 sm:grid-cols-2">
            {profile.features.map((feature) => (
              <div key={feature.key} className="rounded-lg border border-[color:var(--color-border)] p-3">
                <dt className="text-sm font-semibold">{feature.key}</dt>
                <dd className="mt-1 text-lg">{formatFeatureValue(feature.value)} {feature.unit}</dd>
                {feature.limitation ? <p className="mt-1 text-xs text-[color:var(--color-text-muted)]">{feature.limitation}</p> : null}
                <p className="mt-2 text-xs text-[color:var(--color-text-muted)]">สถานะ: {evidenceStateLabel(feature.state)}</p>
              </div>
            ))}
          </dl>
        )}
      </section>

      <details className="workspace-panel p-5">
        <summary className="cursor-pointer font-semibold">ดู provenance และข้อจำกัดของการประมวลผล</summary>
        <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
          <div><dt className="text-[color:var(--color-text-muted)]">Protocol</dt><dd>{profile.provenance.protocol_version_key}</dd></div>
          <div><dt className="text-[color:var(--color-text-muted)]">Feature schema</dt><dd>{profile.provenance.feature_schema_version}</dd></div>
          <div><dt className="text-[color:var(--color-text-muted)]">Pipeline</dt><dd>{profile.provenance.pipeline_version}</dd></div>
          <div><dt className="text-[color:var(--color-text-muted)]">Input checksum</dt><dd className="break-all">{profile.provenance.input_sha256}</dd></div>
        </dl>
        {profile.limitations.length > 0 ? (
          <ul className="mt-4 list-disc space-y-1 pl-5 text-sm text-[color:var(--color-text-muted)]">
            {profile.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}
          </ul>
        ) : null}
      </details>
    </section>
  );
}

function DomainCard({ domain }: { domain: AssessmentV2DomainProfile }) {
  return (
    <article className="rounded-xl border border-[color:var(--color-border)] p-4">
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-semibold">{domainLabel(domain.domain)}</h3>
        <span className="rounded-full bg-[color:var(--color-surface-muted)] px-2 py-1 text-xs font-semibold">
          {domainStatusLabel(domain.status)}
        </span>
      </div>
      <p className="mt-2 text-sm text-[color:var(--color-text-muted)]">{domain.summary}</p>
      {domain.supporting_features.length > 0 ? (
        <p className="mt-3 text-xs">ข้อมูลสนับสนุน: {domain.supporting_features.join(", ")}</p>
      ) : null}
      {domain.conflicting_features.length > 0 ? (
        <p className="mt-1 text-xs text-amber-800">ข้อมูลที่ต้องพิจารณาร่วม: {domain.conflicting_features.join(", ")}</p>
      ) : null}
      {domain.limitations.length > 0 ? (
        <p className="mt-2 text-xs text-[color:var(--color-text-muted)]">ข้อจำกัด: {domain.limitations.join(" ")}</p>
      ) : null}
    </article>
  );
}

function formatFeatureValue(value: boolean | number | string | null): string {
  if (value === null) return "ไม่มีค่า";
  if (typeof value === "boolean") return value ? "ใช่" : "ไม่ใช่";
  return String(value);
}

function evidenceStateLabel(value: string): string {
  const labels: Record<string, string> = {
    pending: "รอประมวลผล",
    processing: "กำลังประมวลผล",
    completed: "พร้อมอ่าน",
    needs_review: "ต้องทบทวน",
    insufficient_data: "ข้อมูลยังไม่พอ",
    unavailable: "ยังใช้ไม่ได้",
    failed: "ประมวลผลไม่สำเร็จ",
    stale: "ไม่เป็นปัจจุบัน",
  };
  return labels[value] ?? value;
}

function domainLabel(value: AssessmentV2DevelopmentalDomain): string {
  const labels: Record<AssessmentV2DevelopmentalDomain, string> = {
    expressive_language: "ภาษาแสดงออก",
    speech_clarity_production: "ความชัดและการผลิตเสียงพูด",
    conversational_interaction: "การโต้ตอบสนทนา",
    social_communication: "การสื่อสารทางสังคม",
    repetitive_language: "รูปแบบภาษาซ้ำ",
    prosody_temporal_organization: "จังหวะและทำนองเสียง",
    evidence_quality_sufficiency: "คุณภาพและความเพียงพอของข้อมูล",
  };
  return labels[value];
}

function domainStatusLabel(value: AssessmentV2DomainProfile["status"]): string {
  const labels: Record<AssessmentV2DomainProfile["status"], string> = {
    descriptive_only: "เชิงพรรณนา",
    within_reference_band: "อยู่ในช่วงอ้างอิง",
    outside_reference_band: "นอกช่วงอ้างอิง",
    attention_suggested: "ควรพิจารณาเพิ่ม",
    insufficient_data: "ข้อมูลไม่เพียงพอ",
    reference_unavailable: "ยังไม่มีช่วงอ้างอิง",
    not_assessed: "ยังไม่ได้ประเมิน",
  };
  return labels[value];
}
