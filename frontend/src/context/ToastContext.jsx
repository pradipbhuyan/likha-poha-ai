import { createContext, useCallback, useContext, useRef, useState } from "react";

const ToastContext = createContext(null);

/**
 * ToastProvider — wraps the app and renders a fixed toast stack.
 *
 * Usage anywhere in the tree:
 *   const { showToast } = useToast();
 *   showToast("Saved!", "success");
 *   showToast("Something went wrong.", "error");
 *   showToast("Loading…", "info");
 */
export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const counter = useRef(0);

  const showToast = useCallback((message, type = "info", duration = 4000) => {
    const id = ++counter.current;
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, duration);
  }, []);

  const dismiss = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}

      {toasts.length > 0 && (
        <div className="toast-container" role="status" aria-live="polite">
          {toasts.map((t) => (
            <div
              key={t.id}
              className={`toast toast-${t.type}`}
              onClick={() => dismiss(t.id)}
              title="Click to dismiss"
            >
              <span className="toast-icon">
                {t.type === "success" ? "✅" : t.type === "error" ? "❌" : "ℹ️"}
              </span>
              <span className="toast-message">{t.message}</span>
            </div>
          ))}
        </div>
      )}
    </ToastContext.Provider>
  );
}

/** Returns { showToast } from the nearest ToastProvider. */
export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    // Graceful fallback outside the provider (e.g. unit tests)
    return { showToast: () => {} };
  }
  return ctx;
}
