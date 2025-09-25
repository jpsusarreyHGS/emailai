import React, { useState } from "react";
import Field from "./FIeld";

function scoreClassByPercent(v) {
  if (typeof v !== "number") return "score";
  if (v <= 30) return "score bad";
  if (v <= 60) return "score mid";
  return "score good";
}

const API_BASE = "http://localhost:7071/api";

export default function EmailDetail({ ticket, onSave, onSend, onBack, onSimReply, onRefresh, sending }) {
  const [draft, setDraft] = useState(ticket?.draft_reply?.body || "");
  const [edits] = useState({}); // extracted fields are read-only now
  const [isGenerating, setIsGenerating] = useState(false);
  const [progress, setProgress] = useState(0); // 0-100
  const [pressed, setPressed] = useState(false);
  const [lightboxUrl, setLightboxUrl] = useState(null);
  const isClosed = ticket.status === "sent";

  const conf = ticket.overall_confidence ?? ticket.scores?.confidence ?? 0;
  const dup = ticket.overall_duplication ?? ticket.scores?.duplication ?? 0;

  // Small helper to animate progress smoothly to a target
  function animateTo(target) {
    setProgress((prev) => {
      const clamped = Math.max(prev, Math.min(100, target));
      return clamped;
    });
  }

  // Handle Generate button
  async function handleGenerate() {
    if (isGenerating) return;
    try {
      setIsGenerating(true);
      setPressed(true);
      animateTo(10);
      setTimeout(() => setPressed(false), 120); // quick press animation

      console.log("Step 1: Running OCR...");
      // 🔹 OCR call
      const ocrRes = await fetch(`${API_BASE}/emails/${ticket.id}/attachments/ocr`, {
        method: "POST",
      });
      if (!ocrRes.ok) throw new Error("OCR failed");
      const ocrData = await ocrRes.json();
      console.log("OCR response:", ocrData);
      animateTo(40);

      console.log("Step 2: Running Draft...");
      // 🔹 Draft call
      const draftRes = await fetch(`${API_BASE}/emails/${ticket.id}/draft`, {
        method: "POST",
      });
      if (!draftRes.ok) throw new Error("Draft failed");
      const draftData = await draftRes.json();
      console.log("Draft response:", draftData);
      animateTo(80);

      // 🔹 Fetch updated ticket
      const fetchRes = await fetch(`${API_BASE}/emails/${ticket.id}/fetch`);
      if (!fetchRes.ok) throw new Error("Fetch failed");
      const freshDoc = await fetchRes.json();
      console.log("Updated ticket:", freshDoc);
      animateTo(100);

      // Map attachments and extracted data
      const atts = (freshDoc.attachments || []).map((a, i) => ({
        sasUrl: a.blobPath || `mock/blob/${i}`,
        blob: a.blobPath || `mock/blob/${i}`,
        name: a.name || a.filename || `attachment_${i}`,
        ocr: a.ocr || null,
      }));
      console.log("Fresh attachments from DB:", atts);
      let extracted = { merchant: null, date: null, total: null, model: null, store_number: null };
      let scores = { confidence: 0, duplication: 0 };
      for (const a of atts) {
        if (a.ocr && a.ocr.text) {
          console.log("Processing OCR text:", a.ocr.text);
          try {
            const parsed = JSON.parse(a.ocr.text);
            console.log("Parsed OCR JSON:", parsed);
            extracted = {
              merchant: parsed.merchant ?? null,
              date: parsed.date ?? null,
              total: parsed.total ?? null,
              model: parsed.model ?? null,
              store_number: parsed.store_number ?? null,
            };
            scores = {
              confidence: typeof parsed.confidence_score === 'number' ? parsed.confidence_score : parseInt(parsed.confidence_score || 0, 10) || 0,
              duplication: typeof parsed.duplication_score === 'number' ? parsed.duplication_score : parseInt(parsed.duplication_score || 0, 10) || 0,
            };
            console.log("Mapped extracted:", extracted);
            console.log("Mapped scores:", scores);
            break;
          } catch (e) {
            console.error("Failed to parse OCR JSON:", e, "Raw text:", a.ocr.text);
          }
        }
      }

      console.log("Final extracted data:", extracted);
      console.log("Final scores:", scores);
      if (onRefresh) onRefresh({ 
        ...freshDoc, 
        attachments: atts, 
        extracted, 
        scores,
        overall_confidence: freshDoc.overall_confidence,
        overall_duplication: freshDoc.overall_duplication
      });
      setDraft(freshDoc.draft_reply?.body || "");
    } catch (err) {
      console.error("Generate failed:", err);
      alert("Error generating OCR + Draft");
    } finally {
      // Let the user see the 100% bar briefly, then reset
      setTimeout(() => {
        setIsGenerating(false);
        setProgress(0);
      }, 400);
    }
  }

  function openLightbox(url) {
    setLightboxUrl(url);
    const onEsc = (e) => { if (e.key === 'Escape') closeLightbox(); };
    window.addEventListener('keydown', onEsc, { once: true });
  }

  function closeLightbox() {
    setLightboxUrl(null);
  }

  return (
    <div>
      {/* Title + status */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
        <h2 style={{ margin: 0 }}>{ticket.subject}</h2>
        <span className={`badge ${isClosed ? "success" : ""}`}>{ticket.status}</span>
      </div>
      <div className="sub" style={{ marginBottom: 10 }}>
        {ticket.sender?.name} &lt;{ticket.sender?.email}&gt; •{" "}
        {new Date(ticket.received_at).toLocaleString()}
      </div>
      <div className="meta-row" style={{ marginBottom: 16 }}>
        {ticket.assignee?.name && (
          <span className="pill assignee">Assigned: {ticket.assignee.name}</span>
        )}
        {!!(ticket.tags && ticket.tags.length) && (
          <span className="pill tagline">
            {ticket.tags.map((t, i) => (
              <span key={i} className="pill tag">
                {t}
              </span>
            ))}
          </span>
        )}
      </div>

      <div className="grid">
        {/* Images */}
        <div className="card">
          <h3>Images</h3>
          <div className="grid" style={{ gridTemplateColumns: "1fr 1fr" }}>
            {ticket.attachments?.map((a, i) => (
              <img
                key={i}
                src={a.sasUrl ? imageProxyUrl(a.sasUrl) : "https://via.placeholder.com/240?text=No+Image"}
                alt={a.name || `Attachment ${i}`}
                onClick={() => a.sasUrl && openLightbox(imageProxyUrl(a.sasUrl))}
                style={{
                  width: 240,
                  height: 240,
                  objectFit: "contain",
                  borderRadius: 8,
                  border: "1px solid #1f2937",
                  cursor: a.sasUrl ? 'zoom-in' : 'default'
                }}
              />
            ))}
          </div>
        </div>

            {/* Extracted Data for each attachment */}
            {ticket.attachments?.map((attachment, index) => {
              let extracted = { merchant: null, date: null, total: null, model: null, store_number: null };
              if (attachment.ocr && attachment.ocr.text) {
                try {
                  const parsed = JSON.parse(attachment.ocr.text);
                  extracted = {
                    merchant: parsed.merchant ?? null,
                    date: parsed.date ?? null,
                    total: parsed.total ?? null,
                    model: parsed.model ?? null,
                    store_number: parsed.store_number ?? null,
                  };
                } catch (e) {
                  console.error("Failed to parse OCR JSON for attachment", index, e);
                }
              }
              
              return (
                <div key={index} className="card">
                  <h3>Extracted Data - {attachment.name || `Attachment ${index + 1}`}</h3>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                    <Field label="Merchant" value={extracted.merchant} />
                    <Field label="Date" value={extracted.date} />
                    <Field label="Total" value={extracted.total} />
                    <Field label="Model" value={extracted.model} />
                    <Field label="Store #" value={extracted.store_number} />
                  </div>
                </div>
              );
            })}

            {/* Overall Scores */}
            <div className="card">
              <h3>Overall Scores</h3>
              <div style={{ marginTop: 8 }}>
                <span className={scoreClassByPercent(conf)}>Confidence {fmt(conf)}</span>
                <span className={scoreClassByPercent(dup)}>Dup {fmt(dup)}</span>
              </div>
            </div>

        {/* Original Email */}
        <div className="card" style={{ gridColumn: "1 / -1" }}>
          <h3>Original Email</h3>
          <pre style={{ whiteSpace: "pre-wrap", fontFamily: "inherit" }}>
            {ticket.email_body || "—"}
          </pre>
        </div>

        {/* Draft + actions */}
        <div className="card" style={{ gridColumn: "1 / -1" }}>
          <h3>Draft Response</h3>
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            disabled={isClosed}
          />
          <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap", justifyContent: "space-between" }}>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {!isClosed ? (
                <>
                  <button className="btn gray" onClick={() => onSave(ticket.id, draft)}>
                    Save
                  </button>
                  <button 
                    className="btn" 
                    onClick={() => onSend(ticket.id, draft)}
                    disabled={sending}
                    style={{ 
                      cursor: sending ? 'not-allowed' : 'pointer',
                      opacity: sending ? 0.6 : 1
                    }}
                  >
                    {sending ? 'Sending...' : 'Send'}
                  </button>
                  <button className="btn secondary" onClick={onBack}>
                    Back to Home
                  </button>
                </>
              ) : (
                <>
                  <button className="btn secondary" onClick={onBack}>
                    Go Home
                  </button>
                  <button className="btn gray" onClick={() => onSimReply(ticket.id)}>
                    Simulate Customer Reply
                  </button>
                </>
              )}
            </div>
            {/* Generate button with progress/press animation */}
            <button
              className="btn"
              onClick={handleGenerate}
              disabled={isGenerating}
              style={{
                position: "relative",
                overflow: "hidden",
                backgroundColor: isGenerating ? "#1d4ed8" : "#2563eb",
                color: "white",
                transform: pressed ? "translateY(1px)" : "translateY(0)",
                boxShadow: pressed ? "inset 0 2px 4px rgba(0,0,0,0.2)" : "none",
                width: 140,
              }}
            >
              <span
                style={{
                  position: "absolute",
                  left: 0,
                  top: 0,
                  bottom: 0,
                  width: `${progress}%`,
                  background: "rgba(255,255,255,0.2)",
                  transition: "width 240ms ease",
                }}
              />
              <span style={{ position: "relative" }}>
                {isGenerating ? `Generating ${progress}%` : "Generate"}
              </span>
            </button>
          </div>
        </div>
      </div>

      {/* Lightbox */}
      {lightboxUrl && (
        <div
          onClick={closeLightbox}
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.75)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50
          }}
        >
          <img
            src={lightboxUrl}
            alt="Attachment"
            style={{ maxWidth: '90vw', maxHeight: '90vh', borderRadius: 8, boxShadow: '0 10px 30px rgba(0,0,0,0.5)' }}
            onClick={(e) => e.stopPropagation()}
          />
          <button
            onClick={closeLightbox}
            style={{ position: 'fixed', top: 16, right: 16, background: '#111827', color: '#e5e7eb', border: '1px solid #374151', borderRadius: 6, padding: '8px 12px' }}
          >
            Close
          </button>
        </div>
      )}

    </div>
  );
}

function fmt(n) {
  if (typeof n !== "number") return "—";
  const v = Math.max(0, Math.min(100, Math.round(n)));
  return `${v}%`;
}

function LabeledInput({ label, value, onChange }) {
  return (
    <div>
      <div style={{ fontSize: 12, color: "#9ca3af", marginBottom: 4 }}>{label}</div>
      <input
        value={value ?? ""}
        onChange={(e) => onChange?.(e.target.value)}
        style={{
          width: "100%",
          padding: "8px 10px",
          borderRadius: 6,
          border: "1px solid #1f2937",
          background: "#0b1220",
          color: "#e5e7eb",
        }}
      />
    </div>
  );
}

function imageProxyUrl(ref) {
  // If ref is already a full URL, return it as-is
  if (ref.startsWith("http://") || ref.startsWith("https://")) return ref;
  // Otherwise, ref is like "<emailId>/filename.jpg" in default container
  // Build proxy URL: /api/attachments/<container>/<blob_path>
  const container = import.meta.env.VITE_EMAIL_BLOB_CONTAINER || 'email-attachments';
  return `${API_BASE}/attachments/${container}/${encodeURI(ref)}`;
}
