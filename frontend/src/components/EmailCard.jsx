import React from "react";

function EmailCard({ email }) {
  return (
    <div className="email-card">
      <strong>{email.subject}</strong>
      <p>{email.body}</p>
    </div>
  );
}

export default EmailCard;
