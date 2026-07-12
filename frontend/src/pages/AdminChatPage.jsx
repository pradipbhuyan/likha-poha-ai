/**
 * AdminChatPage.jsx — Admin panel for Platform Chat settings and moderation
 * Sections:
 *   1. Global chat settings (enable/disable, file/voice, retention)
 *   2. Per-user chat access grants
 *   3. Chat room moderation (view / deactivate rooms)
 */
import { useCallback, useEffect, useState } from "react";
import {
  adminGetChatSettings, adminSaveChatSettings,
  adminListChatUsers, adminToggleChatAccess,
  adminListChatRooms, adminDeactivateChatRoom,
} from "../api/platformChat";
import { authFetch } from "../api/authClient";

export default function AdminChatPage({ user: _user }) {
  const [settings, setSettings] = useState(null);
  const [savingSettings, setSavingSettings] = useState(false);
  const [settingsMsg, setSettingsMsg] = useState(null);

  const [chatUsers, setChatUsers] = useState([]);
  const [searchQ, setSearchQ] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [toggling, setToggling] = useState({});
  const [usersMsg, setUsersMsg] = useState(null);

  const [rooms, setRooms] = useState([]);
  const [loadingRooms, setLoadingRooms] = useState(false);
  const [roomsMsg, setRoomsMsg] = useState(null);

  const loadSettings = useCallback(async () => {
    try {
      const r = await adminGetChatSettings();
      if (r.success) setSettings(r);
    } catch (e) { setSettingsMsg("Error loading settings: " + e.message); }
  }, []);

  const loadChatUsers = useCallback(async () => {
    try {
      const r = await adminListChatUsers();
      if (r.success) setChatUsers(r.users || []);
    } catch (e) {
      console.error("[chat] loadChatUsers failed:", e?.message);
    }
  }, []);

  const loadRooms = useCallback(async () => {
    setLoadingRooms(true);
    try {
      const r = await adminListChatRooms();
      if (r.success) setRooms(r.rooms || []);
    } catch (e) {
      console.error("[chat] loadRooms failed:", e?.message);
    }
    setLoadingRooms(false);
  }, []);

  useEffect(() => { loadSettings(); loadChatUsers(); loadRooms(); }, [loadSettings, loadChatUsers, loadRooms]);

  async function saveSettings() {
    if (!settings) return;
    setSavingSettings(true); setSettingsMsg(null);
    try {
      const r = await adminSaveChatSettings({
        global_enabled: settings.global_enabled,
        allow_files: settings.allow_files,
        allow_voice: settings.allow_voice,
        max_file_size_mb: Number(settings.max_file_size_mb) || 10,
        retention_days: Number(settings.retention_days) || 90,
      });
      if (r.success) { setSettings(r); setSettingsMsg("✅ Settings saved."); }
    } catch (e) { setSettingsMsg("Error: " + e.message); }
    setSavingSettings(false);
  }

  async function searchUsers() {
    if (!searchQ.trim()) return;
    setSearching(true); setUsersMsg(null);
    try {
      const r = await authFetch(`/api/admin/users/search?q=${encodeURIComponent(searchQ)}&limit=10`);
      if (r.success) {
        const grantedIds = new Set(chatUsers.map(u => u.id));
        setSearchResults((r.users || []).map(u => ({ ...u, chat_access: grantedIds.has(u.id) })));
        if (!r.users?.length) setUsersMsg("No users found.");
      }
    } catch (e) { setUsersMsg("Error: " + e.message); }
    setSearching(false);
  }

  async function toggleAccess(userId, enabled) {
    setToggling(p => ({ ...p, [userId]: true })); setUsersMsg(null);
    try {
      const r = await adminToggleChatAccess(userId, enabled);
      if (r.success) {
        setUsersMsg(enabled ? "✅ Chat access granted." : "✅ Chat access revoked.");
        loadChatUsers();
        setSearchResults(prev => prev.map(u => u.id === userId ? { ...u, chat_access: enabled } : u));
      }
    } catch (e) { setUsersMsg("Error: " + e.message); }
    setToggling(p => ({ ...p, [userId]: false }));
  }

  async function deactivateRoom(roomId) {
    if (!window.confirm("Deactivate this chat room? Participants will no longer be able to send messages.")) return;
    try {
      const r = await adminDeactivateChatRoom(roomId);
      if (r.success) { setRoomsMsg("✅ Room deactivated."); loadRooms(); }
    } catch (e) { setRoomsMsg("Error: " + e.message); }
  }

  const inp = { padding: "7px 10px", borderRadius: 7, border: "1px solid var(--border,#e5e7eb)", fontFamily: "inherit", fontSize: ".82rem", background: "var(--panel,#fff)" };
  const card = { background: "var(--panel,#fff)", border: "1px solid var(--border,#e5e7eb)", borderRadius: 12, padding: "20px 22px", marginBottom: 24 };

  return (
    <div style={{ maxWidth: 860, margin: "0 auto", padding: "0 0 60px" }}>
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontWeight: 800, fontSize: "1.2rem", margin: "0 0 3px" }}>💬 Platform Chat Settings</h2>
        <div style={{ fontSize: ".85rem", color: "#64748b" }}>
          Control global chat service, per-user access grants, and moderate conversations.
        </div>
      </div>

      {/* ── 1. Global Settings ── */}
      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: ".95rem", marginBottom: 16 }}>⚙️ Global Settings</div>
        {!settings ? (
          <div style={{ color: "#64748b", fontSize: ".82rem" }}>Loading…</div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {[
              { key: "global_enabled", label: "Global chat service", desc: "Enable or disable chat for the entire platform" },
              { key: "allow_files", label: "File & screenshot sharing", desc: "Allow users to send images and files" },
              { key: "allow_voice", label: "Voice messages", desc: "Allow in-browser voice recording and sending" },
            ].map(({ key, label, desc }) => (
              <div key={key} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: ".85rem" }}>{label}</div>
                  <div style={{ fontSize: ".74rem", color: "#64748b" }}>{desc}</div>
                </div>
                <button
                  onClick={() => setSettings(p => ({ ...p, [key]: !p[key] }))}
                  style={{ padding: "5px 14px", borderRadius: 20, border: "none", fontFamily: "inherit", fontWeight: 700, fontSize: ".76rem", cursor: "pointer", background: settings[key] ? "#dcfce7" : "#fee2e2", color: settings[key] ? "#16a34a" : "#dc2626" }}>
                  {settings[key] ? "● ON" : "○ OFF"}
                </button>
              </div>
            ))}
            <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
              <div>
                <label style={{ fontSize: ".78rem", fontWeight: 600, display: "block", marginBottom: 4 }}>Max file size (MB)</label>
                <input type="number" min={1} max={50} value={settings.max_file_size_mb}
                  onChange={e => setSettings(p => ({ ...p, max_file_size_mb: e.target.value }))}
                  style={{ ...inp, width: 80 }} />
              </div>
              <div>
                <label style={{ fontSize: ".78rem", fontWeight: 600, display: "block", marginBottom: 4 }}>Message retention (days, 0 = forever)</label>
                <input type="number" min={0} max={3650} value={settings.retention_days}
                  onChange={e => setSettings(p => ({ ...p, retention_days: e.target.value }))}
                  style={{ ...inp, width: 100 }} />
              </div>
            </div>
            <div>
              <button onClick={saveSettings} disabled={savingSettings}
                style={{ padding: "9px 20px", borderRadius: 8, border: "none", background: savingSettings ? "#94a3b8" : "#6366f1", color: "#fff", fontWeight: 700, fontSize: ".85rem", cursor: savingSettings ? "not-allowed" : "pointer", fontFamily: "inherit" }}>
                {savingSettings ? "Saving…" : "Save Settings"}
              </button>
              {settingsMsg && <span style={{ marginLeft: 12, fontSize: ".78rem", color: settingsMsg.startsWith("✅") ? "#22c55e" : "#dc2626" }}>{settingsMsg}</span>}
            </div>
          </div>
        )}
      </div>

      {/* ── 2. Per-User Access ── */}
      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: ".95rem", marginBottom: 4 }}>🔐 Per-User Chat Access</div>
        <div style={{ fontSize: ".82rem", color: "#64748b", marginBottom: 14 }}>
          Admins and teachers always have chat. Paid-plan users get chat automatically. Use this to grant or revoke for specific users.
        </div>

        {/* Search */}
        <div style={{ display: "flex", gap: 8, marginBottom: 14, flexWrap: "wrap" }}>
          <input value={searchQ} onChange={e => setSearchQ(e.target.value)} placeholder="Search username or email…"
            style={{ ...inp, flex: "1 1 200px" }}
            onKeyDown={e => { if (e.key === "Enter") searchUsers(); }} />
          <button onClick={searchUsers} disabled={searching}
            style={{ ...inp, cursor: "pointer", background: "#6366f1", color: "#fff", border: "none", fontWeight: 600 }}>
            {searching ? "Searching…" : "Search"}
          </button>
          <button onClick={loadChatUsers} style={{ ...inp, cursor: "pointer", color: "#6366f1", fontWeight: 600 }}>Refresh</button>
        </div>
        {usersMsg && <div style={{ marginBottom: 10, fontSize: ".8rem", color: usersMsg.startsWith("✅") ? "#22c55e" : "#dc2626" }}>{usersMsg}</div>}

        {/* Search results */}
        {searchResults.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: ".76rem", fontWeight: 600, color: "#64748b", marginBottom: 6 }}>SEARCH RESULTS</div>
            {searchResults.map(u => (
              <div key={u.id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "6px 0", borderBottom: "1px solid var(--border,#f1f5f9)", flexWrap: "wrap" }}>
                <span style={{ fontSize: ".8rem", flex: 1 }}>{u.username || u.email} <span style={{ color: "#94a3b8" }}>({u.role})</span></span>
                <button onClick={() => toggleAccess(u.id, !u.chat_access)} disabled={toggling[u.id]}
                  style={{ padding: "4px 12px", borderRadius: 7, border: "none", cursor: "pointer", fontFamily: "inherit", fontWeight: 600, fontSize: ".76rem", background: u.chat_access ? "#fef2f2" : "#f0fdf4", color: u.chat_access ? "#dc2626" : "#16a34a" }}>
                  {toggling[u.id] ? "…" : u.chat_access ? "Revoke Chat" : "Grant Chat"}
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Current users with explicit access */}
        <div>
          <div style={{ fontSize: ".76rem", fontWeight: 600, color: "#64748b", marginBottom: 6 }}>
            USERS WITH EXPLICIT CHAT ACCESS ({chatUsers.length})
          </div>
          {chatUsers.length === 0 ? (
            <div style={{ color: "#94a3b8", fontSize: ".8rem" }}>No explicit grants. Paid-plan users get access automatically.</div>
          ) : chatUsers.map(u => (
            <div key={u.id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "5px 0", borderBottom: "1px solid var(--border,#f1f5f9)", flexWrap: "wrap" }}>
              <span style={{ fontSize: ".8rem", flex: 1 }}>{u.username || u.email} <span style={{ color: "#94a3b8" }}>({u.role} · {u.subscription_plan})</span></span>
              <button onClick={() => toggleAccess(u.id, false)} disabled={toggling[u.id]}
                style={{ padding: "4px 12px", borderRadius: 7, border: "none", cursor: "pointer", fontFamily: "inherit", fontWeight: 600, fontSize: ".76rem", background: "#fef2f2", color: "#dc2626" }}>
                {toggling[u.id] ? "…" : "Revoke"}
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* ── 3. Room Moderation ── */}
      <div style={card}>
        <div style={{ fontWeight: 700, fontSize: ".95rem", marginBottom: 4 }}>🔍 Chat Room Moderation</div>
        <div style={{ fontSize: ".82rem", color: "#64748b", marginBottom: 14 }}>
          View all active conversations. Deactivate rooms to stop participants from messaging.
        </div>
        {roomsMsg && <div style={{ marginBottom: 10, fontSize: ".8rem", color: roomsMsg.startsWith("✅") ? "#22c55e" : "#dc2626" }}>{roomsMsg}</div>}
        {loadingRooms ? (
          <div style={{ color: "#94a3b8", fontSize: ".82rem" }}>Loading…</div>
        ) : rooms.length === 0 ? (
          <div style={{ color: "#94a3b8", fontSize: ".82rem" }}>No chat rooms yet.</div>
        ) : (
          <div style={{ border: "1px solid var(--border,#e5e7eb)", borderRadius: 10, overflow: "hidden" }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 80px 70px 80px", background: "var(--surface2,#f8fafc)", padding: "8px 14px", fontSize: ".72rem", fontWeight: 700, color: "#64748b", textTransform: "uppercase", letterSpacing: ".04em" }}>
              <span>Participant A</span><span>Participant B</span><span>Type</span><span>Msgs</span><span>Action</span>
            </div>
            {rooms.map(rm => (
              <div key={rm.id} style={{ display: "grid", gridTemplateColumns: "1fr 1fr 80px 70px 80px", padding: "9px 14px", borderTop: "1px solid var(--border,#f1f5f9)", alignItems: "center", fontSize: ".8rem" }}>
                <span>{rm.participant_a?.username || "?"}</span>
                <span>{rm.participant_b?.username || "?"}</span>
                <span style={{ fontSize: ".72rem", color: "#64748b" }}>{(rm.room_type || "").replace("_", " ")}</span>
                <span>{rm.message_count || 0}</span>
                <button
                  onClick={() => deactivateRoom(rm.id)}
                  disabled={!rm.is_active}
                  style={{ padding: "3px 8px", borderRadius: 6, border: "none", background: rm.is_active ? "#fef2f2" : "#f1f5f9", color: rm.is_active ? "#dc2626" : "#94a3b8", fontWeight: 600, fontSize: ".72rem", cursor: rm.is_active ? "pointer" : "default", fontFamily: "inherit" }}>
                  {rm.is_active ? "Deactivate" : "Inactive"}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
