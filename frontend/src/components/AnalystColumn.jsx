import React from "react";
import EmailCard from "./EmailCard";

function AnalystColumn({ name, emails }) {
  return (
    <div className="analyst-column">
      <h3>{name}</h3>
      {emails.length > 0 ? (
        emails.map((email) => <EmailCard key={email.id} email={email} />)
      ) : (
        <p>No emails</p>
      )}
    </div>
  );
}

export default AnalystColumn;
