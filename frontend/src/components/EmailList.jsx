import React from "react";
import PaperclipIcon from "../assets/paperclip-icon.png";

const CATEGORY_LABELS = {
  appetite: "Appetite",
  billing: "Billing/Payment", 
  docRequest: "Document Request",
  endorsement: "Endorsement",
  underwriting: "Underwriting",
  receipt: "Proof of Purchase"
};

export default function EmailList({ items, onOpen }) {
  return (
    <ul className="list">
      {items.map((it) => (
        <li key={it.id} className="item" onClick={() => onOpen(it.id)}>
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'space-between',
            width: '100%'
          }}>
            <div style={{ flex: 1 }}>
              <div className="title">{it.title}</div>
              <div className="sub">{it.subtitle}</div>
              <div className="meta-row">
                <span className="pill time">{new Date(it.at).toLocaleString()}</span>
                {!!(it.tags && it.tags.length) && (
                  <span className="pill tagline">
                    {it.tags.map((t, i) => <span key={i} className="pill tag">{t}</span>)}
                  </span>
                )}
                {it.labels?.category && (
                  <span className="pill tag" style={{ marginLeft: '8px' }}>
                    {CATEGORY_LABELS[it.labels.category] || it.labels.category}
                  </span>
                )}
              </div>
            </div>
            {it.hasAttachments && (
              <div style={{
                marginLeft: '12px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <img 
                  src={PaperclipIcon}
                  alt="Has attachments"
                  title="Has attachments"
                  style={{ 
                    width: '24px',
                    height: '24px',
                    opacity: 0.7
                  }}
                />
              </div>
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}
