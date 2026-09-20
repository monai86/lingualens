"use client";

import { ClinicalPdfReport, type ClinicalReportData } from "@/features/reports/components/clinical-pdf-report";

// Demo/prototype report data — will be replaced with API fetch
const DEMO_REPORT: ClinicalReportData = {
  childName: "น้องออโต้ (Nong Auto)",
  childCode: "CASE-001",
  age: "3 ปี 4 เดือน",
  gender: "ชาย",
  evaluator: "อ.สมศรี รักภาษา, นักอรรถบำบัด",
  date: new Date().toLocaleDateString("th-TH", { year: "numeric", month: "long", day: "numeric" }),
  location: "คลินิกภาษาและการสื่อสาร",

  talkBankScore: 0.82,
  receptiveScore: 0.78,
  expressiveScore: 0.71,

  thaiLsaMetrics: {
    mluWords: 3.42,
    mluMorphemes: 4.05,
    ttr: 0.68,
    totalWords: 48,
    uniqueWords: 33,
    questionCount: 4,
    questionRatio: 0.29,
    negationCount: 2,
    negationRatio: 0.14,
    pronounCount: 6,
    politeParticleCount: 5,
    echolaliaCount: 1,
    turnTakingCount: 12,
    speechRateWpm: 88.5,
  },

  longitudinalSessions: [
    {
      sessionId: "SESS-001",
      date: "01/08/2026",
      mluWords: 2.10,
      ttr: 0.52,
      turnTakingCount: 5,
      politeParticleCount: 1,
      echolaliaCount: 4,
      f0MedianHz: 320.5,
    },
    {
      sessionId: "SESS-002",
      date: "15/08/2026",
      mluWords: 2.85,
      ttr: 0.61,
      turnTakingCount: 8,
      politeParticleCount: 3,
      echolaliaCount: 2,
      f0MedianHz: 312.0,
    },
    {
      sessionId: "SESS-003",
      date: "20/09/2026",
      mluWords: 3.42,
      ttr: 0.68,
      turnTakingCount: 12,
      politeParticleCount: 5,
      echolaliaCount: 1,
      f0MedianHz: 308.2,
    },
  ],

  receptiveSummary:
    "เด็กสามารถเข้าใจคำสั่งง่ายๆ 2 ขั้นตอนได้ดี เช่น \"หยิบตุ๊กตาแล้วเอามาให้ครู\" " +
    "ชี้รูปภาพตามคำบอกได้ถูกต้องประมาณ 80% ของชุดทดสอบ " +
    "ยังมีความยากลำบากในการเข้าใจคำถามเชิงเหตุผล (ทำไม, เพราะอะไร)",

  expressiveSummary:
    "พูดเป็นประโยค 3-4 คำได้ เช่น \"ช้าง ตัว ใหญ่\" \"อยากกิน ข้าว\" " +
    "ใช้คำเชื่อมง่ายๆ ได้บ้าง (แล้วก็, แต่) " +
    "การออกเสียงพยัญชนะต้น ร/ล ยังไม่ชัดเจนตามวัย",

  pragmaticsSummary:
    "สบตาได้ตามวัย ตอบสนองเมื่อถูกเรียกชื่อ " +
    "ผลัดกันพูดได้ดีในกิจกรรมที่ชอบ " +
    "ยังมีข้อจำกัดในการเริ่มบทสนทนาด้วยตนเอง",

  behavioralObservations:
    "ร่วมมือดีตลอดการประเมิน สนใจของเล่นและสื่อที่ใช้ " +
    "มีช่วงสมาธิสั้นเมื่อกิจกรรมเปลี่ยน ต้องให้คำชมเชยเป็นระยะ " +
    "แสดงอารมณ์ผิดหวังเมื่อสื่อสารไม่เข้าใจแต่สามารถปรับตัวได้เมื่อได้รับความช่วยเหลือ",

  recommendations: [
    "ฝึกการเล่าเรื่องตามลำดับเหตุการณ์ โดยใช้ภาพลำดับเรื่อง (Story Sequencing)",
    "เพิ่มกิจกรรมเล่นสมมติ (Pretend Play) เพื่อพัฒนาทักษะการสื่อสาร",
    "ฝึกการออกเสียง ร/ล ผ่านกิจกรรมเลียนเสียง และเกมคำ",
    "แนะนำผู้ปกครองให้ใช้เทคนิค Expansion — ขยายประโยคของเด็กให้ยาวขึ้น",
    "นัดติดตามผลภายใน 3 เดือน เพื่อประเมินพัฒนาการอีกครั้ง",
  ],

  signedAt: new Date().toISOString(),
  hash: "a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890",
  reportVersion: "1.0",
  cuesAcknowledgedAt: new Date().toISOString(),
  cuesAcknowledgedBy: "therapist-demo",
};

export default function ReportPreviewPage() {
  return <ClinicalPdfReport data={DEMO_REPORT} />;
}
