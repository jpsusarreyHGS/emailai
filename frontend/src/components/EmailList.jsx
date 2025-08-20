import React from "react";

/** items: [{ id, title, subtitle, at }] */
export default function EmailList({ items, onOpen, mode }) {
  const empty = {
    incoming: "No incoming emails.",
    open: "No open tickets.",
    closed: "No closed tickets."
  }[mode || "incoming"];

  return (
    <ul className="list">
      {items.length === 0 && (
        <li className="item">
          <div className="title">{empty}</div>
        </li>
      )}
      {items.map(x => (
        <li key={x.id} className="item" onClick={() => onOpen(x.id)}>
          <div className="title">{x.title}</div>
          <div className="sub">{x.subtitle}</div>
          <div className="sub">{new Date(x.at).toLocaleString()}</div>
        </li>
      ))}
    </ul>
  );
}
