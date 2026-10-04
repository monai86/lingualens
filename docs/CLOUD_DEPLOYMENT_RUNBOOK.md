# LinguaLens Cloud Deployment Runbook (Vercel + Render + Supabase)

**Document Version:** `v1.7.0`  
**Date:** 2026-10-04  
**Target Environment:** Staging / Controlled Clinical Pilot  

---

## สถาปัตยกรรมระบบบน Cloud

```
┌────────────────────────────────────────────────────────┐
│  Vercel (Frontend Next.js 16)                          │
│  • URL: https://lingualens.vercel.app                  │
│  • Code: apps/lingualens-app                           │
└────────────────────────────────────────────────────────┘
                           │
             REST API Calls (/api/v1)
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│  Render (Backend FastAPI + Python 3.11 Container)      │
│  • URL: https://lingualens-api.onrender.com            │
│  • Config: render.yaml + Dockerfile                    │
└────────────────────────────────────────────────────────┘
                           │
          Direct Postgres & Service Role JWT
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│  Supabase (ap-southeast-1 Singapore)                   │
│  1. PostgreSQL Database with Multi-Tenant RLS          │
│  2. Supabase Auth (TOTP MFA + Invitation-only)         │
│  3. Private Storage Bucket: audio-recordings           │
└────────────────────────────────────────────────────────┘
```

---

## ขั้นตอนที่ 1: ตั้งค่า Supabase (Database & Private Storage)

### 1.1 ข้อมูลโปรเจกต์ Supabase ที่เตรียมไว้แล้ว
- **Organization:** `LinguaLens` (`whgbnlqvrgjodiquclnr`)
- **Staging Project Ref:** `lliodfzujsmapwmpqmjb`
- **Region:** `ap-southeast-1` (Singapore)
- **Supabase URL:** `https://lliodfzujsmapwmpqmjb.supabase.co`
- **Publishable Key:** `sb_publishable_zC7wscUPHNtoqQb4amCEEQ_K2dCC5si`

### 1.2 รัน SQL Schema & RLS Policies
1. เข้าไปที่ [Supabase Dashboard - SQL Editor](https://supabase.com/dashboard/project/lliodfzujsmapwmpqmjb/sql)
2. คัดลอกเนื้อหาทั้งหมดจากไฟล์ [`scripts/supabase/clean_slate_supabase.sql`](file:///Users/porschecaa/lingualens/scripts/supabase/clean_slate_supabase.sql)
3. กด **RUN** เพื่อสร้าง:
   - โครงสร้างตาราง 28 ตาราง (Cases, Assessments, Transcripts, Reports, Care-teams ฯลฯ)
   - 100 Performance Indexes
   - Row-Level Security (RLS) policies แยก Tenant/Organization
   - Private Audio Storage Bucket (`audio-recordings`)
   - Seed ข้อมูล Catalog ทางคลินิกและ Alembic stamp

### 1.3 ดึงข้อมูลสำหรับเชื่อมต่อ Database
1. เข้าไปที่ **Project Settings** > **Database**
2. เลื่อนลงไปที่ **Connection string** > เลือกแท็บ **URI**
3. คัดลอก URI มาใช้งาน (แทนที่ `[YOUR-PASSWORD]` ด้วยรหัสผ่านของฐานข้อมูล):
   ```text
   postgresql://postgres:[YOUR-PASSWORD]@db.lliodfzujsmapwmpqmjb.supabase.co:5432/postgres
   ```
4. เข้าไปที่ **Project Settings** > **API** คัดลอก `service_role secret` เก็บไว้ใช้ใน Render

---

## ขั้นตอนที่ 2: Deploy Backend API บน Render

ใน repository นี้มีไฟล์ [`render.yaml`](file:///Users/porschecaa/lingualens/render.yaml) ซึ่งเป็น Blueprint พร้อมใช้งานเรียบร้อยแล้ว

### 2.1 สร้าง Web Service ผ่าน Blueprint
1. เข้าสู่ระบบ [Render Dashboard](https://dashboard.render.com/)
2. กดปุ่ม **New +** > เลือก **Blueprint**
3. เชื่อมต่อกับ GitHub Repository: `monai86/lingualens`
4. Render จะอ่านไฟล์ [`render.yaml`](file:///Users/porschecaa/lingualens/render.yaml) และสร้าง service:
   - **Service Name:** `lingualens-api`
   - **Runtime:** Docker (สร้างจาก `Dockerfile` ที่มี FFmpeg, libsndfile, PyThaiNLP)
   - **Region:** Singapore
   - **Health Check Path:** `/health`
5. กรอก Environment Variables ที่ต้องใส่เพิ่ม (Secret):
   - `LINGUALENS_DATABASE_URL`: URI จาก Supabase (ขั้นตอนที่ 1.3)
   - `LINGUALENS_SUPABASE_SERVICE_ROLE_KEY`: Service role secret จาก Supabase
   - `LINGUALENS_CORS_ALLOWED_ORIGINS`: ใส่โดเมนของ Frontend บน Vercel เช่น `https://lingualens.vercel.app,http://localhost:3000`
6. กด **Apply** เพื่อเริ่มการ Build และ Deploy

---

## ขั้นตอนที่ 3: Deploy Frontend บน Vercel

### 3.1 ตั้งค่าโปรเจกต์บน Vercel
1. เข้าสู่ระบบ [Vercel Dashboard](https://vercel.com/)
2. กด **Add New...** > **Project** > เลือก repository `monai86/lingualens`
3. ในส่วน **Framework Preset**: เลือก `Next.js`
4. ในส่วน **Root Directory**: กด **Edit** แล้วเลือก `apps/lingualens-app`
5. ในส่วน **Environment Variables** ให้กรอกค่าดังนี้:
   ```env
   NEXT_PUBLIC_API_BASE_URL=https://lingualens-api.onrender.com/api/v1
   NEXT_PUBLIC_SUPABASE_URL=https://lliodfzujsmapwmpqmjb.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=sb_publishable_zC7wscUPHNtoqQb4amCEEQ_K2dCC5si
   NEXT_PUBLIC_DEMO_MODE=false
   ```
   *(หมายเหตุ: แทนที่ `https://lingualens-api.onrender.com` ด้วย URL จริงที่ได้จาก Render ในขั้นตอนที่ 2)*
6. กด **Deploy**

---

## ขั้นตอนที่ 4: การตรวจสอบและทดสอบระบบ (Verification & Smoke Test)

เมื่อ Deploy ครบทั้ง 3 ส่วนแล้ว ให้ทดสอบตาม Checklist ดังนี้:

- [ ] **Backend Health Probe:**
  ```bash
  curl -s https://[YOUR-RENDER-URL]/health
  # ผลลัพธ์ที่ถูกต้อง: {"status":"ok","mock_mode":false}
  ```
- [ ] **Backend API Probe:**
  ```bash
  curl -s https://[YOUR-RENDER-URL]/api/v1/health
  # ผลลัพธ์ที่ถูกต้อง: {"status":"ok","mock_mode":false}
  ```
- [ ] **JWKS Endpoint Reachability:**
  Backend สามารถดึง Public Key จาก Supabase เพื่อตรวจ JWT Bearer token ได้โดยไม่ต้องแชร์ secret
- [ ] **Frontend Vercel Loading:**
  หน้าเว็บเปิดใช้งานได้ มีการแสดงผลภาษาไทยครบถ้วน และเชื่อมต่อไปยัง API ได้
- [ ] **Authentication Gate:**
  ระบบบังคับให้เข้าใช้งานผ่าน Supabase Auth ตามบทบาท (Therapist, Clinical Supervisor, Org Admin)
