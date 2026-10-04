"use client";

import { useEffect } from "react";

export interface KeyboardReviewOptions {
  onPlayPause?: () => void;
  onReplayActive?: () => void;
  onToggleLoop?: () => void;
  onAssignSpeaker?: (speaker: "CHI" | "INV" | "MOT" | "FAT") => void;
  onAdvanceLine?: () => void;
  onPreviousLine?: () => void;
  isEnabled?: boolean;
}

export function useKeyboardReview({
  onPlayPause,
  onReplayActive,
  onToggleLoop,
  onAssignSpeaker,
  onAdvanceLine,
  onPreviousLine,
  isEnabled = true,
}: KeyboardReviewOptions) {
  useEffect(() => {
    if (!isEnabled) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      const isCmdOrCtrl = e.metaKey || e.ctrlKey;
      const target = e.target as HTMLElement | null;
      const isTextInput =
        target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.isContentEditable);

      // Cmd/Ctrl + Space: Replay active utterance
      if (isCmdOrCtrl && e.code === "Space") {
        e.preventDefault();
        onReplayActive?.();
        return;
      }

      // Spacebar: Play/Pause (only when not typing in text input)
      if (e.code === "Space" && !isTextInput) {
        e.preventDefault();
        onPlayPause?.();
        return;
      }

      // Cmd/Ctrl + L: Toggle loop mode
      if (isCmdOrCtrl && (e.key === "l" || e.key === "L")) {
        e.preventDefault();
        onToggleLoop?.();
        return;
      }

      // Cmd/Ctrl + 1: CHI
      if (isCmdOrCtrl && e.key === "1") {
        e.preventDefault();
        onAssignSpeaker?.("CHI");
        return;
      }

      // Cmd/Ctrl + 2: INV
      if (isCmdOrCtrl && e.key === "2") {
        e.preventDefault();
        onAssignSpeaker?.("INV");
        return;
      }

      // Cmd/Ctrl + 3: MOT
      if (isCmdOrCtrl && e.key === "3") {
        e.preventDefault();
        onAssignSpeaker?.("MOT");
        return;
      }

      // Cmd/Ctrl + 4: FAT
      if (isCmdOrCtrl && e.key === "4") {
        e.preventDefault();
        onAssignSpeaker?.("FAT");
        return;
      }

      // Cmd/Ctrl + Enter: Mark verified & advance line
      if (isCmdOrCtrl && e.key === "Enter") {
        e.preventDefault();
        onAdvanceLine?.();
        return;
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [
    isEnabled,
    onPlayPause,
    onReplayActive,
    onToggleLoop,
    onAssignSpeaker,
    onAdvanceLine,
    onPreviousLine,
  ]);
}
