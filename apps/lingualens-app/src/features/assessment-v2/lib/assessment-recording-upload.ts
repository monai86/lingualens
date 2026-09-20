import { apiUploadBlob } from "@/lib/api";
import type { AssessmentV2Client } from "@/services/assessment-v2-client";

export type AssessmentRecordingUploadClient = Pick<
  AssessmentV2Client,
  "createRecording" | "createUploadIntent" | "completeUpload"
>;

export type AssessmentRecordingUploadStage = "hashing" | "creating" | "uploading" | "finalizing";

export type AssessmentRecordingUploadOptions = {
  client: AssessmentRecordingUploadClient;
  assessmentId: string;
  activityCode: string;
  blob: Blob;
  idempotencyKey: string;
  upload?: (url: string, blob: Blob) => Promise<void>;
  onStageChange?: (stage: AssessmentRecordingUploadStage) => void;
};

export async function uploadAssessmentRecording({
  client,
  assessmentId,
  activityCode,
  blob,
  idempotencyKey,
  upload = apiUploadBlob,
  onStageChange,
}: AssessmentRecordingUploadOptions) {
  if (blob.size <= 0) {
    throw new Error("recording_empty");
  }
  if (!idempotencyKey.trim()) {
    throw new Error("idempotency_key_required");
  }

  onStageChange?.("hashing");
  const checksum = await sha256Checksum(blob);
  const contentType = blob.type.trim().toLowerCase() || "audio/webm";

  onStageChange?.("creating");
  const intent = await client.createRecording(
    assessmentId,
    activityCode,
    {
      content_type: contentType,
      size_bytes: blob.size,
      checksum,
    },
    idempotencyKey,
  );

  const uploadIntent = await client.createUploadIntent(intent.recording.id);
  onStageChange?.("uploading");
  await upload(uploadIntent.upload.url, blob);

  onStageChange?.("finalizing");
  const completed = await client.completeUpload(intent.recording.id);
  return { ...completed, checksum };
}

export async function sha256Checksum(blob: Blob): Promise<string> {
  if (!globalThis.crypto?.subtle) {
    throw new Error("secure_hash_unavailable");
  }
  const digest = await globalThis.crypto.subtle.digest("SHA-256", await readBlobBytes(blob));
  const bytes = new Uint8Array(digest);
  const hex = Array.from(bytes, (value) => value.toString(16).padStart(2, "0")).join("");
  return `sha256:${hex}`;
}

async function readBlobBytes(blob: Blob): Promise<ArrayBuffer> {
  if (typeof blob.arrayBuffer === "function") {
    return blob.arrayBuffer();
  }
  if (typeof FileReader !== "undefined") {
    return new Promise<ArrayBuffer>((resolve, reject) => {
      const reader = new FileReader();
      reader.onerror = () => reject(reader.error ?? new Error("blob_read_failed"));
      reader.onload = () => {
        if (reader.result instanceof ArrayBuffer) {
          resolve(reader.result);
          return;
        }
        reject(new Error("blob_read_failed"));
      };
      reader.readAsArrayBuffer(blob);
    });
  }
  return new Response(blob).arrayBuffer();
}
