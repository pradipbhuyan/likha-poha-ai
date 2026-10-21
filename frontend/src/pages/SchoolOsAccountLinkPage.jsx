import { useEffect, useState } from "react";
import LoginPage from "./LoginPage";
import { supabase } from "../api/supabaseClient";

const STATE_KEY = "school-os-account-link-state";
const STATE_TTL_MS = 10 * 60 * 1000;
const OPAQUE_VALUE_PATTERN = /^[A-Za-z0-9_-]{43}$/;

function isOpaqueValue(value) {
  if (typeof value !== "string" || !OPAQUE_VALUE_PATTERN.test(value))
    return false;
  try {
    const decoded = atob(value.replace(/-/g, "+").replace(/_/g, "/"));
    return decoded.length === 32;
  } catch {
    return false;
  }
}

function loadStoredState() {
  try {
    const stored = JSON.parse(sessionStorage.getItem(STATE_KEY) || "null");
    if (
      stored &&
      isOpaqueValue(stored.state) &&
      typeof stored.createdAt === "number" &&
      Date.now() - stored.createdAt >= 0 &&
      Date.now() - stored.createdAt <= STATE_TTL_MS
    ) {
      return stored.state;
    }
  } catch {
    // Invalid storage is treated as an expired attempt.
  }
  sessionStorage.removeItem(STATE_KEY);
  return null;
}

function storeState(state) {
  sessionStorage.setItem(
    STATE_KEY,
    JSON.stringify({ state, createdAt: Date.now() })
  );
}

function clearState() {
  sessionStorage.removeItem(STATE_KEY);
}

function configuredCallback() {
  const configured = import.meta.env.VITE_SCHOOL_OS_ACCOUNT_LINK_CALLBACK_URL;
  if (!configured) return null;
  try {
    const url = new URL(configured);
    if (url.protocol !== "https:" || url.search || url.hash) return null;
    return url;
  } catch {
    return null;
  }
}

export default function SchoolOsAccountLinkPage() {
  const [linkState, setLinkState] = useState(null);
  const [session, setSession] = useState(undefined);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const query = new URLSearchParams(window.location.search);
    const fromQuery = query.get("state");

    if (fromQuery !== null) {
      if (query.size === 1 && isOpaqueValue(fromQuery)) {
        storeState(fromQuery);
      } else {
        clearState();
      }
      window.history.replaceState({}, "", window.location.pathname);
    }

    setLinkState(loadStoredState());

    supabase.auth
      .getSession()
      .then(({ data }) => setSession(data.session || null));
    const { data: listener } = supabase.auth.onAuthStateChange(
      (_event, nextSession) => {
        setSession(nextSession || null);
      }
    );
    return () => listener.subscription.unsubscribe();
  }, []);

  function cancel() {
    clearState();
    window.location.replace("/");
  }

  async function confirm() {
    if (
      submitting ||
      !linkState ||
      !session?.access_token ||
      !configuredCallback()
    )
      return;

    setSubmitting(true);
    setError(null);
    try {
      const response = await fetch(
        `${
          import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"
        }/api/account-link/school-os/proof`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${session.access_token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ state: linkState }),
        }
      );

      const body = await response.json().catch(() => null);
      if (!response.ok || !isOpaqueValue(body?.code)) {
        clearState();
        setError(
          "This linking attempt can no longer be completed. Return to School OS and start a new attempt."
        );
        return;
      }

      const callback = configuredCallback();
      if (!callback) {
        clearState();
        setError(
          "School OS linking is temporarily unavailable. Return to School OS and start a new attempt."
        );
        return;
      }

      callback.hash = new URLSearchParams({
        state: linkState,
        code: body.code,
      }).toString();
      clearState();
      window.location.replace(callback.toString());
    } catch {
      clearState();
      setError(
        "This linking attempt can no longer be completed. Return to School OS and start a new attempt."
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (!linkState) {
    return (
      <main className="sign-in-page">
        <section className="sign-in-card">
          <h1>School OS linking unavailable</h1>
          <p>
            This linking attempt is missing or has expired. Return to School OS
            and start a new attempt.
          </p>
        </section>
      </main>
    );
  }

  if (session === undefined) {
    return (
      <main className="sign-in-page">
        <section className="sign-in-card" role="status">
          <h1>Checking your Likha Poha session…</h1>
        </section>
      </main>
    );
  }

  if (!session) {
    return (
      <LoginPage
        onLogin={() => window.location.reload()}
        onShowSignup={() => {}}
        onShowLanding={() => {}}
      />
    );
  }

  const callbackAvailable = Boolean(configuredCallback());

  return (
    <main className="sign-in-page">
      <section className="sign-in-card" aria-labelledby="school-os-link-title">
        <p className="eyebrow">School OS account linking</p>
        <h1 id="school-os-link-title">Link your Likha Poha account</h1>
        <p>
          Link this currently signed-in Likha Poha account with your School OS
          account.
        </p>
        <p>
          School OS receives an internal account identifier. Your Likha Poha
          password and session are not shared, and school roles or permissions
          are not transferred.
        </p>
        {error ? (
          <p className="form-error" role="alert">
            {error}
          </p>
        ) : null}
        {!callbackAvailable ? (
          <p className="form-error" role="alert">
            School OS linking is temporarily unavailable. Return to School OS
            and start a new attempt later.
          </p>
        ) : (
          <button disabled={submitting} onClick={confirm} type="button">
            {submitting ? "Linking…" : "Confirm link"}
          </button>
        )}
        <button
          className="secondary-button"
          disabled={submitting}
          onClick={cancel}
          type="button"
        >
          Cancel
        </button>
      </section>
    </main>
  );
}
