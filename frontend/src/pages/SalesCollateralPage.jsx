import { useEffect, useMemo, useState } from "react";
import {
  Copy,
  Download,
  ExternalLink,
  FileText,
  MessageCircle,
  Plus,
  Trash2,
  Video,
} from "lucide-react";

import {
  createSalesCollateral,
  deleteSalesCollateral,
  getSalesCollaterals,
  updateSalesCollateral,
  uploadSalesCollateralFile,
} from "../api/sales";

const CHANNEL_OPTIONS = [
  { value: "all", label: "All" },
  { value: "whatsapp", label: "WhatsApp" },
  { value: "instagram_reel", label: "Insta Reels" },
  { value: "brochure", label: "Brochure" },
  { value: "poster", label: "Poster" },
  { value: "demo_script", label: "Demo Script" },
];

const AUDIENCE_OPTIONS = [
  { value: "parents", label: "Parents" },
  { value: "students", label: "Students" },
  { value: "teachers", label: "Teachers" },
  { value: "schools", label: "Schools" },
];

const FORMAT_OPTIONS = [
  { value: "image", label: "Image" },
  { value: "video", label: "Video" },
  { value: "pdf", label: "PDF" },
  { value: "text", label: "Text" },
  { value: "link", label: "Link" },
];

const INITIAL_FORM = {
  title: "",
  audience: "parents",
  channel: "whatsapp",
  format: "image",
  description: "",
  caption: "",
  asset_url: "",
  thumbnail_url: "",
  status: "active",
  display_order: 10,
};

function channelLabel(value) {
  /** Convert stored channel ids into short sales-friendly labels. */
  return CHANNEL_OPTIONS.find((option) => option.value === value)?.label || value;
}

function renderCaption(text) {
  /**
   * Render a WhatsApp-style formatted caption as styled JSX.
   * Supported syntax (mirrors WhatsApp's own formatting):
   *   *bold text*     → <strong>
   *   _italic text_   → <em>
   *   ~strikethrough~ → <s>
   *   Lines starting with •  - * or numbers → bullet list items
   *   Blank lines     → paragraph break
   */
  if (!text) return null;
  const lines = text.split("\n");
  const elements = [];
  let key = 0;

  function parseInline(str) {
    // Process bold (*), italic (_), strikethrough (~) inline markers
    const parts = [];
    let i = 0;
    const markers = [
      { open: "*", tag: "strong" },
      { open: "_", tag: "em" },
      { open: "~", tag: "s" },
    ];
    while (i < str.length) {
      let matched = false;
      for (const { open, tag } of markers) {
        if (str[i] === open) {
          const end = str.indexOf(open, i + 1);
          if (end > i + 1) {
            const inner = str.slice(i + 1, end);
            const Tag = tag;
            parts.push(<Tag key={`${i}-${tag}`}>{inner}</Tag>);
            i = end + 1;
            matched = true;
            break;
          }
        }
      }
      if (!matched) {
        // Append plain text
        const nextSpecial = str.slice(i).search(/[*_~]/);
        if (nextSpecial === -1) {
          parts.push(str.slice(i));
          break;
        } else {
          parts.push(str.slice(i, i + nextSpecial));
          i += nextSpecial;
        }
      }
    }
    return parts.length > 0 ? parts : str;
  }

  for (let li = 0; li < lines.length; li++) {
    const line = lines[li];
    if (line.trim() === "") {
      elements.push(<br key={key++} />);
      continue;
    }
    // Bullet line: starts with •, -, *, or digits followed by . or )
    const bulletMatch = line.match(/^(\s*)(•|-|\*|\d+[.)]\s)/);
    if (bulletMatch) {
      const content = line.slice(bulletMatch[0].length);
      elements.push(
        <div key={key++} style={{ display: "flex", gap: "6px", marginBottom: "2px" }}>
          <span style={{ color: "#3b82f6", fontWeight: 700, minWidth: "12px" }}>•</span>
          <span>{parseInline(content)}</span>
        </div>
      );
    } else {
      elements.push(<div key={key++} style={{ marginBottom: "2px" }}>{parseInline(line)}</div>);
    }
  }
  return elements;
}

function formatIcon(format, channel) {
  /** Pick a compact visual cue for the collateral card. */
  if (channel === "whatsapp") return MessageCircle;
  if (channel === "instagram_reel" || format === "video") return Video;
  return FileText;
}

function SalesCollateralPage({ user }) {
  /** Show salespeople downloadable collateral and admin-only collateral management. */
  const isAdmin = user?.role === "admin" || user?.username === "pradip";
  const [collaterals, setCollaterals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [channelFilter, setChannelFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [form, setForm] = useState(INITIAL_FORM);
  // { [id]: string } — caption currently being edited per card
  const [editingCaptions, setEditingCaptions] = useState({});
  // { [id]: boolean } — saving state per card
  const [savingCaption, setSavingCaption] = useState({});

  async function loadCollaterals() {
    /** Refresh the collateral library from the backend. */
    setLoading(true);
    setError("");

    try {
      const response = await getSalesCollaterals();
      if (!response?.success) {
        throw new Error(response?.detail || "Unable to load collateral library.");
      }
      setCollaterals(response.collaterals || []);
    } catch (err) {
      setError(err.message || "Unable to load collateral library.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadCollaterals();
  }, []);

  const filteredCollaterals = useMemo(() => {
    /** Apply sales-friendly filtering without mutating the original API rows. */
    const normalizedSearch = search.trim().toLowerCase();

    return collaterals.filter((item) => {
      const matchesChannel =
        channelFilter === "all" || item.channel === channelFilter;
      const searchableText = [
        item.title,
        item.description,
        item.caption,
        item.audience,
      ]
        .join(" ")
        .toLowerCase();

      return (
        matchesChannel &&
        (!normalizedSearch || searchableText.includes(normalizedSearch))
      );
    });
  }, [collaterals, channelFilter, search]);

  async function handleSubmit(event) {
    /** Save a new collateral row for sales users to consume. */
    event.preventDefault();
    setSaving(true);
    setError("");
    setMessage("");

    try {
      const response = await createSalesCollateral({
        ...form,
        display_order: Number(form.display_order || 999),
      });
      if (!response?.success) {
        throw new Error(response?.detail || "Unable to save collateral.");
      }
      setMessage("Sales collateral saved.");
      setForm(INITIAL_FORM);
      await loadCollaterals();
    } catch (err) {
      setError(err.message || "Unable to save collateral.");
    } finally {
      setSaving(false);
    }
  }

  async function handleFileUpload(event) {
    /** Upload a selected collateral asset and populate the public URL field. */
    const selectedFile = event.target.files?.[0];
    if (!selectedFile) return;

    setUploading(true);
    setError("");
    setMessage("");

    try {
      const response = await uploadSalesCollateralFile(
        selectedFile,
        form.channel,
      );
      if (!response?.success) {
        throw new Error(response?.detail || "Unable to upload collateral file.");
      }
      setForm((prev) => ({
        ...prev,
        asset_url: response.asset_url || prev.asset_url,
        format: response.format || prev.format,
      }));
      setMessage("Collateral file uploaded. Review details and save.");
    } catch (err) {
      setError(err.message || "Unable to upload collateral file.");
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  async function handleDelete(collateralId) {
    /** Remove a collateral row from the active sales library. */
    setError("");
    setMessage("");

    try {
      const response = await deleteSalesCollateral(collateralId);
      if (!response?.success) {
        throw new Error(response?.detail || "Unable to delete collateral.");
      }
      setMessage("Sales collateral deleted.");
      await loadCollaterals();
    } catch (err) {
      setError(err.message || "Unable to delete collateral.");
    }
  }

  async function startEditCaption(item) {
    setEditingCaptions((prev) => ({ ...prev, [item.id]: item.caption || "" }));
  }

  async function saveCaption(item) {
    const newCaption = editingCaptions[item.id] ?? item.caption;
    setSavingCaption((prev) => ({ ...prev, [item.id]: true }));
    setError("");
    try {
      const response = await updateSalesCollateral(item.id, { caption: newCaption });
      if (!response?.success) throw new Error(response?.detail || "Save failed.");
      setMessage("Caption saved.");
      setEditingCaptions((prev) => { const n = { ...prev }; delete n[item.id]; return n; });
      await loadCollaterals();
    } catch (err) {
      setError(err.message || "Unable to save caption.");
    } finally {
      setSavingCaption((prev) => ({ ...prev, [item.id]: false }));
    }
  }

  async function shareToWhatsApp(item) {
    /**
     * Share image + caption to WhatsApp.
     *
     * On mobile (Web Share API with file support): fetches the image as a blob,
     * creates a File object, and invokes navigator.share() — the native share
     * sheet appears with WhatsApp as an option.
     *
     * On desktop (no file-share support): opens wa.me with the caption + image
     * URL as text so the user can paste it into WhatsApp Web.
     */
    const caption = item.caption || item.title || "";
    const imageUrl = item.asset_url || "";

    // Try native Web Share API with image (works on iOS Safari, Android Chrome)
    if (navigator.canShare && imageUrl) {
      try {
        const response = await fetch(imageUrl);
        const blob = await response.blob();
        const ext = blob.type.includes("png") ? "png" : blob.type.includes("pdf") ? "pdf" : "jpg";
        const file = new File([blob], `likhapoha-${item.id || "card"}.${ext}`, { type: blob.type });
        if (navigator.canShare({ files: [file] })) {
          await navigator.share({
            title: item.title || "Likha Poha AI",
            text: caption,
            files: [file],
          });
          return;
        }
      } catch {
        // Fall through to text-only share
      }
    }

    // Text-only Web Share API fallback
    if (navigator.share) {
      try {
        await navigator.share({
          title: item.title || "Likha Poha AI",
          text: imageUrl ? `${caption}\n\n${imageUrl}` : caption,
        });
        return;
      } catch {
        // User cancelled or not supported — fall through to wa.me
      }
    }

    // Desktop fallback: open WhatsApp Web with caption + image URL
    const waText = imageUrl ? `${caption}\n\n${imageUrl}` : caption;
    window.open(`https://wa.me/?text=${encodeURIComponent(waText)}`, "_blank");
  }

  async function copyCaption(text) {
    /** Copy the prepared sales message so it can be pasted into WhatsApp or Instagram. */
    if (!text) return;

    try {
      await navigator.clipboard.writeText(text);
      setMessage("Caption copied.");
    } catch {
      setError("Copy failed. Select the caption text and copy it manually.");
    }
  }

  return (
    <div className="sales-collateral-page page-section">
      <section className="sales-collateral-hero premium-card">
        <div>
          <p className="eyebrow">Sales enablement</p>
          <h2>Collateral Library</h2>
          <p>
            Download WhatsApp creatives, Instagram reels, brochures, and demo
            scripts approved for prospect communication.
          </p>
        </div>
        <div className="sales-collateral-hero-metrics">
          <span>{collaterals.length} total assets</span>
          <span>{filteredCollaterals.length} visible now</span>
        </div>
      </section>

      {message && <div className="success-banner">{message}</div>}
      {error && <div className="error-banner">{error}</div>}

      {isAdmin && (
        <section className="sales-form-card sales-collateral-admin">
          <div>
            <p className="eyebrow">Admin upload</p>
            <h3>Add Sales Collateral</h3>
            <p>
              Store a downloadable link and ready-to-send caption for the sales
              team. Draft assets stay hidden from salesperson logins.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="sales-collateral-form">
            <label>
              Title
              <input
                value={form.title}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, title: event.target.value }))
                }
                placeholder="Grade 9 SOF launch WhatsApp poster"
                required
              />
            </label>

            <label>
              Channel
              <select
                value={form.channel}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, channel: event.target.value }))
                }
              >
                {CHANNEL_OPTIONS.filter((option) => option.value !== "all").map(
                  (option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  )
                )}
              </select>
            </label>

            <label>
              Audience
              <select
                value={form.audience}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, audience: event.target.value }))
                }
              >
                {AUDIENCE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Format
              <select
                value={form.format}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, format: event.target.value }))
                }
              >
                {FORMAT_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Upload File
              <input
                type="file"
                accept="image/*,video/mp4,video/webm,video/quicktime,application/pdf,text/plain"
                onChange={handleFileUpload}
                disabled={uploading}
              />
                <small className="field-help">
                  {uploading
                    ? "Uploading to Supabase Storage..."
                    : "Uploads fill the public link automatically. Max 100 MB."}
                </small>
            </label>

            <label>
              Asset URL
              <input
                value={form.asset_url}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, asset_url: event.target.value }))
                }
                placeholder="https://..."
              />
            </label>

            <label>
              Thumbnail URL
              <input
                value={form.thumbnail_url}
                onChange={(event) =>
                  setForm((prev) => ({
                    ...prev,
                    thumbnail_url: event.target.value,
                  }))
                }
                placeholder="Optional preview image"
              />
            </label>

            <label>
              Display Order
              <input
                type="number"
                min="1"
                value={form.display_order}
                onChange={(event) =>
                  setForm((prev) => ({
                    ...prev,
                    display_order: event.target.value,
                  }))
                }
              />
            </label>

            <label>
              Status
              <select
                value={form.status}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, status: event.target.value }))
                }
              >
                <option value="active">Active</option>
                <option value="draft">Draft</option>
                <option value="archived">Archived</option>
              </select>
            </label>

            <label className="wide-field">
              Short Description
              <textarea
                value={form.description}
                onChange={(event) =>
                  setForm((prev) => ({
                    ...prev,
                    description: event.target.value,
                  }))
                }
                placeholder="Where and when this collateral should be used."
              />
            </label>

            <label className="wide-field">
              WhatsApp / Reel Caption
              <textarea
                value={form.caption}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, caption: event.target.value }))
                }
                placeholder={`Use WhatsApp formatting:\n*bold text*\n_italic text_\n- bullet item\n• bullet item`}
              />
              <small className="field-help">
                *bold* · _italic_ · ~strikethrough~ · Start lines with • or - for bullets
              </small>
            </label>

            <button type="submit" className="primary-btn" disabled={saving}>
              <Plus size={18} />
              {saving ? "Saving..." : "Add Collateral"}
            </button>
          </form>
        </section>
      )}

      <section className="sales-collateral-toolbar premium-card">
        <div className="sales-demo-selector">
          {CHANNEL_OPTIONS.map((option) => (
            <button
              key={option.value}
              className={channelFilter === option.value ? "active" : ""}
              onClick={() => setChannelFilter(option.value)}
            >
              {option.label}
            </button>
          ))}
        </div>
        <input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search title, audience, or caption"
        />
      </section>

      <section className="sales-collateral-grid">
        {loading && <div className="sales-empty-state">Loading collateral...</div>}

        {!loading && filteredCollaterals.length === 0 && (
          <div className="sales-empty-state">
            No collateral found. Ask admin to add WhatsApp, reel, brochure, or
            demo script assets.
          </div>
        )}

        {filteredCollaterals.map((item) => {
          const Icon = formatIcon(item.format, item.channel);

          return (
            <article key={item.id || item.title} className="sales-collateral-card">
              {item.thumbnail_url ? (
                <img src={item.thumbnail_url} alt="" />
              ) : (
                <div className="sales-collateral-placeholder">
                  <Icon size={34} />
                </div>
              )}

              <div className="sales-collateral-card-body">
                <div className="sales-collateral-card-top">
                  <span>{channelLabel(item.channel)}</span>
                  <span>{item.audience}</span>
                  {isAdmin && <span>{item.status}</span>}
                </div>

                <h3>{item.title}</h3>
                {item.description && <p>{item.description}</p>}

                {/* Admin inline caption editor */}
                {isAdmin && editingCaptions[item.id] !== undefined ? (
                  <div className="sales-collateral-caption">
                    <strong>Edit Caption</strong>
                    <small style={{ display: "block", color: "var(--muted)", fontSize: ".74rem", margin: "4px 0 2px" }}>
                      *bold* · _italic_ · ~strikethrough~ · Start lines with • or - for bullets
                    </small>
                    <textarea
                      value={editingCaptions[item.id]}
                      onChange={(e) =>
                        setEditingCaptions((prev) => ({ ...prev, [item.id]: e.target.value }))
                      }
                      rows={10}
                      style={{ width: "100%", fontFamily: "monospace", fontSize: ".84rem",
                               padding: "8px", borderRadius: "8px", border: "1px solid var(--border)",
                               resize: "vertical", marginTop: "6px" }}
                    />
                    <div style={{ display: "flex", gap: "8px", marginTop: "8px" }}>
                      <button
                        type="button"
                        className="primary-btn"
                        style={{ padding: "6px 16px", fontSize: ".82rem" }}
                        onClick={() => saveCaption(item)}
                        disabled={savingCaption[item.id]}
                      >
                        {savingCaption[item.id] ? "Saving…" : "Save Caption"}
                      </button>
                      <button
                        type="button"
                        className="secondary-btn"
                        style={{ padding: "6px 14px", fontSize: ".82rem" }}
                        onClick={() =>
                          setEditingCaptions((prev) => { const n = { ...prev }; delete n[item.id]; return n; })
                        }
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    {item.caption && (
                      <div className="sales-collateral-caption">
                        <strong>Caption</strong>
                        <div style={{ fontSize: ".84rem", lineHeight: 1.55, marginTop: "6px" }}>
                          {renderCaption(item.caption)}
                        </div>
                      </div>
                    )}
                    {isAdmin && (
                      <button
                        type="button"
                        style={{ fontSize: ".78rem", background: "none", border: "1px solid var(--border)",
                                 borderRadius: "6px", padding: "4px 10px", cursor: "pointer",
                                 color: "var(--muted)", marginBottom: "8px" }}
                        onClick={() => startEditCaption(item)}
                      >
                        ✏️ Edit Caption
                      </button>
                    )}
                  </>
                )}

                <div className="sales-collateral-actions">
                  <button
                    type="button"
                    onClick={() => shareToWhatsApp(item)}
                    style={{background:"#25D366",color:"#fff",border:"none"}}
                    title="Share to WhatsApp — downloads image + opens WhatsApp on mobile"
                  >
                    <MessageCircle size={17} />
                    Share on WhatsApp
                  </button>

                  <button
                    type="button"
                    onClick={() => copyCaption(item.caption)}
                    disabled={!item.caption}
                  >
                    <Copy size={17} />
                    Copy Caption
                  </button>

                  {item.asset_url ? (
                    <a
                      href={item.asset_url}
                      target="_blank"
                      rel="noreferrer"
                      download
                    >
                      <Download size={17} />
                      Download
                    </a>
                  ) : (
                    <button type="button" disabled>
                      <ExternalLink size={17} />
                      No File
                    </button>
                  )}

                  {isAdmin && (
                    <button
                      type="button"
                      className="danger-link-button"
                      onClick={() => handleDelete(item.id)}
                    >
                      <Trash2 size={17} />
                      Delete
                    </button>
                  )}
                </div>
              </div>
            </article>
          );
        })}
      </section>
    </div>
  );
}

export default SalesCollateralPage;
