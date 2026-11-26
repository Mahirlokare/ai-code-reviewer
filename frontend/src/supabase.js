/**
 * Supabase Auth Client for ReviewPilot
 * Handles user sign-up, confirmation emails, login, session persistence, and logout.
 */
import { createClient } from "@supabase/supabase-js";

// Read from build environment or localStorage configuration
export const getSupabaseConfig = () => {
  const envUrl = import.meta.env.VITE_SUPABASE_URL || "";
  const envKey = import.meta.env.VITE_SUPABASE_ANON_KEY || "";
  const localUrl = sessionStorage.getItem("reviewpilot_supabase_url") || "";
  const localKey = sessionStorage.getItem("reviewpilot_supabase_key") || "";

  const url = localUrl || envUrl;
  const anonKey = localKey || envKey;

  return { url: url.trim(), anonKey: anonKey.trim() };
};

export const isSupabaseConfigured = () => {
  const { url, anonKey } = getSupabaseConfig();
  return Boolean(url && anonKey && url.startsWith("https://"));
};

let supabaseClient = null;

export const getSupabase = () => {
  const { url, anonKey } = getSupabaseConfig();
  if (url && anonKey) {
    if (!supabaseClient || supabaseClient.supabaseUrl !== url) {
      supabaseClient = createClient(url, anonKey, {
        auth: {
          persistSession: true,
          autoRefreshToken: true,
          detectSessionInUrl: true,
        },
      });
    }
    return supabaseClient;
  }
  return null;
};

export const setCustomSupabaseConfig = (url, anonKey) => {
  if (url && anonKey) {
    sessionStorage.setItem("reviewpilot_supabase_url", url.trim());
    sessionStorage.setItem("reviewpilot_supabase_key", anonKey.trim());
    supabaseClient = createClient(url.trim(), anonKey.trim());
  } else {
    sessionStorage.removeItem("reviewpilot_supabase_url");
    sessionStorage.removeItem("reviewpilot_supabase_key");
    supabaseClient = null;
  }
};

/**
 * Sign up a new user via Supabase Auth
 * Automatically sends confirmation email to user's registered inbox.
 */
export async function supabaseSignUp(email, password, { username, fullName } = {}) {
  const client = getSupabase();
  if (!client) {
    throw new Error("Supabase is not configured. Please provide Supabase URL and Anon Key.");
  }

  const { data, error } = await client.auth.signUp({
    email,
    password,
    options: {
      data: {
        username: username || email.split("@")[0],
        full_name: fullName || username || email.split("@")[0],
      },
      emailRedirectTo: window.location.origin,
    },
  });

  if (error) throw error;
  return data;
}

/**
 * Sign in existing user via Supabase Auth
 */
export async function supabaseSignIn(email, password) {
  const client = getSupabase();
  if (!client) {
    throw new Error("Supabase is not configured. Please provide Supabase URL and Anon Key.");
  }

  const { data, error } = await client.auth.signInWithPassword({
    email,
    password,
  });

  if (error) throw error;
  return data;
}

/**
 * Sign out current session
 */
export async function supabaseSignOut() {
  const client = getSupabase();
  if (client) {
    try {
      await client.auth.signOut();
    } catch (e) {
      console.warn("Supabase sign out error:", e);
    }
  }
}

/**
 * Get current active user from Supabase
 */
export async function getSupabaseCurrentUser() {
  const client = getSupabase();
  if (!client) return null;
  try {
    const { data: { session } } = await client.auth.getSession();
    if (!session || !session.user) return null;
    return {
      id: session.user.id,
      email: session.user.email,
      username: session.user.user_metadata?.username || session.user.email.split("@")[0],
      full_name: session.user.user_metadata?.full_name || "",
      provider: "supabase",
      token: session.access_token,
    };
  } catch (e) {
    return null;
  }
}
