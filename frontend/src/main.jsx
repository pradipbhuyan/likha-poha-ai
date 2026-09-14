import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { CapacitorUpdater } from '@capgo/capacitor-updater'
import './index.css'
import App from './App.jsx'
import "katex/dist/katex.min.css";
import "./i18n";

// Must be called on every launch, before any network requests, or the
// native updater auto-rolls back to the previous bundle after a timeout
// (it takes this as the signal that the current bundle's JS loaded).
// No-op on web (see the plugin's web shim) — safe to call unconditionally.
CapacitorUpdater.notifyAppReady();

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
