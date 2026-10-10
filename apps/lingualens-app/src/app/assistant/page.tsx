import Link from "next/link";
import { Sparkles, ArrowRight, ShieldCheck, FileText } from "lucide-react";
import { AppShell } from "@/components/app-shell";

export default function AssistantPage() {
  return (
    <AppShell active="Today">
      <div className="mx-auto max-w-3xl py-8">
        <section className="rounded-2xl border border-[color:var(--color-pasa-teal-border)] bg-[color:var(--color-surface-reading)] p-8 shadow-xs">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-[color:var(--color-pasa-teal-soft)] text-[color:var(--color-pasa-teal)]">
            <Sparkles className="h-6 w-6" />
          </div>

          <div className="mt-5">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-800">
              <ShieldCheck className="h-3.5 w-3.5" />
              Integrated Clinical Decision Support
            </span>
            <h1 className="mt-3 text-2xl font-extrabold tracking-tight text-[color:var(--color-text-strong)] sm:text-3xl">
              AI Decision Support has moved to Session Findings
            </h1>
            <p className="mt-3 text-sm leading-relaxed text-[color:var(--color-text-muted)]">
              เพื่อความถูกต้องทางคลินิกและการป้องกันข้อมูลรั่วไหล ระบบ AI Assistant สำหรับวิเคราะห์ตัวชี้วัดภาษาไทย (Thai LSA Pragmatics) และการร่างข้อความรายงาน (Clinical Narrative Drafting) ได้รับการผสานรวมเข้ากับหน้า Session Workspace โดยตรงแล้ว
            </p>
          </div>

          <div className="mt-6 rounded-xl border border-[color:var(--color-border)] bg-[color:var(--color-surface)] p-4 text-xs leading-relaxed text-[color:var(--color-text-muted)]">
            <p className="font-semibold text-[color:var(--color-text-strong)]">
              ฟังก์ชันที่ย้ายไปยัง Session Workspace:
            </p>
            <ul className="mt-2 list-inside list-disc space-y-1">
              <li><strong>AI Clinical Review & Findings:</strong> อยู่ในหน้า Session &gt; Findings พร้อมระบบตรวจสอบความยินยอม (Consent Gates)</li>
              <li><strong>Narrative Drafting for Reports:</strong> อยู่ในหน้า Session &gt; Report พร้อมการบันทึก Audit Log และการลงนามรับรอง</li>
              <li><strong>ความปลอดภัยทางคลินิก:</strong> ข้อมูลประมวลผลผ่าน Backend API ที่มี Consent Authorization ป้องกันการระบุตัวตนเด็ก</li>
            </ul>
          </div>

          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              href="/today"
              className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-[color:var(--color-pasa-teal)] px-5 text-sm font-semibold text-white shadow-xs transition hover:bg-[color:var(--color-pasa-teal-hover)]"
            >
              <span>ไปยังคิวงานวันนี้ (Today Queue)</span>
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href="/sessions/session_demo_001?view=findings"
              className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-[color:var(--color-pasa-teal-border)] bg-[color:var(--color-pasa-teal-soft)] px-5 text-sm font-semibold text-[color:var(--color-pasa-teal)] shadow-2xs transition hover:bg-[color:var(--color-pasa-teal)] hover:text-white"
            >
              <FileText className="h-4 w-4" />
              <span>เปิดดูตัวอย่าง Findings AI Review</span>
            </Link>
          </div>
        </section>
      </div>
    </AppShell>
  );
}
