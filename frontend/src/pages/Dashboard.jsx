import React, { useMemo, useState } from "react";
import "./Dashboard.css";
import EmailList from "../components/EmailList";
import EmailDetail from "../components/EmailDetail";

export default function Dashboard() {
  // Seed mock incoming emails
  const [incomingEmails, setIncomingEmails] = useState([
    {
      id: "EML-1001",
      subject: "Warranty Request: Store #123 (ZX100)",
      from: { name: "Jane Doe", email: "jane@example.com" },
      body:
        "Hi team,\n\nAttaching receipt for ZX100.\nStore: BB-0421, Total: $1299.99.\n\nThanks,\nJane",
      attachments: [
        "https://via.placeholder.com/600x800?text=Receipt+1",
        "https://via.placeholder.com/600x800?text=Receipt+2",
      ],
      received_at: new Date().toISOString(),
      messageId: "msg-1001",
    },
    {
      id: "EML-1002",
      subject: "Warranty Request: QX55",
      from: { name: "Mark Lee", email: "mark@example.com" },
      body: "Hello, re-sending clearer photo.\nTotal: $249.50",
      attachments: ["https://via.placeholder.com/600x800?text=Receipt+Blurry"],
      received_at: new Date().toISOString(),
      messageId: "msg-1002",
    },
  ]);

  // Tickets are created from incoming emails
  const [tickets, setTickets] = useState([]);
  const [selected, setSelected] = useState(null);

  const openTickets = useMemo(
    () => tickets.filter((t) => t.status !== "sent"),
    [tickets]
  );
  const closedTickets = useMemo(
    () => tickets.filter((t) => t.status === "sent"),
    [tickets]
  );

  // Build a ticket from an email (with simple idempotency key)
  function mkTicketFromEmail(em) {
    const attachKeys = (em.attachments || []).join("|");
    const ingestionKey = `${em.messageId}|${attachKeys}`;
    const exists = tickets.find((t) => t.ingestionKey === ingestionKey);
    if (exists) return exists;

    const model = em.subject.match(/ZX100|QX55/)?.[0] || "—";

    // Defaults (edit here if you want ZX100 to start with specific scores)
    const defaultScores =
      model === "ZX100"
        ? { confidence: 92, dup_score: 36, fraud_score: 8 }
        : { confidence: 92, dup_score: 12, fraud_score: 8 };  

    const t = {
      id: `TKT-${Math.random().toString(16).slice(2, 8).toUpperCase()}`,
      ingestionKey,
      email_id: em.id,
      subject: em.subject,
      sender: em.from,
      received_at: em.received_at,
      status: "awaiting_review",
      email_body: em.body,
      attachments: em.attachments.map((url, i) => ({
        sasUrl: url,
        blob: `mock/blob/${i}`,
      })),
      extracted: {
        merchant: em.body.includes("BB") ? "Best Buy" : "Unknown",
        date: new Date().toISOString().slice(0, 10),
        total: em.body.includes("$1299.99") ? 1299.99 : 249.5,
        model,
        storeNumber: em.body.match(/BB-\d{4}/)?.[0] || "—",
      },
      // store percentages (0–100)
      scores: defaultScores,
      validation: { status: "pass", rules_passed: ["merchant_known"], rules_failed: [] },
      draft_reply: {
        template: "approve",
        body:
          `Hi ${em.from.name || "Customer"},\n\n` +
          `We verified your purchase for ${tModel(em)}. Your warranty claim is approved.\n\nBest,\nSupport`,
      },
      thread: [
        {
          id: em.messageId,
          direction: "in",
          subject: em.subject,
          body: em.body,
          at: em.received_at,
        },
      ],
    };
    return t;

    function tModel(e) {
      const m = e.subject.match(/ZX100|QX55/);
      return m ? m[0] : "your product";
    }
  }

  // Create ticket when an incoming email is clicked
  const handleOpenIncoming = (emailId) => {
    const em = incomingEmails.find((e) => e.id === emailId);
    if (!em) return;
    const t = mkTicketFromEmail(em);

    setTickets((prev) => {
      if (prev.find((x) => x.ingestionKey === t.ingestionKey)) return prev;
      return [t, ...prev];
    });
    setIncomingEmails((prev) => prev.filter((e) => e.id !== em.id));
    setSelected(t);
  };

  const handleOpenTicket = (ticketId) => {
    const t = tickets.find((x) => x.id === ticketId);
    if (t) setSelected(t);
  };

  // Save keeps it open
  const handleSave = (ticketId, draftBody) => {
    setTickets((prev) =>
      prev.map((t) =>
        t.id === ticketId ? { ...t, draft_reply: { ...t.draft_reply, body: draftBody } } : t
      )
    );
  };

  // Send → Closed
  const handleSend = (ticketId, draftBody) => {
    setTickets((prev) =>
      prev.map((t) =>
        t.id === ticketId ? { ...t, status: "sent", draft_reply: { ...t.draft_reply, body: draftBody } } : t
      )
    );
    setSelected(null);
  };

  // Simulate customer reply → reopen same ticket
  const handleSimulateReply = (ticketId) => {
    setTickets((prev) =>
      prev.map((t) =>
        t.id === ticketId
          ? {
              ...t,
              status: "awaiting_review",
              thread: [
                ...t.thread,
                {
                  id: `reply-${Date.now()}`,
                  direction: "in",
                  subject: `Re: ${t.subject}`,
                  body: "Customer: thanks!",
                  at: new Date().toISOString(),
                },
              ],
            }
          : t
      )
    );
    setSelected(null);
  };

  const handleBackHome = () => setSelected(null);

  return (
    <div className="dashboard">
      <div className="header">
        <div className="brand">
          <div className="logo"></div>
          <div>
            <div className="title">Warranty CRM</div>
            <div className="subtitle">Incoming • Open • Closed</div>
          </div>
        </div>
      </div>

      {!selected ? (
        <div className="board">
          <section className="column">
            <h2>Incoming Emails</h2>
            <EmailList
              mode="incoming"
              items={incomingEmails.map((e) => ({
                id: e.id,
                title: e.subject,
                subtitle: `${e.from?.name || ""} <${e.from.email}>`,
                at: e.received_at,
              }))}
              onOpen={handleOpenIncoming}
            />
          </section>

          <section className="column">
            <h2>Open Tickets</h2>
            <EmailList
              mode="open"
              items={openTickets.map((t) => ({
                id: t.id,
                title: `[${t.id}] ${t.subject}`,
                subtitle: `${t.sender?.name || ""} <${t.sender?.email}>`,
                at: t.received_at,
              }))}
              onOpen={handleOpenTicket}
            />
          </section>

          <section className="column">
            <h2>Closed Tickets</h2>
            <EmailList
              mode="closed"
              items={closedTickets.map((t) => ({
                id: t.id,
                title: `[${t.id}] ${t.subject}`,
                subtitle: `${t.sender?.name || ""} <${t.sender?.email}>`,
                at: t.received_at,
              }))}
              onOpen={handleOpenTicket}
            />
          </section>
        </div>
      ) : (
        <main className="detail">
          <EmailDetail
            ticket={selected}
            onSave={handleSave}
            onSend={handleSend}
            onBack={handleBackHome}
            onSimReply={handleSimulateReply}
          />
        </main>
      )}
    </div>
  );
}
