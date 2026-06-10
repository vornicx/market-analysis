import { createSupabaseServer } from "./supabase/server";
import { apiError } from "./api";

export interface AuthedUser {
  id: string;
  email: string;
  role: "admin" | "viewer";
}

/** Returns the authed admin user, or a NextResponse error to return as-is. */
export async function requireAdmin(): Promise<
  { user: AuthedUser; error: null } | { user: null; error: Response }
> {
  const supabase = await createSupabaseServer();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    return { user: null, error: apiError("UNAUTHENTICATED", "Sign in required", 401) };
  }
  const { data: profile } = await supabase
    .from("users")
    .select("id, email, role")
    .eq("id", user.id)
    .single();
  if (!profile || profile.role !== "admin") {
    return { user: null, error: apiError("FORBIDDEN", "Admin role required", 403) };
  }
  return { user: profile as AuthedUser, error: null };
}
