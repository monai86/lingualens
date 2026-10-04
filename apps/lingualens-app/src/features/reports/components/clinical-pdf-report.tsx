"use client";

import { Printer, ShieldCheck, FileDown, Building2 } from "lucide-react";

export interface ClinicalReportData {
  /* Demographics */
  childName: string;
  childCode?: string;
  age: string;
  gender?: string;
  evaluator: string;
  date: string;
  location?: string;

  /* Assessment Sections */
  receptiveSummary: string;
  expressiveSummary: string;
  pragmaticsSummary?: string;
  behavioralObservations?: string;

  /* Metrics (optional ML-derived scores) */
  talkBankScore?: number;
  receptiveScore?: number;
  expressiveScore?: number;

  /* Thai LSA Quantitative Linguistic Indicators */
  thaiLsaMetrics?: {
    mluWords?: number;
    mluMorphemes?: number;
    ttr?: number;
    totalWords?: number;
    uniqueWords?: number;
    questionCount?: number;
    questionRatio?: number;
    negationCount?: number;
    negationRatio?: number;
    pronounCount?: number;
    politeParticleCount?: number;
    echolaliaCount?: number;
    turnTakingCount?: number;
    speechRateWpm?: number;
  };

  /* Longitudinal Trajectory */
  longitudinalSessions?: Array<{
    sessionId: string;
    date: string;
    mluWords?: number;
    ttr?: number;
    turnTakingCount?: number;
    echolaliaCount?: number;
    politeParticleCount?: number;
    f0MedianHz?: number;
  }>;

  /* Recommendations */
  recommendations?: string[];

  /* Sign-off & Audit */
  signedAt?: string;
  hash?: string;
  reportVersion?: string;
  /** Therapist + date of the server-recorded reviewed-cues acknowledgement. */
  cuesAcknowledgedBy?: string;
  cuesAcknowledgedAt?: string;
}

function ScoreDisplay({ label, score }: { label: string; score?: number }) {
  if (score == null) return null;
  const pct = (score * 100).toFixed(0);
  return (
    <div className="flex items-center justify-between border-b border-slate-200 py-1.5 last:border-0">
      <span className="text-slate-600">{label}</span>
      <span className="font-semibold text-slate-900">{pct}%</span>
    </div>
  );
}

export function ClinicalPdfReport({ data }: { data: ClinicalReportData }) {
  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="min-h-screen bg-[#171717] print:bg-white print:min-h-0">
      {/* Toolbar (hidden when printing) */}
      <div className="sticky top-0 z-10 border-b border-[#2f2f2f] bg-[#212121]/95 backdrop-blur print:hidden">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-3 md:px-8">
          <h1 className="text-lg font-bold text-slate-100">Clinical Assessment Report</h1>
          <div className="flex items-center gap-2">
            <button
              onClick={handlePrint}
              className="flex items-center gap-2 rounded-lg bg-[#10a37f] px-4 py-2 text-sm font-medium text-white shadow-lg hover:bg-[#1a7f64] transition"
            >
              <Printer className="h-4 w-4" />
              Print / Download PDF
            </button>
          </div>
        </div>
      </div>

      {/* A4 Document */}
      <div className="mx-auto max-w-4xl px-4 py-8 md:px-8 print:max-w-none print:px-0 print:py-0">
        <div className="bg-white text-slate-900 shadow-2xl rounded-sm print:shadow-none print:rounded-none">

          {/* ===== PAGE CONTENT ===== */}
          <div className="p-8 md:p-12 print:p-[15mm] space-y-8 print:space-y-6 [print-color-adjust:exact] [-webkit-print-color-adjust:exact]">

            {/* ── Document Header ── */}
            <header className="border-b-2 border-slate-900 pb-5">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2 text-[#10a37f] print:text-emerald-700 mb-1">
                    <Building2 className="h-5 w-5" />
                    <span className="text-xs font-bold uppercase tracking-widest">PasaScope Clinical Suite (ภาษา-สโคป)</span>
                  </div>
                  <h2 className="text-2xl font-bold uppercase tracking-tight text-slate-900 print:text-xl">
                    Speech-Language Assessment Report
                  </h2>
                  <p className="mt-0.5 text-sm font-medium text-slate-500">
                    แบบรายงานผลการประเมินพัฒนาการทางภาษาและการสื่อสาร
                  </p>
                </div>
                <div className="text-right text-xs text-slate-500 shrink-0">
                  <div>Date: {data.date}</div>
                  {data.reportVersion && <div>Version: {data.reportVersion}</div>}
                </div>
              </div>
            </header>

            {/* ── Patient Demographics ── */}
            <section>
              <h3 className="mb-3 text-xs font-bold uppercase tracking-widest text-slate-400 border-b border-slate-200 pb-1">
                ข้อมูลทั่วไป (Patient Demographics)
              </h3>
              <div className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm">
                <div><span className="font-semibold text-slate-700">ชื่อเด็ก:</span> <span className="text-slate-900">{data.childName}</span></div>
                <div><span className="font-semibold text-slate-700">อายุ:</span> <span className="text-slate-900">{data.age}</span></div>
                {data.childCode && (
                  <div><span className="font-semibold text-slate-700">รหัสเด็ก:</span> <span className="text-slate-900">{data.childCode}</span></div>
                )}
                {data.gender && (
                  <div><span className="font-semibold text-slate-700">เพศ:</span> <span className="text-slate-900">{data.gender}</span></div>
                )}
                <div><span className="font-semibold text-slate-700">ผู้ประเมิน:</span> <span className="text-slate-900">{data.evaluator}</span></div>
                <div><span className="font-semibold text-slate-700">วันที่ประเมิน:</span> <span className="text-slate-900">{data.date}</span></div>
                {data.location && (
                  <div className="col-span-2"><span className="font-semibold text-slate-700">สถานที่:</span> <span className="text-slate-900">{data.location}</span></div>
                )}
              </div>
            </section>

            {/* ── Metric Scores (if available) ── */}
            {(data.talkBankScore != null || data.receptiveScore != null || data.expressiveScore != null) && (
              <section>
                <h3 className="mb-3 text-xs font-bold uppercase tracking-widest text-slate-400 border-b border-slate-200 pb-1">
                  คะแนนสรุป (Summary Scores)
                </h3>
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm">
                  <ScoreDisplay label="TalkBank Feature Score" score={data.talkBankScore} />
                  <ScoreDisplay label="Receptive Language" score={data.receptiveScore} />
                  <ScoreDisplay label="Expressive Language" score={data.expressiveScore} />
                </div>
                <p className="mt-1 text-[10px] text-slate-400 italic">
                  Research prototype scores — non-diagnostic. Therapist clinical judgment required.
                </p>
              </section>
            )}

            {/* ── Thai Clinical Language Sample Analysis (Thai LSA) ── */}
            {data.thaiLsaMetrics && (
              <section className="print:break-inside-avoid">
                <h3 className="mb-3 text-xs font-bold uppercase tracking-widest text-slate-400 border-b border-slate-200 pb-1 flex items-center justify-between">
                  <span>ตัวชี้วัดทางภาษาไทยเชิงปริมาณ (Thai Clinical LSA Indicators)</span>
                  <span className="text-[10px] font-normal lowercase text-slate-500">PyThaiNLP Dict / Morphological Analysis</span>
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                  {data.thaiLsaMetrics.mluWords != null && (
                    <div className="rounded border border-slate-200 bg-slate-50/70 p-2.5">
                      <div className="text-slate-500 text-[11px]">ความยาวประโยค (MLU-w)</div>
                      <div className="text-base font-bold text-slate-900 mt-0.5">{data.thaiLsaMetrics.mluWords.toFixed(2)} <span className="text-[10px] font-normal text-slate-500">คำ/ประโยค</span></div>
                      <div className="text-[10px] text-slate-400 mt-0.5">Mean Length of Utterance</div>
                    </div>
                  )}
                  {data.thaiLsaMetrics.ttr != null && (
                    <div className="rounded border border-slate-200 bg-slate-50/70 p-2.5">
                      <div className="text-slate-500 text-[11px]">ความหลากหลายคำศัพท์ (TTR)</div>
                      <div className="text-base font-bold text-slate-900 mt-0.5">{(data.thaiLsaMetrics.ttr * 100).toFixed(1)}%</div>
                      <div className="text-[10px] text-slate-400 mt-0.5">Type-Token Ratio</div>
                    </div>
                  )}
                  {data.thaiLsaMetrics.questionCount != null && (
                    <div className="rounded border border-slate-200 bg-slate-50/70 p-2.5">
                      <div className="text-slate-500 text-[11px]">การริเริ่มคำถาม (Questions)</div>
                      <div className="text-base font-bold text-slate-900 mt-0.5">{data.thaiLsaMetrics.questionCount} <span className="text-[10px] font-normal text-slate-500">ครั้ง</span></div>
                      <div className="text-[10px] text-slate-400 mt-0.5">Initiated Question Particles</div>
                    </div>
                  )}
                  {data.thaiLsaMetrics.negationCount != null && (
                    <div className="rounded border border-slate-200 bg-slate-50/70 p-2.5">
                      <div className="text-slate-500 text-[11px]">การสื่อสารปฏิเสธ (Negations)</div>
                      <div className="text-base font-bold text-slate-900 mt-0.5">{data.thaiLsaMetrics.negationCount} <span className="text-[10px] font-normal text-slate-500">ครั้ง</span></div>
                      <div className="text-[10px] text-slate-400 mt-0.5">Thai Negation Structures</div>
                    </div>
                  )}
                  {data.thaiLsaMetrics.pronounCount != null && (
                    <div className="rounded border border-slate-200 bg-slate-50/70 p-2.5">
                      <div className="text-slate-500 text-[11px]">การใช้สรรพนาม (Pronouns)</div>
                      <div className="text-base font-bold text-slate-900 mt-0.5">{data.thaiLsaMetrics.pronounCount} <span className="text-[10px] font-normal text-slate-500">ครั้ง</span></div>
                      <div className="text-[10px] text-slate-400 mt-0.5">Self/Other Reference Markers</div>
                    </div>
                  )}
                  {data.thaiLsaMetrics.politeParticleCount != null && (
                    <div className="rounded border border-slate-200 bg-slate-50/70 p-2.5">
                      <div className="text-slate-500 text-[11px]">คำลงท้ายสุภาพ (Polite)</div>
                      <div className="text-base font-bold text-slate-900 mt-0.5">{data.thaiLsaMetrics.politeParticleCount} <span className="text-[10px] font-normal text-slate-500">ครั้ง</span></div>
                      <div className="text-[10px] text-slate-400 mt-0.5">Pragmatic Politeness Tokens</div>
                    </div>
                  )}
                  {data.thaiLsaMetrics.echolaliaCount != null && (
                    <div className="rounded border border-slate-200 bg-slate-50/70 p-2.5">
                      <div className="text-slate-500 text-[11px]">การพูดซ้ำทันที (Repetition)</div>
                      <div className="text-base font-bold text-slate-900 mt-0.5">{data.thaiLsaMetrics.echolaliaCount} <span className="text-[10px] font-normal text-slate-500">ครั้ง</span></div>
                      <div className="text-[10px] text-slate-400 mt-0.5">Immediate Echo Turns</div>
                    </div>
                  )}
                  {data.thaiLsaMetrics.turnTakingCount != null && (
                    <div className="rounded border border-slate-200 bg-slate-50/70 p-2.5">
                      <div className="text-slate-500 text-[11px]">การสลับบทสนทนา (Turn-Taking)</div>
                      <div className="text-base font-bold text-slate-900 mt-0.5">{data.thaiLsaMetrics.turnTakingCount} <span className="text-[10px] font-normal text-slate-500">รอบ</span></div>
                      <div className="text-[10px] text-slate-400 mt-0.5">Conversational Exchange Turns</div>
                    </div>
                  )}
                </div>
                <p className="mt-2 text-[10px] text-slate-400 italic">
                  การวิเคราะห์ตัวอย่างภาษาพูด (LSA) ด้วยระบบประมวลผลภาษาธรรมชาติภาษาไทย สำหรับเป็นข้อมูลประกอบการวินิจฉัยของนักอรรถบำบัด
                </p>
              </section>
            )}

            {/* ── Assessment Findings ── */}
            <section className="space-y-5 print:break-inside-avoid">
              <h3 className="mb-3 text-xs font-bold uppercase tracking-widest text-slate-400 border-b border-slate-200 pb-1">
                ผลการประเมิน (Assessment Findings)
              </h3>

              <div>
                <h4 className="font-bold text-sm text-slate-800 mb-1">1. การเข้าใจภาษา (Receptive Language)</h4>
                <p className="text-sm text-slate-700 leading-relaxed pl-4">{data.receptiveSummary}</p>
              </div>

              <div>
                <h4 className="font-bold text-sm text-slate-800 mb-1">2. การแสดงออกทางภาษา (Expressive Language)</h4>
                <p className="text-sm text-slate-700 leading-relaxed pl-4">{data.expressiveSummary}</p>
              </div>

              {data.pragmaticsSummary && (
                <div>
                  <h4 className="font-bold text-sm text-slate-800 mb-1">3. การสื่อสารตามบริบทสังคม (Pragmatics)</h4>
                  <p className="text-sm text-slate-700 leading-relaxed pl-4">{data.pragmaticsSummary}</p>
                </div>
              )}

              {data.behavioralObservations && (
                <div>
                  <h4 className="font-bold text-sm text-slate-800 mb-1">4. พฤติกรรมและการตอบสนอง (Behavioral Observations)</h4>
                  <p className="text-sm text-slate-700 leading-relaxed pl-4">{data.behavioralObservations}</p>
                </div>
              )}
            </section>

            {/* ── Longitudinal Trajectory ── */}
            {data.longitudinalSessions && data.longitudinalSessions.length > 1 && (
              <section className="print:break-inside-avoid space-y-2">
                <h3 className="mb-2 text-xs font-bold uppercase tracking-widest text-slate-400 border-b border-slate-200 pb-1 flex items-center justify-between">
                  <span>ติดตามพัฒนาการข้ามเซสชัน (Longitudinal Assessment Trajectory)</span>
                  <span className="text-[10px] font-normal text-slate-500 normal-case">{data.longitudinalSessions.length} เซสชัน</span>
                </h3>
                <div className="overflow-x-auto rounded border border-slate-200">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="bg-slate-50 border-b border-slate-200 text-slate-700 font-semibold">
                        <th className="py-2 px-2.5">วันที่</th>
                        <th className="py-2 px-2.5">Session</th>
                        <th className="py-2 px-2.5 text-right">MLU-w (คำ)</th>
                        <th className="py-2 px-2.5 text-right">TTR</th>
                        <th className="py-2 px-2.5 text-right">Turn-Taking</th>
                        <th className="py-2 px-2.5 text-right">คำสุภาพ</th>
                        <th className="py-2 px-2.5 text-right">Echolalia</th>
                        <th className="py-2 px-2.5 text-right">Pitch F0 (Hz)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {data.longitudinalSessions.map((s, idx) => (
                        <tr key={s.sessionId} className={idx === (data.longitudinalSessions?.length ?? 0) - 1 ? "bg-teal-50/30 font-semibold" : ""}>
                          <td className="py-1.5 px-2.5 whitespace-nowrap">{s.date}</td>
                          <td className="py-1.5 px-2.5 font-mono text-[11px] text-slate-600">{s.sessionId}</td>
                          <td className="py-1.5 px-2.5 text-right font-mono">{s.mluWords != null ? s.mluWords.toFixed(2) : "-"}</td>
                          <td className="py-1.5 px-2.5 text-right font-mono">{s.ttr != null ? `${(s.ttr * 100).toFixed(0)}%` : "-"}</td>
                          <td className="py-1.5 px-2.5 text-right font-mono">{s.turnTakingCount != null ? s.turnTakingCount : "-"}</td>
                          <td className="py-1.5 px-2.5 text-right font-mono">{s.politeParticleCount != null ? s.politeParticleCount : "-"}</td>
                          <td className="py-1.5 px-2.5 text-right font-mono">{s.echolaliaCount != null ? s.echolaliaCount : "-"}</td>
                          <td className="py-1.5 px-2.5 text-right font-mono">{s.f0MedianHz != null ? s.f0MedianHz : "-"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            )}

            {/* ── Recommendations ── */}
            {data.recommendations && data.recommendations.length > 0 && (
              <section className="print:break-inside-avoid">
                <h3 className="mb-3 text-xs font-bold uppercase tracking-widest text-slate-400 border-b border-slate-200 pb-1">
                  ข้อเสนอแนะ (Clinical Recommendations)
                </h3>
                <ul className="list-disc pl-8 text-sm text-slate-700 space-y-1.5 leading-relaxed">
                  {data.recommendations.map((rec, i) => (
                    <li key={i}>{rec}</li>
                  ))}
                </ul>
              </section>
            )}

            {/* ── Sign-Off & Audit ── */}
            <footer className="mt-12 pt-6 border-t-2 border-slate-900 print:break-inside-avoid">
              <div className="flex items-end justify-between">
                {/* Hash verification */}
                {data.hash && (
                  <div className="flex items-center gap-2 text-[10px] text-slate-400 font-mono">
                    <ShieldCheck className="h-4 w-4 text-emerald-600 print:text-emerald-800" />
                    <div>
                      <div>SHA-256 Verified Snapshot</div>
                      <div className="mt-0.5">{data.hash.slice(0, 32)}...</div>
                      {data.signedAt && <div>Signed: {data.signedAt}</div>}
                      {data.cuesAcknowledgedAt && (
                        <div className="mt-0.5">
                          Reviewed cues acknowledged: {data.cuesAcknowledgedBy ?? "Therapist"} — {new Date(data.cuesAcknowledgedAt).toLocaleDateString()}
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Signature block */}
                <div className="text-center text-sm">
                  <div className="mb-1 h-[1px] w-52 bg-slate-400" />
                  <div className="font-semibold text-slate-800">{data.evaluator}</div>
                  <div className="text-xs text-slate-500">นักอรรถบำบัด / Speech-Language Pathologist</div>
                  <div className="text-[10px] text-slate-400 mt-0.5">{data.date}</div>
                </div>
              </div>
            </footer>
          </div>
        </div>
      </div>

      {/* Print CSS */}
      <style
        dangerouslySetInnerHTML={{
          __html: `
            @media print {
              @page {
                size: A4 portrait;
                margin: 0;
              }
              body {
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
              }
              .print\\:hidden { display: none !important; }
            }
          `,
        }}
      />
    </div>
  );
}
