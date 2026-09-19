# Content and Clinical-Safety Language

This is the copy contract for the first prototype. Labels describe evidence and
workflow state; they do not make a diagnosis. The same meanings must be used in
Figma, the web app, GUI, TUI, API errors, reports, and research figures.

## Required Thai labels

| Concept | Required label | Use |
|---|---|---|
| Clinical attention profile | `ประเด็นที่ควรพิจารณาเพิ่มเติม` | Heading for one or more non-exclusive attention cues. |
| Insufficient evidence | `ข้อมูลยังไม่เพียงพอ` | State when the available input cannot support the requested interpretation. |
| Reference unavailable | `ไม่มีข้อมูลอ้างอิงที่เหมาะสม` | State when age/language/task/protocol or other reference compatibility is not met. |
| Not comparable | `ไม่สามารถเปรียบเทียบกับครั้งก่อนได้` | Longitudinal state when prior and current measurements are incompatible. |
| Clinician-authored conclusion | `ข้อสรุปที่บันทึกโดยผู้เชี่ยวชาญ` | Label for a human-authored conclusion, with author and time. |
| Safety boundary | `ระบบช่วยจัดระเบียบหลักฐาน การวินิจฉัยเป็นหน้าที่ของผู้เชี่ยวชาญ` | Persistent or contextual disclosure on clinical result and sign-off screens. |
| Additional evidence | `ขอหลักฐานเพิ่มเติม` | Action when evidence is conflicting, insufficient, or not comparable. |
| Monitoring | `ติดตามพัฒนาการต่อเนื่อง` | Clinician disposition option; not a claim that no concern exists. |

## Concern vocabulary

Allowed attention labels describe areas for review and may coexist:

- language-development concern;
- speech-production concern;
- social-communication concern;
- features that support further ASD-focused assessment;
- mixed or conflicting evidence;
- unclassified developmental concern; and
- insufficient evidence.

The UI must not turn these labels into mutually exclusive percentages or a
ranking that implies diagnostic severity. A clinician may acknowledge, disagree
with, or request more evidence for each computed cue. The computed cue remains
visible after disagreement and the clinician response is stored separately.

## Required evidence sentence pattern

Every computed result uses this structure:

```text
สิ่งที่พบ: [descriptive feature/domain/cue]
หลักฐาน: [source, quality, and protocol context]
ข้อจำกัด: [missing, conflicting, stale, or reference limitation]
ขั้นตอนถัดไป: [therapist-reviewable action]
```

If a field is unavailable, state that it is unavailable. Do not replace it with
zero, normal, negative, or an empty success state.

## Prohibited wording

Do not use these phrases or equivalent wording in UI, report templates,
notifications, fixtures, screenshots, Figma text, or API messages:

```text
ตรวจพบออทิสติก
ไม่เป็นออทิสติก
ความน่าจะเป็น ASD
ASD score
diagnosed by system
ASD probability
```

Do not claim that a speech feature, prosody feature, questionnaire response,
reference-band status, or longitudinal trend proves or rules out ASD. Do not
display a numeric value beside an ASD-related cue. Percent signs are allowed
only for clearly operational information such as upload progress.

## State copy rules

| State | Must say | Must not say |
|---|---|---|
| Offline/API failure | What could not be reached and whether retry is available. | That data was saved when no server record exists. |
| Permission denied | The role/care-team boundary and safe return. | Any restricted child or clinical detail. |
| Consent blocked | Capture is unavailable until valid consent is confirmed. | A path to recording hidden behind a stale client state. |
| Insufficient | Which evidence is missing and the concrete recovery action. | A negative, normal, or zero result. |
| Reference unavailable | Descriptive evidence can still be reviewed with its limitation. | A forced reference-band classification. |
| Stale | The result is excluded from the current report until regenerated. | Editing or signing stale evidence. |
| Not comparable | Why a trend is not produced. | A line, arrow, or severity implication built from incompatible data. |
| Sign-off | The clinician owns the authored conclusion and snapshot. | Automated diagnosis or silent mutation of a signed report. |

## Accessibility and localization rules

- Pair color with text, icon, and shape; red/green is never the only meaning.
- Keep visible labels beside controls and announce errors through an accessible
  status region.
- Keep the 3px focus ring and 44px minimum target in all interactive states.
- Use Noto Sans Thai, body line height at least 1.5, and allow Thai wrapping at
  200% zoom without hiding the primary action.
- Avoid dense English abbreviations in the default therapist view. Expose
  feature names, schema versions, and provider details progressively.
