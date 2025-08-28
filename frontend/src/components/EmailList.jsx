import React from "react";

export default function EmailList({ items, onOpen }) {
  return (
    <ul className="list">
      {items.map((it) => (
        <li key={it.id} className="item" onClick={() => onOpen(it.id)}>
          <div className="title">{it.title}</div>
          <div className="sub">{it.subtitle}</div>
          <div className="meta-row">
            {it.assignee?.name && (
              <span className="pill assignee">Assigned: {it.assignee.name}</span>
            )}
            <span className="pill time">{new Date(it.at).toLocaleString()}</span>
          </div>
          {!!(it.tags && it.tags.length) && (
            <div className="tag-row">
              {it.tags.map((t, i) => (
                <span key={i} className="pill tag">{t}</span>
              ))}
            </div>
          )}
        </li>
      ))}
    </ul>
  );
}
