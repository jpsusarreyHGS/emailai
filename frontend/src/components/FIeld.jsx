import React from "react";
export default function Field({ label, value }) {
  return (
    <div style={{ display: "flex", gap: 8, fontSize: 14, margin: "4px 0" }}>
      <div style={{ width: 120, color: "#9ca3af" }}>{label}</div>
      <div>{value ?? "—"}</div>
    </div>
  );
}
