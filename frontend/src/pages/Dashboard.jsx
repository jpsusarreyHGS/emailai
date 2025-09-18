import React, { useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import HgsLogo from "../assets/HgsLogo.svg";
import EmailDetail from "../components/EmailDetail";

const ROSTER = {
  coach: { id: "coach", name: "Coach View", role: "coach" },
  alice: { id: "alice", name: "Alice", role: "analyst" },
  bob:   { id: "bob",   name: "Bob",   role: "analyst" },
  cara:  { id: "cara",  name: "Cara",  role: "analyst" },
};

// Fallback seed emails (used only if nothing is passed from SortBoard)
const DEFAULT_EMAILS = [
  {
    id: "EML-1001",
    subject: "Warranty Request: Store #123 (ZX100)",
    from: { name: "Jane Doe", email: "jane@example.com" },
    body: "Hi team,\n\nAttaching receipt for ZX100 TV.\nStore: BB-0421, Total: $1299.99.\n\nThanks,\nJane",
    attachments: [
      "https://via.placeholder.com/600x800?text=Receipt+1",
      "https://via.placeholder.com/600x800?text=Receipt+2",
    ],
    received_at: new Date().toISOString(),
    messageId: "msg-1001",
    assignee: { id: "alice", name: "Alice" },
    tags: ["TV/Screen", "Warranty"]
  },
  {
    id: "EML-1002",
    subject: "Need help: Soundbar QX55 warranty",
    from: { name: "Mark Lee", email: "mark@example.com" },
    body: "Hello, re-sending a clearer receipt for the QX55 soundbar. Total: $249.50",
    attachments: ["https://via.placeholder.com/600x800?text=Receipt+Blurry"],
    received_at: new Date().toISOString(),
    messageId: "msg-1002",
    assignee: { id: "cara", name: "Cara" },
    tags: ["Audio", "Warranty"]
  }
];

export default function Dashboard() {
  const navigate = useNavigate();
  const { state } = useLocation();

  const selectedProfile = state?.profile || ROSTER.coach;

  const seedEmails = useMemo(() => {
    if (Array.isArray(state?.emails) && state.emails.length) {
      return state.emails.map((e, idx) => ({
        id: e.id || `EML-${idx + 1}`,
        subject: e.subject,
        from: e.from || { email: "unknown@example.com" },
        body: e.body || "",
        attachments: e.attachments || [],
        received_at: e.at || new Date().toISOString(),
        messageId: e.messageId || `msg-${idx + 1}`,
        assignee: e.assignedTo
          ? { id: e.assignedTo, name: e.assignedTo[0].toUpperCase() + e.assignedTo.slice(1) }
          : undefined,
        tags: e.tags || []
      }));
    }
    return DEFAULT_EMAILS;
  }, [state]);

  const [incomingEmails, setIncomingEmails] = useState(seedEmails);
  const [tickets, setTickets] = useState([]);
  const [selected, setSelected] = useState(null);

  const visibleIncoming = useMemo(() => {
    if (selectedProfile.role === "coach") return incomingEmails;
    return incomingEmails.filter(e => e.assignee?.id === selectedProfile.id);
  }, [incomingEmails, selectedProfile]);

  const openTickets = useMemo(() => {
    const all = tickets.filter(t => t.status !== "sent");
    if (selectedProfile.role === "coach") return all;
    return all.filter(t => t.assignee?.id === selectedProfile.id);
  }, [tickets, selectedProfile]);

  const closedTickets = useMemo(() => {
    const all = tickets.filter(t => t.status === "sent");
    if (selectedProfile.role === "coach") return all;
    return all.filter(t => t.assignee?.id === selectedProfile.id);
  }, [tickets, selectedProfile]);

  function mkTicketFromEmail(em) {
    const ingestionKey = `${em.messageId}|${(em.attachments || []).join("|")}`;
    const exists = tickets.find(t => t.ingestionKey === ingestionKey);
    if (exists) return exists;

    const model = em.subject.match(/ZX100|QX55/i)?.[0]?.toUpperCase() || "—";
    const defaultScores = model === "ZX100"
      ? { confidence: 92, dup_score: 12, fraud_score: 8 }
      : { confidence: 86, dup_score: 18, fraud_score: 10 };

    const t = {
      id: `TKT-${Math.random().toString(16).slice(2, 8).toUpperCase()}`,
      ingestionKey,
      email_id: em.id,
      subject: em.subject,
      sender: em.from,
      received_at: em.received_at,
      status: "awaiting_review",
      email_body: em.body,
      attachments: (em.attachments || []).map((url, i) => ({ sasUrl: url, blob: `mock/blob/${i}` })),
      extracted: {
        merchant: em.body?.includes("BB") ? "Best Buy" : "Unknown",
        date: new Date().toISOString().slice(0, 10),
        total: em.body?.includes("$1299.99") ? 1299.99 : 249.5,
        model,
        storeNumber: em.body?.match(/BB-\d{4}/)?.[0] || "—",
      },
      scores: defaultScores,
      validation: { status: "pass", rules_passed: ["merchant_known"], rules_failed: [] },
      draft_reply: {
        template: "approve",
        body:
          `Hi ${em.from?.name || "Customer"},\n\n` +
          `We verified your ${model} purchase on ${new Date().toISOString().slice(0,10)}. ` +
          `Your warranty claim is approved.\n\nBest,\nSupport`,
      },
      thread: [
        { id: em.messageId, direction: "in", subject: em.subject, body: em.body, at: em.received_at }
      ],
      assignee: em.assignee,
      tags: em.tags || []
    };
    return t;
  }

  const handleOpenIncoming = (emailId) => {
    const em = incomingEmails.find(e => e.id === emailId);
    if (!em) return;
    const t = mkTicketFromEmail(em);

    setTickets(prev => {
      if (prev.find(x => x.ingestionKey === t.ingestionKey)) return prev;
      return [t, ...prev];
    });
    setIncomingEmails(prev => prev.filter(e => e.id !== em.id));
    setSelected(t);
  };

  const handleOpenTicket = (ticketId) => {
    const t = tickets.find(x => x.id === ticketId);
    if (t) setSelected(t);
  };

  const handleSave = (ticketId, draftBody) => {
    setTickets(prev =>
      prev.map(t => t.id === ticketId ? { ...t, draft_reply: { ...t.draft_reply, body: draftBody } } : t)
    );
  };

  const handleSend = (ticketId, draftBody) => {
    setTickets(prev =>
      prev.map(t => t.id === ticketId ? { ...t, status: "sent", draft_reply: { ...t.draft_reply, body: draftBody } } : t)
    );
    setSelected(null);
  };

  const handleSimulateReply = (ticketId) => {
    setTickets(prev =>
      prev.map(t => t.id === ticketId
        ? {
            ...t,
            status: "awaiting_review",
            thread: [
              ...t.thread,
              { id: `reply-${Date.now()}`, direction: "in", subject: `Re: ${t.subject}`, body: "Customer: thanks!", at: new Date().toISOString() }
            ]
          }
        : t
      )
    );
    setSelected(null);
  };

  const handleBackHome = () => setSelected(null);

  const viewTitle =
    selectedProfile.id === "coach"
      ? "Coach View"
      : `${selectedProfile.name} View`;

  const roleSubtitle =
    selectedProfile.id === "coach"
      ? "See all tickets across analysts"
      : "Analyst-specific view (assigned only)";

  return (
    <div className="dashboard">
      <div className="header">
        <div className="brand">
          <img className="logo" src={HgsLogo} alt="EmailAI logo" />
          <div>
            <div className="title">{viewTitle}</div>
            <div className="subtitle">{roleSubtitle}</div>
          </div>
        </div>
        <div>
          <button className="btn secondary" onClick={() => navigate("/")}>
            ← Back to Dashboard
          </button>
        </div>
      </div>

      {!selected ? (
        <div className="board">
          <section className="column">
            <h2>Incoming Emails</h2>
            <EmailList
              items={visibleIncoming.map(e => ({
                id: e.id,
                title: e.subject,
                subtitle: `${e.from?.name || ""} <${e.from?.email || ""}>`,
                at: e.received_at,
                assignee: e.assignee,
                tags: e.tags
              }))}
              onOpen={handleOpenIncoming}
            />
          </section>

          <section className="column">
            <h2>Open Tickets</h2>
            <EmailList
              items={openTickets.map(t => ({
                id: t.id,
                title: `[${t.id}] ${t.subject}`,
                subtitle: `${t.sender?.name || ""} <${t.sender?.email || ""}>`,
                at: t.received_at,
                assignee: t.assignee,
                tags: t.tags
              }))}
              onOpen={handleOpenTicket}
            />
          </section>

          <section className="column">
            <h2>Closed Tickets</h2>
            <EmailList
              items={closedTickets.map(t => ({
                id: t.id,
                title: `[${t.id}] ${t.subject}`,
                subtitle: `${t.sender?.name || ""} <${t.sender?.email || ""}>`,
                at: t.received_at,
                assignee: t.assignee,
                tags: t.tags
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
