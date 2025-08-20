import React from "react";

export default function ResponseForm({ readOnly, value, onChange, onSend, onBack, status }) {
  return (
    <div>
      <textarea
        value={value}
        onChange={(e) => onChange?.(e.target.value)}
        disabled={readOnly}
      />
      <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
        {status !== "sent" ? (
          <>
            <button className="btn" onClick={onSend}>Send</button>
            <button className="btn secondary" onClick={onBack}>Back to Home</button>
          </>
        ) : (
          <button className="btn secondary" onClick={onBack}>Go Home</button>
        )}
      </div>
    </div>
  );
}
