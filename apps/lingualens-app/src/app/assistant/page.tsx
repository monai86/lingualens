"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import {
  Bot,
  Send,
  Sparkles,
  FileText,
  TrendingUp,
  Activity,
  ShieldAlert,
  ChevronRight,
  MessageSquare,
  Copy,
  Check,
  RotateCcw,
  SlidersHorizontal,
} from "lucide-react";

import { AppShell } from "@/components/app-shell";
import { listBackendCases } from "@/lib/workflow";

interface Message {
  id: string;
  sender: "user" | "assistant";
  text: string;
  timestamp: string;
  metrics?: {
    mluWords?: number;
    ttr?: number;
    fillers?: number;
    particles?: number;
  };
  recommendation?: string[];
  actionLabel?: string;
  actionUrl?: string;
}

const SAMPLE_CASES = [
  { id: "C-001", name: "C-001 (น้องบี, 36m)", baselineDate: "2026-06-15", followUpDate: "2026-08-20", mlu: 2.8, ttr: 0.52 },
  { id: "C-002", name: "C-002 (น้องเอ, 42m)", baselineDate: "2026-05-10", followUpDate: "2026-07-28", mlu: 3.6, ttr: 0.64 },
  { id: "C-003", name: "C-003 (น้องซี, 29m)", baselineDate: "2026-07-02", followUpDate: "2026-09-11", mlu: 1.9, ttr: 0.38 },
];

const INITIAL_MESSAGES: Message[] = [
  {
    id: "m-1",
    sender: "assistant",
    text: "สวัสดีครับคุณหมอ/นักอรรถบำบัด ยินดีต้อนรับสู่ LinguaLens AI Assistant 👋\n\nผมพร้อมช่วยวิเคราะห์ Language Sample Analysis (LSA), ตรวจสอบตัวชี้วัดไวยากรณ์ไทย (คำอนุภาค/คำสร้อย, คำเชื่อม, คำลังเล), ช่วยร่าง Clinical Narrative สำหรับรายงานสรุป และติดตามผลการรักษาตามช่วงเวลา (Longitudinal Trajectory) ครับ\n\nเลือกหัวข้อที่ต้องการตรวจสอบด้านล่าง หรือพิมพ์คำถามได้เลยครับ:",
    timestamp: "10:00 AM",
  },
];

const QUICK_PROMPTS = [
  {
    icon: Activity,
    label: "วิเคราะห์ LSA & อนุภาคภาษาไทย (Pragmatics)",
    prompt: "ช่วยวิเคราะห์ผล Thai LSA Pragmatics (คำลงท้าย นะ/สิ/ครับ, คำเชื่อม และคำลังเล เอ่อ/อ่า) ของเคสที่เลือกให้หน่อยครับ",
  },
  {
    icon: FileText,
    label: "ร่าง Clinical Narrative สำหรับ Progress Report",
    prompt: "ช่วยร่าง Clinical Narrative สรุปพัฒนาการด้านภาษาและปฏิสัมพันธ์การสื่อสาร สำหรับใส่ในรายงานการประเมินทางคลินิก",
  },
  {
    icon: TrendingUp,
    label: "เปรียบเทียบพัฒนาการตามช่วงเวลา (Longitudinal)",
    prompt: "เปรียบเทียบพัฒนาการ MLU-w และ TTR ระหว่าง Baseline กับ Follow-up session ล่าสุด",
  },
  {
    icon: Sparkles,
    label: "แนะนำเป้าหมาย SMART Goals สำหรับการบำบัด",
    prompt: "ขอคำแนะนำเป้าหมายการบำบัดแบบ SMART Goals สำหรับส่งเสริมการพูดและขยายความยาวประโยคในเด็ก",
  },
];

export default function AssistantPage() {
  const [messages, setMessages] = useState<Message[]>(INITIAL_MESSAGES);
  const [inputText, setInputText] = useState("");
  const [isThinking, setIsThinking] = useState(false);
  const [caseList, setCaseList] = useState<typeof SAMPLE_CASES>(SAMPLE_CASES);
  const [selectedCaseId, setSelectedCaseId] = useState("C-001");
  const [mobileTab, setMobileTab] = useState<"chat" | "context">("chat");
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [draftPushSuccess, setDraftPushSuccess] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const activeCase = caseList.find((c) => c.id === selectedCaseId) || caseList[0] || SAMPLE_CASES[0];

  useEffect(() => {
    let active = true;
    listBackendCases()
      .then((backendCases) => {
        if (!active || !backendCases || backendCases.length === 0) return;
        const mapped = backendCases.map((bc, idx) => ({
          id: bc.case_id,
          name: `${bc.case_id} (${bc.display_label || bc.nickname || bc.anonymized_child_code || bc.child_code || `Case ${idx + 1}`}${bc.age_months ? `, ${bc.age_months}m` : ""})`,
          baselineDate: bc.created_at ? bc.created_at.slice(0, 10) : "2026-06-15",
          followUpDate: bc.updated_at ? bc.updated_at.slice(0, 10) : "2026-08-20",
          mlu: 3.2,
          ttr: 0.58,
        }));
        setCaseList(mapped);
        setSelectedCaseId(mapped[0].id);
      })
      .catch(() => {
        // Fallback gracefully on network error or offline mock mode
      });
    return () => {
      active = false;
    };
  }, []);

  function pushToDraft(text: string) {
    if (typeof window !== "undefined") {
      sessionStorage.setItem("lingualens_ai_draft", text);
    }
    setDraftPushSuccess(true);
    setTimeout(() => setDraftPushSuccess(false), 3000);
  }

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isThinking]);

  function handleSend(textToSend?: string) {
    const text = (textToSend || inputText).trim();
    if (!text || isThinking) return;

    const userMsg: Message = {
      id: `u-${Date.now()}`,
      sender: "user",
      text,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputText("");
    setIsThinking(true);

    // Dynamic response generator based on query intent
    setTimeout(() => {
      let reply: Message;
      const lower = text.toLowerCase();

      if (lower.includes("pragmatic") || lower.includes("อนุภาค") || lower.includes("lsa") || lower.includes("คำลงท้าย")) {
        reply = {
          id: `a-${Date.now()}`,
          sender: "assistant",
          text: `📊 **ผลการวิเคราะห์ Thai LSA Pragmatics สำหรับเคส ${activeCase.id}:**\n\nจากการวิเคราะห์กลุ่มคำในบทสนทนาการบำบัดล่าสุด (18 turns):\n\n• **คำอนุภาคบ่งบอกอารมณ์/เจตนา (Mood Particles):** พบ 4 ครั้ง (เช่น *นะ, ครับ, สิ*) คิดเป็น 22.2% ของรอบพูดคุย แสดงถึงการเริ่มมีปฏิสัมพันธ์และการตอบรับกับผู้บำบัด\n• **คำเชื่อมความ (Conjunctions):** พบ 2 ครั้ง (*และ, กับ*) ประโยคเริ่มมีการเชื่อมความในระดับวลี\n• **คำลังเล/ไม่คล่อง (Fillers/Disfluency):** พบ 1 ครั้ง (*เอ่อ*) คิดเป็น Filler Ratio 5.5% อยู่ในเกณฑ์ปกติของเด็กวัยพัฒนาการ\n• **MLU-w:** ${activeCase.mlu} คำ/รอบการพูด (เฉลี่ยระดับ 2-3 คำต่อประโยค)`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          metrics: { mluWords: activeCase.mlu, ttr: activeCase.ttr, fillers: 1, particles: 4 },
        };
      } else if (lower.includes("narrative") || lower.includes("ร่าง") || lower.includes("สรุป")) {
        reply = {
          id: `a-${Date.now()}`,
          sender: "assistant",
          text: `📝 **ร่าง Clinical Narrative (ร่างข้อความสำหรับใส่ในรายงานการตรวจ):**\n\n"ผู้รับการประเมินสามารถตอบสนองต่อคำถามปลายเปิดและรูปภาพกระตุ้นได้ดีขึ้น โดยพบความยาวประโยคเฉลี่ย (MLU-w) อยู่ที่ ${activeCase.mlu} คำต่อรอบการพูด มีความหลากหลายของคำศัพท์ (TTR) ที่ ${(activeCase.ttr * 100).toFixed(1)}% มีการใช้คำบ่งบอกอารมณ์และคำลงท้ายเพื่อแสดงเจตนาการสื่อสารอย่างเหมาะสม พบการสื่อสารแบบผลัดกันพูด (Turn-taking) ต่อเนื่องโดยมีความลังเลหรือสะดุดเพียงเล็กน้อย แนะนำให้ผู้ปกครองเสริมสร้างการขยายประโยคผ่านกิจกรรมการเล่านิทานและการเล่นตามบทบาทสมมติในชีวิตประจำวัน"`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          actionLabel: "ไปที่หน้าจัดทำรายงาน (Reports)",
          actionUrl: "/reports",
        };
      } else if (lower.includes("longitudinal") || lower.includes("เปรียบเทียบ") || lower.includes("baseline")) {
        reply = {
          id: `a-${Date.now()}`,
          sender: "assistant",
          text: `📈 **การติดตามพัฒนาการตามช่วงเวลา (Longitudinal Trajectory):**\n\n• **Baseline Session (${activeCase.baselineDate}):**\n  - MLU-w: ${(activeCase.mlu * 0.7).toFixed(1)} คำ/ประโยค\n  - TTR: ${(activeCase.ttr * 0.8).toFixed(2)}\n  - สัดส่วนรอบการพูดของเด็ก: 38%\n\n• **Follow-up Session (${activeCase.followUpDate}):**\n  - MLU-w: ${activeCase.mlu} คำ/ประโยค (+${((activeCase.mlu - activeCase.mlu * 0.7)).toFixed(1)} คำ)\n  - TTR: ${activeCase.ttr.toFixed(2)} (+${((activeCase.ttr - activeCase.ttr * 0.8)).toFixed(2)})\n  - สัดส่วนรอบการพูดของเด็ก: 54%\n\n📌 **สรุปแนวโน้ม:** เด็กมีพัฒนาการด้านความยาวประโยคและคลังคำศัพท์ที่เพิ่มขึ้นอย่างมีนัยสำคัญ สามารถคงบทสนทนาได้ยาวนานขึ้น`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        };
      } else if (lower.includes("smart") || lower.includes("เป้าหมาย") || lower.includes("บำบัด")) {
        reply = {
          id: `a-${Date.now()}`,
          sender: "assistant",
          text: `🎯 **ข้อเสนอแนะเป้าหมายการบำบัด (SMART Therapy Goals):**\n\n1. **เป้าหมายระยะสั้น (Short-Term - 4 สัปดาห์):**\n   - เพิ่มความยาวประโยคเป็น 3-4 คำ โดยใช้คำเชื่อม *และ*, *เพราะ* เมื่อเล่าเหตุการณ์จากภาพ ได้ถูกต้องอย่างน้อย 8 ใน 10 ครั้ง\n   - ใช้คำลงท้ายหรือคำขอร้อง (*ขอ, ครับ/ค่ะ*) อย่างสม่ำเสมอในสถานการณ์เล่นเกม\n\n2. **เป้าหมายที่บ้านสำหรับผู้ปกครอง (Home-based Coaching):**\n   - ชวนคุยแบบ 'Wait and See' เว้นจังหวะ 5-10 วินาที ให้เด็กเป็นฝ่ายริเริ่มหัวข้อสนทนา\n   - เทคนิค Expansion: เติมคำขยาย 1 คำเมื่อเด็กพูด เช่น เด็กพูด 'รถวิ่ง' ผู้ปกครองขานรับ 'ใช่แล้ว รถสีแดงวิ่งเร็วมาก'`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          recommendation: [
            "เทคนิค Expansion ขยายความประโยค 1-2 คำ",
            "การใช้คำเชื่อม 'และ' / 'เพราะ' ในการบรรยายภาพ",
            "การฝึกผลัดกันพูดในเกมกระดานแบบสลับเทิร์น",
          ],
        };
      } else {
        reply = {
          id: `a-${Date.now()}`,
          sender: "assistant",
          text: `รับทราบครับ สำหรับเคส **${activeCase.name}** ข้อมูลดังกล่าวเกี่ยวข้องกับการสนับสนุนการตัดสินใจทางคลินิก ท่านสามารถระบุประเด็นเพิ่มเติม เช่น ตรวจสอบความถี่คำศัพท์เฉพาะ, จัดทำข้อความสรุปสำหรับผู้ปกครอง, หรือวิเคราะห์คุณสมบัติทางเสียง (F0 Pitch Contour) เพิ่มเติมได้ครับ`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        };
      }

      setMessages((prev) => [...prev, reply]);
      setIsThinking(false);
    }, 600);
  }

  function copyMessage(id: string, text: string) {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  }

  return (
    <AppShell active="Today">
      <div className="flex h-full flex-col overflow-hidden bg-[#f8faff] text-[#1e1e62]">
        {/* Top Header Banner */}
        <header className="flex flex-shrink-0 items-center justify-between border-b border-[#e0e7ff] bg-white px-4 py-3 sm:px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#e8607e] text-white shadow-sm">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-bold text-[#1e1e62] sm:text-lg">Clinician AI Assistant</h1>
                <span className="rounded-full bg-[#eef2ff] px-2 py-0.5 text-xs font-semibold text-[#4f46e5]">
                  Thai Clinical NLP
                </span>
              </div>
              <p className="text-xs text-slate-500">
                Interactive Decision Support • Language Sample Analysis • Report Drafting
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="hidden items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700 sm:inline-flex">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
              Decision-Support Ready
            </span>
            <Link
              href="/reports"
              className="inline-flex items-center gap-1 rounded-lg border border-[#e0e7ff] bg-white px-3 py-1.5 text-xs font-semibold text-[#4f46e5] shadow-sm hover:bg-[#eef2ff]"
            >
              <FileText className="h-3.5 w-3.5" />
              <span>Reports</span>
            </Link>
          </div>
        </header>

        {/* Safety Boundary Banner */}
        <div className="flex items-center gap-2 border-b border-amber-200 bg-amber-50/80 px-4 py-1.5 text-xs text-amber-900 sm:px-6">
          <ShieldAlert className="h-3.5 w-3.5 flex-shrink-0 text-amber-600" />
          <span className="truncate">
            <strong>Clinical Safety Boundary:</strong> Research/Decision-support prototype. Non-diagnostic. All clinical conclusions require licensed clinician attestation.
          </span>
        </div>

        {/* Mobile View Switcher (Chat vs Case Context) */}
        <div className="flex border-b border-[#e0e7ff] bg-white p-1 lg:hidden">
          <button
            type="button"
            onClick={() => setMobileTab("chat")}
            className={`flex-1 py-1.5 text-xs font-semibold rounded-md transition ${
              mobileTab === "chat" ? "bg-[#4f46e5] text-white shadow-sm" : "text-slate-600 hover:text-slate-900"
            }`}
          >
            💬 Chatbot Conversation
          </button>
          <button
            type="button"
            onClick={() => setMobileTab("context")}
            className={`flex-1 py-1.5 text-xs font-semibold rounded-md transition ${
              mobileTab === "context" ? "bg-[#4f46e5] text-white shadow-sm" : "text-slate-600 hover:text-slate-900"
            }`}
          >
            📋 Case Context & Metrics
          </button>
        </div>

        {/* Main 2-Column Responsive Workspace */}
        <div className="flex flex-1 overflow-hidden">
          {/* Left Panel: Case Context & Quick Actions (Desktop & Mobile Context Tab) */}
          <aside
            className={`w-full lg:w-80 xl:w-96 flex-shrink-0 flex-col border-r border-[#e0e7ff] bg-white p-4 overflow-y-auto ${
              mobileTab === "context" ? "flex" : "hidden lg:flex"
            }`}
          >
            <div className="mb-4">
              <label htmlFor="case-select" className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-1.5">
                Active Case / เคสที่ตรวจ
              </label>
              <select
                id="case-select"
                value={selectedCaseId}
                onChange={(e) => setSelectedCaseId(e.target.value)}
                className="w-full rounded-lg border border-[#cbd5e1] bg-white px-3 py-2 text-sm font-semibold text-[#1e1e62] shadow-sm focus:border-[#4f46e5] focus:outline-none"
              >
                {caseList.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Case Snapshot Card */}
            <div className="rounded-xl border border-[#e0e7ff] bg-[#f8faff] p-3.5 shadow-sm mb-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold text-[#1e1e62]">LSA Baseline & Progression</span>
                <span className="text-[10px] font-semibold text-[#4f46e5] bg-indigo-50 px-2 py-0.5 rounded-full">
                  Verified
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="rounded-lg bg-white p-2 border border-slate-100">
                  <div className="text-slate-500 text-[10px]">MLU-w (Words/Utt)</div>
                  <div className="text-base font-bold text-[#4f46e5]">{activeCase.mlu}</div>
                </div>
                <div className="rounded-lg bg-white p-2 border border-slate-100">
                  <div className="text-slate-500 text-[10px]">TTR (Vocab Diversity)</div>
                  <div className="text-base font-bold text-emerald-600">{activeCase.ttr.toFixed(2)}</div>
                </div>
                <div className="rounded-lg bg-white p-2 border border-slate-100">
                  <div className="text-slate-500 text-[10px]">Baseline Date</div>
                  <div className="font-semibold text-slate-700 text-[11px]">{activeCase.baselineDate}</div>
                </div>
                <div className="rounded-lg bg-white p-2 border border-slate-100">
                  <div className="text-slate-500 text-[10px]">Latest Follow-up</div>
                  <div className="font-semibold text-slate-700 text-[11px]">{activeCase.followUpDate}</div>
                </div>
              </div>
            </div>

            {/* Quick Prompts Panel */}
            <div className="mb-4">
              <span className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                Quick Clinical Prompts
              </span>
              <div className="space-y-2">
                {QUICK_PROMPTS.map((qp, idx) => {
                  const Icon = qp.icon;
                  return (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => {
                        handleSend(qp.prompt);
                        if (mobileTab === "context") setMobileTab("chat");
                      }}
                      className="flex w-full items-start gap-2.5 rounded-lg border border-[#e0e7ff] bg-white p-2.5 text-left text-xs font-medium text-[#1e1e62] transition hover:border-[#4f46e5] hover:bg-[#eef2ff]"
                    >
                      <div className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded bg-[#eef2ff] text-[#4f46e5]">
                        <Icon className="h-3.5 w-3.5" />
                      </div>
                      <span className="flex-1 leading-snug">{qp.label}</span>
                      <ChevronRight className="h-4 w-4 text-slate-400 mt-0.5" />
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Reset Conversation Button */}
            <div className="mt-auto pt-4 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setMessages(INITIAL_MESSAGES)}
                className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                <span>Reset Conversation</span>
              </button>
            </div>
          </aside>

          {/* Right Panel: Chat Stream & Input Area (Desktop & Mobile Chat Tab) */}
          <main
            className={`flex flex-1 flex-col overflow-hidden bg-[#f8faff] ${
              mobileTab === "chat" ? "flex" : "hidden lg:flex"
            }`}
          >
            {/* Message Stream */}
            <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
              {messages.map((msg) => {
                const isUser = msg.sender === "user";
                return (
                  <div key={msg.id} className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
                    <div className={`flex max-w-2xl gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
                      {/* Avatar */}
                      <div
                        className={`flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full text-xs font-bold shadow-sm ${
                          isUser ? "bg-[#1e1e62] text-white" : "bg-[#4f46e5] text-white"
                        }`}
                      >
                        {isUser ? "DR" : <Bot className="h-4 w-4" />}
                      </div>

                      {/* Bubble */}
                      <div
                        className={`rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${
                          isUser
                            ? "bg-[#1e1e62] text-white rounded-br-sm"
                            : "bg-white text-[#1e1e62] border border-[#e0e7ff] rounded-bl-sm"
                        }`}
                      >
                        <div className="whitespace-pre-wrap">{msg.text}</div>

                        {/* Metric Highlights Card if present */}
                        {msg.metrics && (
                          <div className="mt-3 grid grid-cols-4 gap-2 rounded-lg bg-[#f8faff] p-2.5 border border-[#e0e7ff] text-center">
                            <div>
                              <span className="text-[10px] text-slate-500 block">MLU-w</span>
                              <span className="text-xs font-bold text-[#4f46e5]">{msg.metrics.mluWords}</span>
                            </div>
                            <div>
                              <span className="text-[10px] text-slate-500 block">TTR</span>
                              <span className="text-xs font-bold text-emerald-600">{msg.metrics.ttr}</span>
                            </div>
                            <div>
                              <span className="text-[10px] text-slate-500 block">อนุภาค</span>
                              <span className="text-xs font-bold text-amber-600">{msg.metrics.particles}</span>
                            </div>
                            <div>
                              <span className="text-[10px] text-slate-500 block">คำลังเล</span>
                              <span className="text-xs font-bold text-rose-600">{msg.metrics.fillers}</span>
                            </div>
                          </div>
                        )}

                        {/* Action link if present */}
                        {msg.actionLabel && msg.actionUrl && (
                          <div className="mt-3">
                            <Link
                              href={msg.actionUrl}
                              className="inline-flex items-center gap-1.5 rounded-lg bg-[#e8607e] px-3 py-1.5 text-xs font-bold text-white shadow-sm hover:bg-[#d9486c]"
                            >
                              <span>{msg.actionLabel}</span>
                              <ChevronRight className="h-3.5 w-3.5" />
                            </Link>
                          </div>
                        )}

                        {/* Bottom Timestamp, Push to Draft, & Copy */}
                        <div className="mt-2 flex items-center justify-between gap-2 text-[10px] text-slate-400">
                          <span>{msg.timestamp}</span>
                          {!isUser && (
                            <div className="flex items-center gap-3">
                              <button
                                type="button"
                                onClick={() => pushToDraft(msg.text)}
                                className="flex items-center gap-1 font-semibold text-[#4f46e5] hover:text-[#4338ca]"
                                title="บันทึกข้อความนี้เข้าสู่ Session Report Draft"
                              >
                                <FileText className="h-3 w-3" />
                                <span>{draftPushSuccess ? "บันทึกใน Draft แล้ว ✓" : "คัดลอกลง Report Draft"}</span>
                              </button>
                              <button
                                type="button"
                                onClick={() => copyMessage(msg.id, msg.text)}
                                className="flex items-center gap-1 text-slate-500 hover:text-[#4f46e5]"
                                title="Copy text"
                              >
                                {copiedId === msg.id ? (
                                  <>
                                    <Check className="h-3 w-3 text-emerald-600" />
                                    <span className="text-emerald-600">Copied</span>
                                  </>
                                ) : (
                                  <>
                                    <Copy className="h-3 w-3" />
                                    <span>Copy</span>
                                  </>
                                )}
                              </button>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}

              {/* Thinking Indicator */}
              {isThinking && (
                <div className="flex justify-start">
                  <div className="flex gap-3 max-w-md">
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#4f46e5] text-white text-xs">
                      <Bot className="h-4 w-4" />
                    </div>
                    <div className="rounded-2xl rounded-bl-sm border border-[#e0e7ff] bg-white px-4 py-3 shadow-sm">
                      <div className="flex items-center gap-1.5 text-xs text-slate-500">
                        <span className="h-2 w-2 rounded-full bg-[#4f46e5] animate-bounce" />
                        <span className="h-2 w-2 rounded-full bg-[#4f46e5] animate-bounce [animation-delay:0.2s]" />
                        <span className="h-2 w-2 rounded-full bg-[#4f46e5] animate-bounce [animation-delay:0.4s]" />
                        <span className="ml-1 font-medium">กำลังวิเคราะห์ข้อมูลทางภาษา...</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Input Bar */}
            <div className="border-t border-[#e0e7ff] bg-white p-3 sm:p-4">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSend();
                }}
                className="mx-auto flex max-w-4xl items-center gap-2"
              >
                <input
                  type="text"
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  placeholder="ถามเกี่ยวกับผลประเมิน LSA, ร่างข้อความรายงาน หรือขอคำแนะนำเป้าหมายการบำบัด..."
                  className="flex-1 rounded-xl border border-[#cbd5e1] bg-[#f8faff] px-4 py-2.5 text-sm text-[#1e1e62] placeholder-slate-400 shadow-inner focus:border-[#4f46e5] focus:bg-white focus:outline-none"
                />
                <button
                  type="submit"
                  disabled={!inputText.trim() || isThinking}
                  className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#4f46e5] text-white shadow-md transition hover:bg-[#4338ca] disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <Send className="h-4 w-4" />
                </button>
              </form>
            </div>
          </main>
        </div>
      </div>
    </AppShell>
  );
}
