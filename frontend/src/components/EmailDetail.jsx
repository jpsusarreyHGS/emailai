import { useMemo, useState } from "react";
import EmailBody from "./EmailBody";
import Field from "./Field";

/**
 * Expects a `ticket` object with (at minimum):
 * {
 *   id, subject, received_at,
 *   from: { name, email },
 *   email_body_html?, email_body_text?,
 *   attachments?: [{ name, sasUrl? }],
 *   extracted?: { merchant, date, total, model, storeNo },
 *   scores?: { confidence, dup_score, fraud_score },
 *   draft_reply?: { subject, body },
 *   status
 * }
 *
 * Callbacks:
 *   onBack?()
 *   onSaveDraft?(updatedBody: string)
 *   onSend?()
 *   onSimulateReply?()
 */
export default function EmailDetail({
  ticket,
  onBack,
  onSaveDraft,
  onSend,
  onSimulateReply,
}) {
  const [draft, setDraft] = useState(ticket?.draft_reply?.body || "");

  const {
    confidenceColor,
    dupColor,
    fraudColor,
    confidencePct,
    dupPct,
    fraudPct,
  } = useMemo(() => {
    const c = clampPct(ticket?.scores?.confidence);
    const d = clampPct(ticket?.scores?.dup_score);
    const f = clampPct(ticket?.scores?.fraud_score);
    return {
      confidenceColor: scoreColor(c),
      dupColor: scoreColor(100 - d, true), // lower dup better → invert color logic
      fraudColor: scoreColor(100 - f, true), // lower fraud better → invert
      confidencePct: c,
      dupPct: d,
      fraudPct: f,
    };
  }, [ticket]);

  const images = (ticket?.attachments || []).filter(
    (a) =>
      a?.sasUrl &&
      (a.name?.match(/\.(png|jpe?g|gif|webp)$/i) || a.sasUrl.startsWith("http"))
  );

  return (
    <div className="detail-root">
      <div className="detail-header">
        <button className="btn ghost" onClick={onBack} aria-label="Back to board">
          ← Back
        </button>
        <div className="title-wrap">
          <h2 className="title">{ticket?.subject || "(no subject)"}</h2>
          <div className="meta">
            <span>
              From:{" "}
              <strong>
                {ticket?.from?.name || ticket?.from?.email || "Unknown"}
              </strong>
            </span>
            {ticket?.received_at && (
              <span className="dot">•</span>
            )}
            {ticket?.received_at && (
              <span>{new Date(ticket.received_at).toLocaleString()}</span>
            )}
          </div>
        </div>
        <div className="status-badge">{badgeForStatus(ticket?.status)}</div>
      </div>

      <div className="detail-grid">
        {/* Left: images */}
        <div className="card">
          <h3>Attachments</h3>
          {images.length === 0 ? (
            <div className="empty">No images</div>
          ) : (
            <div className="image-grid">
              {images.map((img, i) => (
                <a
                  key={i}
                  href={img.sasUrl}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="image-wrap"
                  title={img.name}
                >
                  <img src={img.sasUrl} alt={img.name || `attachment-${i}`} />
                </a>
              ))}
            </div>
          )}
        </div>

        {/* Right: extracted + scores */}
        <div className="card">
          <h3>Extracted Data</h3>
          <div className="fields">
            <Field label="Merchant" value={ticket?.extracted?.merchant} />
            <Field label="Date" value={ticket?.extracted?.date} />
            <Field label="Total" value={ticket?.extracted?.total} />
            <Field label="Model" value={ticket?.extracted?.model} />
            <Field label="Store #" value={ticket?.extracted?.storeNo} />
          </div>

          <div className="scores">
            <ScorePill
              label="Confidence"
              value={confidencePct}
              className={confidenceColor}
              tooltip="Overall extraction confidence (higher is better)"
            />
            <ScorePill
              label="Duplicate"
              value={dupPct}
              className={dupColor}
              tooltip="Similarity to existing receipts (lower is better)"
            />
            <ScorePill
              label="Fraud"
              value={fraudPct}
              className={fraudColor}
              tooltip="Heuristic tamper signals (lower is better)"
            />
          </div>
        </div>

        {/* Full-width: original email */}
        <div className="card" style={{ gridColumn: "1 / -1" }}>
          <h3>Original Email</h3>
          <EmailBody
            html={ticket?.email_body_html}
            text={ticket?.email_body_text || ticket?.email_body}
          />
        </div>

        {/* Full-width: draft reply */}
        <div className="card" style={{ gridColumn: "1 / -1" }}>
          <h3>Draft Response</h3>
          <textarea
            className="draft-textarea"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Type your response..."
            aria-label="Draft response"
          />
          <div className="actions">
            <button
              className="btn"
              onClick={() => onSaveDraft?.(draft)}
              disabled={!draft?.trim()}
            >
              Save
            </button>
            <button
              className="btn primary"
              onClick={onSend}
              disabled={!draft?.trim()}
            >
              Send
            </button>
            <button
              className="btn ghost"
              onClick={onSimulateReply}
              title="Simulate a customer reply (dev only)"
            >
              Simulate Reply
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ---------- helpers ---------- */

function clampPct(v) {
  if (v == null || Number.isNaN(+v)) return 0;
  // Accept 0-1 or 0-100
  const n = +v <= 1 ? +v * 100 : +v;
  return Math.max(0, Math.min(100, Math.round(n)));
}

function scoreColor(pct, inverted = false) {
  // Default: 0–30 red, 31–60 orange, 61–100 green
  // Inverted: low is good → flip thresholds meaning
  const val = inverted ? 100 - pct : pct;
  if (val <= 30) return "score-red";
  if (val <= 60) return "score-orange";
  return "score-green";
}

function ScorePill({ label, value, className, tooltip }) {
  return (
    <div className={`score-pill ${className}`} title={tooltip}>
      <span className="score-label">{label}</span>
      <span className="score-value">{clampPct(value)}%</span>
    </div>
  );
}

function badgeForStatus(status) {
  const s = (status || "").toLowerCase();
  if (s === "closed" || s === "sent") return <span className="badge badge-green">Closed</span>;
  if (s === "open" || s === "awaiting_review") return <span className="badge badge-yellow">Open</span>;
  if (s === "categorized" || s === "new") return <span className="badge badge-gray">Incoming</span>;
  return <span className="badge badge-gray">{status || "Unknown"}</span>;
}
