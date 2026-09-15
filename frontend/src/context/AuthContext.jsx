import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { getCurrentProfile } from "../services/api";
import { supabase, supabaseConfigurationError } from "../services/supabase";
import { isSupportedSignUpEmail, supportedEmailMessage } from "../utils/authValidation";

export const AuthContext = createContext(null);

const friendlyAuthError = (error) => error?.message || "We could not complete that request. Please try again.";

export function AuthProvider({ children }) {
  const [session, setSession] = useState(null);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(supabaseConfigurationError);

  const resolveProfile = useCallback(async (nextSession) => {
    if (!nextSession?.access_token) {
      setProfile(null);
      return null;
    }
    try {
      const nextProfile = await getCurrentProfile(nextSession.access_token);
      setProfile(nextProfile);
      setError(null);
      return nextProfile;
    } catch (requestError) {
      setProfile(null);
      setError("Your session could not be verified. Please sign in again.");
      return null;
    }
  }, []);

  useEffect(() => {
    if (!supabase) {
      setLoading(false);
      return undefined;
    }
    let mounted = true;
    const load = async () => {
      const { data, error: sessionError } = await supabase.auth.getSession();
      if (!mounted) return;
      if (sessionError) setError(friendlyAuthError(sessionError));
      setSession(data.session);
      await resolveProfile(data.session);
      if (mounted) setLoading(false);
    };
    load();
    const { data: listener } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession);
      resolveProfile(nextSession).finally(() => mounted && setLoading(false));
    });
    return () => { mounted = false; listener.subscription.unsubscribe(); };
  }, [resolveProfile]);

  const signIn = useCallback(async ({ email, password }) => {
    if (!supabase) return { error: new Error(supabaseConfigurationError) };
    const { data, error: signInError } = await supabase.auth.signInWithPassword({ email, password });
    if (signInError) return { error: signInError };
    setSession(data.session);
    const resolvedProfile = await resolveProfile(data.session);
    return { profile: resolvedProfile, error: resolvedProfile ? null : new Error("Profile verification failed.") };
  }, [resolveProfile]);

  const signUp = useCallback(async ({ fullName, email, password }) => {
    if (!supabase) return { error: new Error(supabaseConfigurationError) };
    if (!isSupportedSignUpEmail(email)) return { error: new Error(supportedEmailMessage) };
    // Role is deliberately absent: the database auth trigger provisions attendees only.
    const { data, error: signUpError } = await supabase.auth.signUp({
      email,
      password,
      options: { data: { full_name: fullName } },
    });
    if (signUpError) return { error: signUpError };
    if (data.session) {
      setSession(data.session);
      const resolvedProfile = await resolveProfile(data.session);
      return { profile: resolvedProfile, confirmationRequired: false, error: resolvedProfile ? null : new Error("Profile verification failed.") };
    }
    return { confirmationRequired: true, error: null };
  }, [resolveProfile]);

  const signOut = useCallback(async () => {
    if (!supabase) return;
    const { error: signOutError } = await supabase.auth.signOut();
    if (signOutError) throw signOutError;
    setSession(null);
    setProfile(null);
    setError(null);
  }, []);

  const value = useMemo(() => ({
    session, user: session?.user ?? null, profile, loading, error,
    signIn, signUp, signOut, resolveProfile,
  }), [session, profile, loading, error, signIn, signUp, signOut, resolveProfile]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider.");
  return context;
}
