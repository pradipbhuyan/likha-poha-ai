import { useEffect, useState } from "react";
import { supabase } from "../api/supabaseClient";

const OPAQUE_CODE_PATTERN = /^[A-Za-z0-9_-]{43}$/;
const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function isOpaqueCode(value) {
  if (typeof value !== "string" || !OPAQUE_CODE_PATTERN.test(value)) {
    return false;
  }

  try {
    const decoded = atob(value.replace(/-/g, "+").replace(/_/g, "/"));
    return decoded.length === 32;
  } catch {
    return false;
  }
}

function readAndClearLaunchCode() {
  const hash = window.location.hash.startsWith("#")
    ? window.location.hash.slice(1)
    : "";

  // Remove the opaque launch artifact before making a request or rendering UI.
  window.history.replaceState(
    window.history.state,
    "",
    `${window.location.pathname}${window.location.search}`
  );

  const params = new URLSearchParams(hash);
  const codes = params.getAll("code");
  if (params.size !== 1 || codes.length !== 1 || !isOpaqueCode(codes[0])) {
    return null;
  }

  return codes[0];
}

function FailureScreen() {
  return (
    <main className="sign-in-page">
      <section
        className="sign-in-card"
        aria-labelledby="school-os-sso-error-title"
      >
        <h1 id="school-os-sso-error-title">
          Unable to open Likha Poha from School OS.
        </h1>
        <p>
          Return to School OS and start a new attempt, or continue to Likha Poha
          sign in.
        </p>
        <button onClick={() => window.location.replace("/")} type="button">
          Go to Likha Poha sign in
        </button>
      </section>
    </main>
  );
}

export default function SchoolOsSsoPage() {
  const [code] = useState(readAndClearLaunchCode);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!code) {
      setFailed(true);
      return;
    }

    let cancelled = false;

    async function complete() {
      try {
        const response = await fetch(`${API_BASE}/api/sso/school-os/complete`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ code }),
        });

        const body = await response.json().catch(() => null);
        if (
          !response.ok ||
          !body ||
          typeof body.access_token !== "string" ||
          !body.access_token ||
          typeof body.refresh_token !== "string" ||
          !body.refresh_token
        ) {
          throw new Error("SSO completion failed");
        }

        const { error: setSessionError } = await supabase.auth.setSession({
          access_token: body.access_token,
          refresh_token: body.refresh_token,
        });

        if (setSessionError) {
          throw setSessionError;
        }

        const {
          data: { session },
          error: sessionError,
        } = await supabase.auth.getSession();

        if (sessionError || !session?.user) {
          throw sessionError || new Error("SSO session verification failed");
        }

        if (!cancelled) {
          window.location.replace("/");
        }
      } catch {
        if (!cancelled) {
          setFailed(true);
        }
      }
    }

    void complete();

    return () => {
      cancelled = true;
    };
  }, [code]);

  if (failed) {
    return <FailureScreen />;
  }

  return (
    <main className="sign-in-page">
      <section className="sign-in-card" role="status">
        <h1>Opening Likha Poha…</h1>
      </section>
    </main>
  );
}
