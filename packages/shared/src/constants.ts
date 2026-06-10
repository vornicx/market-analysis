export const SEGMENT_KEYS = ["general_football", "world_cup"] as const;
export type SegmentKey = (typeof SEGMENT_KEYS)[number];

export const ALERT_TYPES = [
  "SHARP_MOVE",
  "STEAM_MOVE",
  "PRICE_SPIKE",
  "BOOK_DIVERGENCE",
  "RARE_MOVE",
  "REVERSAL",
] as const;
export type AlertType = (typeof ALERT_TYPES)[number];

export const CONFIDENCE_BANDS = ["low", "medium", "high"] as const;
export type ConfidenceBand = (typeof CONFIDENCE_BANDS)[number];

export const ALERT_STATUSES = ["new", "acknowledged", "dismissed", "replayed"] as const;
export type AlertStatus = (typeof ALERT_STATUSES)[number];

export const FEEDBACK_VERDICTS = ["useful", "noise", "late", "wrong"] as const;
export type FeedbackVerdict = (typeof FEEDBACK_VERDICTS)[number];

export const TOGGLEABLE_FLAGS = [
  "football_enabled",
  "world_cup_enabled",
  "world_cup_only_mode",
  "global_pause",
  "dry_run",
] as const;
export type ToggleableFlag = (typeof TOGGLEABLE_FLAGS)[number];

export const API_ERROR_CODES = [
  "UNAUTHENTICATED",
  "FORBIDDEN",
  "NOT_FOUND",
  "VALIDATION",
  "CONFLICT",
  "INTERNAL",
] as const;
export type ApiErrorCode = (typeof API_ERROR_CODES)[number];
