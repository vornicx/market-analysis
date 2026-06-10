import { NextResponse } from "next/server";
import type { ApiErrorCode } from "@market-monitor/shared";

export function apiError(code: ApiErrorCode, message: string, status: number) {
  return NextResponse.json({ error: { code, message } }, { status });
}

export function apiOk<T>(body: T, status = 200) {
  return NextResponse.json(body, { status });
}
