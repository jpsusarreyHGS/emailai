export default function Field({ label, value }) {
  return (
    <div className="field-row">
      <div className="field-label" style={{ color: "#9aa4b2", fontSize: 12 }}>{label}</div>
      <div className="field-value" style={{ fontSize: 14 }}>{value || "—"}</div>
    </div>
  );
}
