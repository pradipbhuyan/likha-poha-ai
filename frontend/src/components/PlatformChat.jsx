/**
 * PlatformChat.jsx — Real-time user-to-user chat widget
 * Supports: text, image/file attachments, voice recording
 * Uses Supabase Realtime for live message delivery
 */
import { useEffect, useRef, useState } from "react";
import {
  getChatSettings, getChatContacts, getChatRooms,
  getOrCreateRoom, getRoomMessages, sendMessage,
  markRoomRead, uploadChatFile, subscribeToRoom,
} from "../api/platformChat";

const ROLE_EMOJI = { teacher: "👨‍🏫", student: "🎓", parent: "👨‍👩‍👧", admin: "🛠️" };
const MSG_MAX = 4000;

function Avatar({ user, size = 32 }) {
  const emoji = ROLE_EMOJI[user?.role] || "👤";
  if (user?.avatar) {
    return (
      <img src={user.avatar} alt={user.username}
        style={{ width: size, height: size, borderRadius: "50%", objectFit: "cover", flexShrink: 0 }} />
    );
  }
  return (
    <div style={{ width: size, height: size, borderRadius: "50%", background: "#1e3a5f",
      display: "flex", alignItems: "center", justifyContent: "center",
      fontSize: size * 0.45, flexShrink: 0 }}>
      {emoji}
    </div>
  );
}

function formatTime(ts) {
  if (!ts) return "";
  const d = new Date(ts);
  const now = new Date();
  const isToday = d.toDateString() === now.toDateString();
  return isToday
    ? d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    : d.toLocaleDateString([], { month: "short", day: "numeric" }) + " " + d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function AttachmentPreview({ msg }) {
  if (!msg.attachment_url) return null;
  const mime = msg.attachment_mime || "";
  if (mime.startsWith("image/")) {
    return (
      <div style={{ marginTop: 6 }}>
        <img src={msg.attachment_url} alt={msg.attachment_name || "image"}
          style={{ maxWidth: 220, maxHeight: 160, borderRadius: 8, objectFit: "cover",
            cursor: "pointer", display: "block" }}
          onClick={() => window.open(msg.attachment_url, "_blank")} />
      </div>
    );
  }
  if (mime.startsWith("audio/")) {
    return (
      <div style={{ marginTop: 6 }}>
        <audio controls src={msg.attachment_url}
          style={{ maxWidth: 220, height: 36 }} />
      </div>
    );
  }
  return (
    <div style={{ marginTop: 6 }}>
      <a href={msg.attachment_url} target="_blank" rel="noreferrer"
        style={{ color: "#93c5fd", fontSize: ".78rem", display: "flex", alignItems: "center", gap: 4 }}>
        📎 {msg.attachment_name || "file"}
        {msg.attachment_size ? ` (${(msg.attachment_size / 1024).toFixed(0)} KB)` : ""}
      </a>
    </div>
  );
}

export default function PlatformChat({ user }) {
  const [chatSettings, setChatSettings] = useState(null);
  const [open, setOpen] = useState(false);
  const [view, setView] = useState("rooms"); // "rooms" | "contacts" | "conversation"
  const [rooms, setRooms] = useState([]);
  const [contacts, setContacts] = useState([]);
  const [activeRoom, setActiveRoom] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [uploadingFile, setUploadingFile] = useState(false);
  const [recording, setRecording] = useState(false);
  const [totalUnread, setTotalUnread] = useState(0);
  const [loadingRooms, setLoadingRooms] = useState(false);
  const [error, setError] = useState(null);

  const bottomRef = useRef(null);
  const inputRef = useRef(null);
  const fileInputRef = useRef(null);
  const mediaRef = useRef(null);
  const chunksRef = useRef([]);
  const unsubRef = useRef(null);

  // Load chat settings on mount
  useEffect(() => {
    if (!user) return;
    getChatSettings().then(r => {
      if (r.success) setChatSettings(r);
    }).catch(() => {});
  }, [user]);

  async function loadRooms() {
    setLoadingRooms(true);
    try {
      const r = await getChatRooms();
      if (r.success) {
        setRooms(r.rooms || []);
        setTotalUnread((r.rooms || []).reduce((s, rm) => s + (rm.unread_count || 0), 0));
      }
    } catch (e) {
      console.error("[chat] loadRooms failed:", e?.message);
    }
    setLoadingRooms(false);
  }

  // Load rooms when panel opens
  useEffect(() => {
    if (open && view === "rooms" && user) loadRooms();
  }, [open, view]); // eslint-disable-line react-hooks/exhaustive-deps

  // Scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Focus input when entering conversation
  useEffect(() => {
    if (view === "conversation") inputRef.current?.focus();
  }, [view, activeRoom]);

  // Realtime subscription for active room
  useEffect(() => {
    if (unsubRef.current) { unsubRef.current(); unsubRef.current = null; }
    if (activeRoom && view === "conversation") {
      unsubRef.current = subscribeToRoom(activeRoom.id, (newMsg) => {
        setMessages(prev => {
          if (prev.find(m => m.id === newMsg.id)) return prev;
          return [...prev, newMsg];
        });
        if (newMsg.sender_id !== user?.id) {
          markRoomRead(activeRoom.id).catch(() => {});
        }
        setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
      });
    }
    return () => { if (unsubRef.current) { unsubRef.current(); unsubRef.current = null; } };
  }, [activeRoom, view, user?.id]);

  async function openContact(contact) {
    try {
      const r = await getOrCreateRoom(contact.id);
      if (r.success) await openRoom(r.room);
    } catch (e) { setError("Could not open chat: " + e.message); }
  }

  async function openRoom(room) {
    setActiveRoom(room);
    setMessages([]);
    setView("conversation");
    try {
      const r = await getRoomMessages(room.id);
      if (r.success) setMessages(r.messages || []);
      await markRoomRead(room.id);
      setRooms(prev => prev.map(rm => rm.id === room.id ? { ...rm, unread_count: 0 } : rm));
      setTotalUnread(prev => Math.max(0, prev - (room.unread_count || 0)));
    } catch (e) {
      console.error("[chat] openRoom failed:", e?.message);
    }
  }

  async function handleSend() {
    const text = input.trim();
    if (!text || sending) return;
    setInput("");
    setSending(true);
    try {
      const r = await sendMessage(activeRoom.id, { content: text, message_type: "text" });
      if (r.success) setMessages(prev => [...prev, r.message]);
    } catch (e) { setError("Send failed: " + e.message); }
    setSending(false);
  }

  async function handleFileChange(e) {
    const file = e.target.files?.[0];
    if (!file || !activeRoom) return;
    e.target.value = "";
    setUploadingFile(true);
    try {
      const att = await uploadChatFile(activeRoom.id, file);
      const mime = file.type || "";
      const msgType = mime.startsWith("image/") ? "image" : mime.startsWith("audio/") ? "voice" : "file";
      const r = await sendMessage(activeRoom.id, {
        message_type: msgType,
        attachment_url: att.url,
        attachment_name: att.name,
        attachment_size: att.size,
        attachment_mime: att.mime,
      });
      if (r.success) setMessages(prev => [...prev, r.message]);
    } catch (e) { setError("Upload failed: " + e.message); }
    setUploadingFile(false);
  }

  async function handlePaste(e) {
    const items = e.clipboardData?.items;
    if (!items || !activeRoom || !chatSettings?.allow_files) return;
    for (const item of items) {
      if (item.type.startsWith("image/")) {
        const file = item.getAsFile();
        if (!file) continue;
        e.preventDefault();
        setUploadingFile(true);
        try {
          const named = new File([file], "screenshot.png", { type: "image/png" });
          const att = await uploadChatFile(activeRoom.id, named);
          const r = await sendMessage(activeRoom.id, {
            message_type: "image", attachment_url: att.url,
            attachment_name: att.name, attachment_size: att.size, attachment_mime: att.mime,
          });
          if (r.success) setMessages(prev => [...prev, r.message]);
        } catch (err) { setError("Paste upload failed: " + err.message); }
        setUploadingFile(false);
        break;
      }
    }
  }

  function startRecording() {
    if (!navigator.mediaDevices) return;
    navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
      chunksRef.current = [];
      const mr = new MediaRecorder(stream, { mimeType: "audio/webm" });
      mr.ondataavailable = e => chunksRef.current.push(e.data);
      mr.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const file = new File([blob], "voice_message.webm", { type: "audio/webm" });
        setUploadingFile(true);
        try {
          const att = await uploadChatFile(activeRoom.id, file);
          const r = await sendMessage(activeRoom.id, {
            message_type: "voice", attachment_url: att.url,
            attachment_name: "Voice message", attachment_size: att.size, attachment_mime: att.mime,
          });
          if (r.success) setMessages(prev => [...prev, r.message]);
        } catch (err) { setError("Voice upload failed: " + err.message); }
        setUploadingFile(false);
      };
      mediaRef.current = mr;
      mr.start();
      setRecording(true);
    }).catch(() => setError("Microphone access denied."));
  }

  function stopRecording() {
    if (mediaRef.current && recording) {
      mediaRef.current.stop();
      setRecording(false);
    }
  }

  // Don't render at all if user has no chat access
  if (!user || !chatSettings?.can_use_chat) return null;

  const panelStyle = {
    position: "fixed", bottom: 88, right: 84, zIndex: 9998,
    width: 340, maxWidth: "calc(100vw - 104px)",
    height: 520, maxHeight: "calc(100vh - 120px)",
    background: "#0f172a", border: "1px solid #334155",
    borderRadius: 16, display: "flex", flexDirection: "column",
    boxShadow: "0 20px 60px rgba(0,0,0,0.5)",
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    overflow: "hidden",
  };

  const headerStyle = {
    display: "flex", alignItems: "center", gap: 10,
    padding: "12px 14px", borderBottom: "1px solid #1e293b",
    background: "linear-gradient(135deg, #1e3a5f, #1d4ed8)",
  };

  return (
    <>
      {open && (
        <div style={panelStyle}>
          {/* ── HEADER ── */}
          <div style={headerStyle}>
            {view === "conversation" && activeRoom ? (
              <>
                <button onClick={() => { setView("rooms"); loadRooms(); }}
                  style={{ background: "none", border: "none", color: "#fff", cursor: "pointer", fontSize: 18, padding: 0 }}>‹</button>
                <Avatar user={activeRoom.other_user} size={28} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 700, fontSize: 13, color: "#fff" }}>{activeRoom.other_user?.username}</div>
                  <div style={{ fontSize: 10, color: "rgba(255,255,255,.6)", textTransform: "capitalize" }}>
                    {activeRoom.other_user?.role} {activeRoom.other_user?.role === "student" ? `· ${activeRoom.other_user?.grade || ""}` : ""}
                  </div>
                </div>
              </>
            ) : (
              <>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 700, fontSize: 14, color: "#fff" }}>
                    {view === "contacts" ? "New Message" : "💬 Messages"}
                  </div>
                  {view === "rooms" && <div style={{ fontSize: 10, color: "rgba(255,255,255,.6)" }}>Your conversations</div>}
                </div>
                {view === "rooms" && (
                  <button onClick={() => { setView("contacts"); getChatContacts().then(r => { if (r.success) setContacts(r.contacts || []); }); }}
                    style={{ background: "rgba(255,255,255,.12)", border: "none", color: "#fff", borderRadius: 7, padding: "4px 9px", cursor: "pointer", fontSize: 11, fontFamily: "inherit", fontWeight: 600 }}>
                    + New
                  </button>
                )}
                {view === "contacts" && (
                  <button onClick={() => setView("rooms")}
                    style={{ background: "none", border: "none", color: "rgba(255,255,255,.7)", cursor: "pointer", fontSize: 11, fontFamily: "inherit" }}>
                    Cancel
                  </button>
                )}
              </>
            )}
            <button onClick={() => setOpen(false)}
              style={{ background: "rgba(255,255,255,.12)", border: "none", color: "#fff", borderRadius: 7, width: 26, height: 26, cursor: "pointer", fontSize: 14, display: "flex", alignItems: "center", justifyContent: "center" }}>×</button>
          </div>

          {/* ── ERROR BANNER ── */}
          {error && (
            <div style={{ padding: "6px 14px", background: "rgba(239,68,68,.15)", borderBottom: "1px solid rgba(239,68,68,.3)", fontSize: ".75rem", color: "#fca5a5", display: "flex", justifyContent: "space-between" }}>
              <span>{error}</span>
              <button onClick={() => setError(null)} style={{ background: "none", border: "none", color: "#fca5a5", cursor: "pointer", fontSize: 14 }}>×</button>
            </div>
          )}

          {/* ── ROOMS LIST ── */}
          {view === "rooms" && (
            <div style={{ flex: 1, overflowY: "auto" }}>
              {loadingRooms && <div style={{ padding: 20, textAlign: "center", color: "#64748b", fontSize: ".82rem" }}>Loading…</div>}
              {!loadingRooms && rooms.length === 0 && (
                <div style={{ padding: 24, textAlign: "center", color: "#64748b", fontSize: ".82rem" }}>
                  <div style={{ fontSize: "2rem", marginBottom: 8 }}>💬</div>
                  <div>No conversations yet.</div>
                  <div style={{ marginTop: 4, fontSize: ".74rem" }}>Tap <strong>+ New</strong> to start one.</div>
                </div>
              )}
              {rooms.map(rm => (
                <div key={rm.id} onClick={() => openRoom(rm)}
                  style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 14px", borderBottom: "1px solid #1e293b", cursor: "pointer" }}
                  onMouseEnter={e => e.currentTarget.style.background = "#1e293b"}
                  onMouseLeave={e => e.currentTarget.style.background = "transparent"}>
                  <Avatar user={rm.other_user} size={36} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontWeight: 600, fontSize: 13, color: "#f1f5f9", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {rm.other_user?.username}
                      </span>
                      {rm.unread_count > 0 && (
                        <span style={{ background: "#2563eb", color: "#fff", borderRadius: 10, minWidth: 18, height: 18, fontSize: 10, fontWeight: 700, display: "flex", alignItems: "center", justifyContent: "center", padding: "0 4px", flexShrink: 0 }}>
                          {rm.unread_count}
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: 11, color: "#64748b", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", marginTop: 2 }}>
                      {rm.last_message
                        ? rm.last_message.message_type !== "text"
                          ? `📎 ${rm.last_message.attachment_name || rm.last_message.message_type}`
                          : rm.last_message.content?.slice(0, 50)
                        : "No messages yet"}
                    </div>
                  </div>
                  <div style={{ fontSize: 10, color: "#475569", flexShrink: 0 }}>{rm.last_message_at ? formatTime(rm.last_message_at) : ""}</div>
                </div>
              ))}
            </div>
          )}

          {/* ── CONTACTS LIST ── */}
          {view === "contacts" && (
            <div style={{ flex: 1, overflowY: "auto" }}>
              {contacts.length === 0 && <div style={{ padding: 20, textAlign: "center", color: "#64748b", fontSize: ".82rem" }}>Loading contacts…</div>}
              {contacts.map(c => (
                <div key={c.id} onClick={() => openContact(c)}
                  style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 14px", borderBottom: "1px solid #1e293b", cursor: "pointer" }}
                  onMouseEnter={e => e.currentTarget.style.background = "#1e293b"}
                  onMouseLeave={e => e.currentTarget.style.background = "transparent"}>
                  <Avatar user={c} size={36} />
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 13, color: "#f1f5f9" }}>{c.username}</div>
                    <div style={{ fontSize: 11, color: "#64748b", textTransform: "capitalize" }}>
                      {ROLE_EMOJI[c.role]} {c.role}{c.grade ? ` · ${c.grade}` : ""}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* ── CONVERSATION ── */}
          {view === "conversation" && (
            <>
              {/* Messages */}
              <div style={{ flex: 1, overflowY: "auto", padding: "12px 12px 6px", display: "flex", flexDirection: "column", gap: 8 }}>
                {messages.map((msg, i) => {
                  const isMe = msg.sender_id === user?.id;
                  return (
                    <div key={msg.id || i} style={{ display: "flex", justifyContent: isMe ? "flex-end" : "flex-start", alignItems: "flex-end", gap: 6 }}>
                      {!isMe && <Avatar user={activeRoom?.other_user} size={22} />}
                      <div style={{ maxWidth: "78%", background: isMe ? "linear-gradient(135deg,#2563eb,#7c3aed)" : "#1e293b", color: "#f8fafc", borderRadius: isMe ? "14px 14px 4px 14px" : "14px 14px 14px 4px", padding: "8px 11px", fontSize: 13, lineHeight: 1.5 }}>
                        {msg.content && <div>{msg.content}</div>}
                        <AttachmentPreview msg={msg} />
                        <div style={{ fontSize: 10, color: isMe ? "rgba(255,255,255,.5)" : "#475569", marginTop: 3, textAlign: "right" }}>
                          {formatTime(msg.created_at)}{isMe && msg.read_at ? " ✓✓" : isMe ? " ✓" : ""}
                        </div>
                      </div>
                    </div>
                  );
                })}
                {(sending || uploadingFile) && (
                  <div style={{ display: "flex", justifyContent: "flex-end" }}>
                    <div style={{ background: "#1e293b", borderRadius: "14px 14px 4px 14px", padding: "8px 12px", display: "flex", gap: 4 }}>
                      {[0,1,2].map(i => <div key={i} style={{ width: 6, height: 6, borderRadius: "50%", background: "#6366f1", animation: `bounce 1.2s ease-in-out ${i*0.2}s infinite` }} />)}
                    </div>
                  </div>
                )}
                <div ref={bottomRef} />
              </div>

              {/* Recording indicator */}
              {recording && (
                <div style={{ padding: "6px 14px", background: "rgba(239,68,68,.15)", borderTop: "1px solid rgba(239,68,68,.2)", display: "flex", alignItems: "center", gap: 8, fontSize: ".78rem", color: "#fca5a5" }}>
                  <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#ef4444", animation: "pulse 1s ease-in-out infinite", display: "inline-block" }} />
                  Recording… tap 🎙️ to stop
                </div>
              )}

              {/* Input bar */}
              <div style={{ padding: "8px 10px", borderTop: "1px solid #1e293b", display: "flex", gap: 6, alignItems: "flex-end" }}>
                {chatSettings?.allow_files && (
                  <>
                    <button onClick={() => fileInputRef.current?.click()} disabled={uploadingFile}
                      title="Attach file or screenshot"
                      style={{ background: "none", border: "none", color: uploadingFile ? "#475569" : "#64748b", cursor: uploadingFile ? "not-allowed" : "pointer", fontSize: 17, padding: "4px 2px", flexShrink: 0 }}>
                      📎
                    </button>
                    <input ref={fileInputRef} type="file" accept="image/*,audio/*,.pdf,.doc,.docx" style={{ display: "none" }} onChange={handleFileChange} />
                  </>
                )}
                {chatSettings?.allow_voice && (
                  <button
                    onMouseDown={startRecording}
                    onMouseUp={stopRecording}
                    onTouchStart={startRecording}
                    onTouchEnd={stopRecording}
                    title="Hold to record voice"
                    style={{ background: recording ? "rgba(239,68,68,.2)" : "none", border: "none", color: recording ? "#ef4444" : "#64748b", cursor: "pointer", fontSize: 17, padding: "4px 2px", flexShrink: 0, borderRadius: 6 }}>
                    🎙️
                  </button>
                )}
                <textarea
                  ref={inputRef}
                  rows={1}
                  value={input}
                  maxLength={MSG_MAX}
                  placeholder="Type a message…"
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
                  onPaste={handlePaste}
                  style={{ flex: 1, background: "#111827", border: "1px solid #334155", borderRadius: 10, padding: "8px 10px", color: "#f8fafc", fontFamily: "inherit", fontSize: 13, resize: "none", outline: "none", lineHeight: 1.4, maxHeight: 72, overflowY: "auto" }}
                />
                <button onClick={handleSend} disabled={!input.trim() || sending}
                  style={{ background: input.trim() && !sending ? "linear-gradient(135deg,#2563eb,#7c3aed)" : "#1e293b", border: "none", borderRadius: 10, width: 36, height: 36, cursor: input.trim() && !sending ? "pointer" : "not-allowed", color: "#fff", fontSize: 15, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                  ›
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {/* ── FLOATING BUTTON ── */}
      <button onClick={() => setOpen(v => !v)}
        style={{ position: "fixed", bottom: 20, right: 84, zIndex: 9998, width: 54, height: 54, borderRadius: "50%", border: "none", background: open ? "#334155" : "linear-gradient(135deg,#10b981,#0ea5e9)", color: "#fff", fontSize: 20, cursor: "pointer", boxShadow: "0 4px 20px rgba(16,185,129,.4)", display: "flex", alignItems: "center", justifyContent: "center", transition: "all .2s" }}
        title="Messages">
        {open ? "×" : "👥"}
        {!open && totalUnread > 0 && (
          <span style={{ position: "absolute", top: 0, right: 0, background: "#ef4444", color: "#fff", borderRadius: "50%", width: 18, height: 18, fontSize: 10, fontWeight: 700, display: "flex", alignItems: "center", justifyContent: "center" }}>{totalUnread}</span>
        )}
      </button>

      <style>{`
        @keyframes bounce{0%,60%,100%{transform:translateY(0)}30%{transform:translateY(-5px)}}
        @keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
      `}</style>
    </>
  );
}
