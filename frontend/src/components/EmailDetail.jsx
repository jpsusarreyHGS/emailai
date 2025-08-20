import React, { useState } from "react";
import Field from "./FIeld";


/** Map % → color class for the score chip */
function scoreClassByPercent(value /* 0..100 */) {
  if (typeof value !== "number") return "score";
  if (value <= 30) return "score bad";     // red
  if (value <= 60) return "score mid";     // orange
  return "score good";                      // green
}

export default function EmailDetail({ ticket, onSave, onSend, onBack, onSimReply }) {
  const [draft, setDraft] = useState(ticket?.draft_reply?.body || "");
  const isClosed = ticket.status === "sent";

  const conf  = ticket.scores?.confidence ?? 0;  // 0..100
  const dup   = ticket.scores?.dup_score  ?? 0;  // 0..100
  const fraud = ticket.scores?.fraud_score ?? 0; // 0..100

  return (
    <div>
      {/* Title + status */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
        <h2 style={{ margin: 0 }}>{ticket.subject}</h2>
        <span className={`badge ${isClosed ? "success" : ""}`}>{ticket.status}</span>
      </div>
      <div className="sub" style={{ marginBottom: 16 }}>
        {ticket.sender?.name} &lt;{ticket.sender?.email}&gt; • {new Date(ticket.received_at).toLocaleString()}
      </div>

      <div className="grid">
        {/* Images */}
        <div className="card">
          <h3>Images</h3>
          <div className="grid" style={{ gridTemplateColumns: "1fr 1fr" }}>
            {ticket.attachments?.map((a, i) => (
              <img
                key={i}
                src={a.sasUrl || "https://via.placeholder.com/600x800?text=No+Image"}
                alt=""
                style={{ width: "100%", borderRadius: 8, border: "1px solid #1f2937" }}
              />
            ))}
          </div>
        </div>

        {/* Extracted + Scores */}
        <div className="card">
          <h3>Extracted Data</h3>
          <Field label="Merchant"   value={ticket.extracted?.merchant} />
          <Field label="Date"       value={ticket.extracted?.date} />
          <Field label="Total"      value={ticket.extracted?.total} />
          <Field label="Model"      value={ticket.extracted?.model} />
          <Field label="Store #"    value={ticket.extracted?.storeNumber} />

          <hr style={{ margin: "12px 0", borderColor: "#1f2937" }} />
          <h3>Scores</h3>
          <div style={{ marginTop: 8 }}>
            <span className={scoreClassByPercent(conf)}>Confidence {fmt(conf)}</span>
            <span className={scoreClassByPercent(dup)}>Dup {fmt(dup)}</span>
            <span className={scoreClassByPercent(fraud)}>Fraud {fmt(fraud)}</span>
          </div>
        </div>

        {/* Original Email */}
        <div className="card" style={{ gridColumn: "1 / -1" }}>
          <h3>Original Email</h3>
          <pre style={{ whiteSpace: "pre-wrap", fontFamily: "inherit" }}>{ticket.email_body || "—"}</pre>
        </div>

        {/* Draft + actions */}
        <div className="card" style={{ gridColumn: "1 / -1" }}>
          <h3>Draft Response</h3>
          <textarea value={draft} onChange={(e)=>setDraft(e.target.value)} disabled={isClosed}/>
          <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
            {!isClosed ? (
              <>
                <button className="btn gray" onClick={()=>onSave(ticket.id, draft)}>Save</button>
                <button className="btn" onClick={()=>onSend(ticket.id, draft)}>Send</button>
                <button className="btn secondary" onClick={onBack}>Back to Home</button>
              </>
            ) : (
              <>
                <button className="btn secondary" onClick={onBack}>Go Home</button>
                <button className="btn gray" onClick={()=>onSimReply(ticket.id)}>Simulate Customer Reply</button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function fmt(n){ 
  if (typeof n !== "number") return "—";
  const v = Math.max(0, Math.min(100, Math.round(n)));
  return `${v}%`;
}
