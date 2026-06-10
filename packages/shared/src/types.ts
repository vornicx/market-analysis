import type {
  AlertStatus,
  AlertType,
  ConfidenceBand,
  FeedbackVerdict,
  SegmentKey,
} from "./constants";

export interface MonitorConfig {
  id: 1;
  football_enabled: boolean;
  world_cup_enabled: boolean;
  world_cup_only_mode: boolean;
  global_pause: boolean;
  dry_run: boolean;
  llm_enabled: boolean;
  daily_credit_cap: number;
  monthly_credit_cap: number;
  odds_api_region: string;
  worker_poll_floor_seconds: number;
  alert_suppression_minutes: number;
  updated_by: string | null;
  updated_at: string;
}

export interface PollingProfile {
  gt48h: number; // minutes between polls; 0 = off
  h48_24: number;
  h24_6: number;
  h6_1: number;
  lt1h: number;
}

export interface SegmentThresholds {
  price_move: { abs_dp_min: number; z_min: number };
  divergence: { divergence_min: number };
  drift: { drift_polls_min: number; drift_cum_min: number };
  sharp_leader: { sharp_dp_min: number; follower_count_min: number };
  persistence: { persistence_ratio_min: number };
  reversal: { reversal_ratio: number; reversal_window_polls: number };
  rarity: { rarity_pctile_min: number; rarity_min_samples: number };
}

export interface MonitorSegment {
  segment_key: SegmentKey;
  display_label: string;
  sport_keys: string[];
  bookmaker_keys: string[];
  sharp_bookmaker_keys: string[];
  market_keys: string[];
  polling_profile: PollingProfile;
  min_alert_score: number;
  thresholds: SegmentThresholds;
  telegram_chat_id: string | null;
  enabled: boolean;
  updated_at: string;
}

export interface EventRow {
  id: string;
  provider_event_id: string;
  sport_key: string;
  segment_key: SegmentKey;
  home_team: string;
  away_team: string;
  commence_time: string;
  status: "upcoming" | "live" | "finished" | "cancelled";
}

export interface Alert {
  id: string;
  segment_key: SegmentKey;
  event_id: string;
  market_key: string;
  selection_id: string;
  alert_type: AlertType;
  alert_score: number;
  confidence_band: ConfidenceBand;
  reason_summary: string;
  status: AlertStatus;
  dedupe_key: string;
  created_at: string;
}

export interface AlertEvidence {
  alert_id: string;
  payload: {
    detectors: Record<string, { fired: boolean; points: number; evidence: unknown }>;
    price_path: Array<{
      bookmaker_key: string;
      series: Array<{ polled_at: string; price: number; implied_prob: number }>;
    }>;
    consensus_series: Array<{ polled_at: string; implied_prob: number }>;
    thresholds_used: SegmentThresholds;
  };
}

export interface AlertFeedback {
  id: string;
  alert_id: string;
  user_id: string;
  verdict: FeedbackVerdict;
  note: string | null;
  created_at: string;
}

export interface LlmAnalysis {
  alert_id: string;
  classification:
    | "possible_sharp_move"
    | "possible_market_correction"
    | "possible_news_driven_move"
    | "possible_noise"
    | "needs_human_review"
    | null;
  summary: string | null;
  confidence: ConfidenceBand | null;
  status: "ok" | "failed" | "skipped";
}

export interface WorkerRun {
  id: string;
  started_at: string;
  finished_at: string | null;
  cycle_type: "poll" | "event_refresh" | "idle";
  segments: string[];
  credits_used: number;
  snapshots_written: number;
  alerts_created: number;
  status: "ok" | "error" | "partial" | "running";
  error: string | null;
}

export interface ApiError {
  error: { code: string; message: string };
}
