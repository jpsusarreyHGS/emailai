import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import HgsLogo from "../assets/HgsLogo.svg";
import PaperclipIcon from "../assets/paperclip-icon.png";
import { fetchEmails } from "../utils/api";
import "./Dashboard.css";

const ANALYSTS = [
  { id: "coach", name: "Coach", role: "coach", tags: ["All"] },
  { id: "alice", name: "Alice", role: "analyst", tags: ["TV", "Display", "Screen"] },
  { id: "bob",   name: "Bob",   role: "analyst", tags: ["appliance", "warranty"] },
  { id: "cara",  name: "Cara",  role: "analyst", tags: ["car", "insurance"] },
];

const SEED_EMAILS = [
  {
    id: "E-1001",
    subject: "Warranty Request: Broken TV Screen (ZX100)",
    from: { name: "Jane Doe", email: "jane@example.com" },
    body: "My ZX100 TV screen cracked during installation. Store: BB-0421",
    at: new Date().toISOString(),
    tags: [],
    assignedTo: null,
    hasAttachments: false
  },
  {
    id: "E-1002",
    subject: "Fridge appliance issue under warranty",
    from: { name: "Rina Park", email: "rina@example.com" },
    body: "Our kitchen fridge compressor failed. Need warranty service.",
    at: new Date().toISOString(),
    tags: [],
    assignedTo: null,
    hasAttachments: false
  },
  {
    id: "E-1003",
    subject: "Car insurance claim – help needed",
    from: { name: "Evan Lin", email: "evan@example.com" },
    body: "Please review my car insurance claim. Paperwork attached.",
    at: new Date().toISOString(),
    tags: [],
    assignedTo: null,
    hasAttachments: true
  },
  {
    id: "E-1004",
    subject: "QX55 soundbar receipt for warranty",
    from: { name: "Mark Lee", email: "mark@example.com" },
    body: "Re-sending clearer receipt for QX55 soundbar purchase.",
    at: new Date().toISOString(),
    tags: [],
    assignedTo: null,
    hasAttachments: true
  },
];

function tagAndAssign(email) {
  const text = `${email.subject} ${email.body}`.toLowerCase();
  const tags = [];
  if (/\b(tv|display|screen|zx100)\b/.test(text)) tags.push("TV/Screen");
  if (/\b(appliance|fridge|kitchen)\b/.test(text)) tags.push("Appliance");
  if (/\bwarranty\b/.test(text)) tags.push("Warranty");
  if (/\b(car|insurance)\b/.test(text)) tags.push("Car/Insurance");

  const scores = [
    { id: "alice", hits: +( /tv|display|screen|zx100/.test(text) ) },
    { id: "bob",   hits: +( /appliance|fridge|kitchen|warranty/.test(text) ) },
    { id: "cara",  hits: +( /car|insurance/.test(text) ) }
  ].sort((a,b)=>b.hits-a.hits);

  const best = scores[0];
  const assignedTo = best && best.hits > 0 ? best.id : null;

  return { ...email, tags, assignedTo };
}

export default function SortBoard() {
  const navigate = useNavigate();
  const [emails, setEmails] = useState([]);
  const [sortedMode, setSortedMode] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch emails from backend on component mount
  useEffect(() => {
    async function loadIncomingEmails() {
      try {
        setLoading(true);
        setError(null);
        
        // Fetch emails with "new" status for incoming emails
        const apiEmails = await fetchEmails('new');
        
        // Transform backend email format to SortBoard format
        const transformedEmails = apiEmails.map((email, idx) => {
          // Handle the emailAddress parsing - it might come as a string representation
          let fromName = 'Unknown';
          let fromEmail = 'unknown@example.com';
          
          if (email.from?.emailAddress) {
            if (typeof email.from.emailAddress === 'string') {
              // Parse string representation like "@{name=Nina Davis; address=nina.davis@example.com}"
              const nameMatch = email.from.emailAddress.match(/name=([^;]+)/);
              const emailMatch = email.from.emailAddress.match(/address=([^}]+)/);
              fromName = nameMatch ? nameMatch[1] : 'Unknown';
              fromEmail = emailMatch ? emailMatch[1] : 'unknown@example.com';
            } else {
              // Handle as object
              fromName = email.from.emailAddress.name || 'Unknown';
              fromEmail = email.from.emailAddress.address || 'unknown@example.com';
            }
          }
          
          return {
            id: email.id || `E-${idx + 1}`,
            subject: email.subject || 'No Subject',
            from: {
              name: fromName,
              email: fromEmail
            },
            body: email.body?.content || email.body || '',
            at: email.receivedDateTime || new Date().toISOString(),
            tags: email.tags || [],
            assignedTo: null, // Initially unassigned
            hasAttachments: email.hasAttachments || false
          };
        });
        
        setEmails(transformedEmails);
      } catch (err) {
        console.error('Failed to load emails:', err);
        setError(err.message);
        // Fallback to seed emails
        setEmails(SEED_EMAILS);
      } finally {
        setLoading(false);
      }
    }
    
    loadIncomingEmails();
  }, []);

  const inboxEmails = useMemo(() => emails.filter(e => !e.assignedTo), [emails]);
  const byAssignee = useMemo(() => ({
    alice: emails.filter(e => e.assignedTo === "alice"),
    bob:   emails.filter(e => e.assignedTo === "bob"),
    cara:  emails.filter(e => e.assignedTo === "cara"),
    coach: emails.filter(e => !!e.assignedTo)
  }), [emails]);

  const handleFilterSort = () => {
    setEmails(prev => prev.map(tagAndAssign));
    setSortedMode(true);
  };

  const handleReset = () => {
    setEmails(prev => prev.map(e => ({ ...e, assignedTo: null, tags: [] })));
    setSortedMode(false);
  };

  const handleRefreshEmails = async () => {
    try {
      setLoading(true);
      setError(null);
      const apiEmails = await fetchEmails('new');
      const transformedEmails = apiEmails.map((email, idx) => {
        let fromName = 'Unknown';
        let fromEmail = 'unknown@example.com';
        
        if (email.from?.emailAddress) {
          if (typeof email.from.emailAddress === 'string') {
            const nameMatch = email.from.emailAddress.match(/name=([^;]+)/);
            const emailMatch = email.from.emailAddress.match(/address=([^}]+)/);
            fromName = nameMatch ? nameMatch[1] : 'Unknown';
            fromEmail = emailMatch ? emailMatch[1] : 'unknown@example.com';
          } else {
            fromName = email.from.emailAddress.name || 'Unknown';
            fromEmail = email.from.emailAddress.address || 'unknown@example.com';
          }
        }
        
        return {
          id: email.id || `E-${idx + 1}`,
          subject: email.subject || 'No Subject',
          from: { name: fromName, email: fromEmail },
          body: email.body?.content || email.body || '',
          at: email.receivedDateTime || new Date().toISOString(),
          tags: email.tags || [],
          assignedTo: null,
          hasAttachments: email.hasAttachments || false
        };
      });
      setEmails(transformedEmails);
    } catch (err) {
      console.error('Failed to refresh emails:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const openBoard = (profileId) => {
    const p = ANALYSTS.find(a => a.id === profileId) || ANALYSTS[0];
    navigate("/board", { state: { profile: { id: p.id, name: p.name, role: p.role }, emails } });
  };

  return (
    <div className="dashboard">
      <div className="header">
        <div className="brand">
          <img className="logo" src={HgsLogo} alt="EmailAI logo" />
          <div>
            <div className="title">EmailAI</div>
            <div className="subtitle">Inbox → Filter/Sort → Pick a profile to open the board</div>
          </div>
        </div>
        <div>
          {!sortedMode ? (
            <button className="btn" onClick={handleFilterSort}>Filter / Sort</button>
          ) : (
            <button className="btn gray" onClick={handleReset}>Reset</button>
          )}
        </div>
      </div>

      <div className="preboard">
        <section className="inbox">
          <h2>
            Incoming Email
            <button 
              onClick={handleRefreshEmails} 
              disabled={loading}
              style={{ 
                marginLeft: '10px', 
                fontSize: '12px', 
                padding: '4px 8px',
                background: '#1976d2',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: loading ? 'not-allowed' : 'pointer',
                opacity: loading ? 0.6 : 1
              }}
            >
              {loading ? 'Loading...' : 'Refresh'}
            </button>
          </h2>
          <div className="hint">All new emails appear here first.</div>
          {loading ? (
            <div className="loading">Loading emails...</div>
          ) : error ? (
            <div className="error">
              <p>Error loading emails: {error}</p>
              <button onClick={() => window.location.reload()}>Retry</button>
            </div>
          ) : (
            <ul className="list">
              {inboxEmails.map(e => (
                <li key={e.id} className="item slide-in">
                  <EmailRow email={e} />
                </li>
              ))}
              {inboxEmails.length === 0 && (
                <div className="empty">No unassigned emails.</div>
              )}
            </ul>
          )}
          <div style={{ marginTop: 16 }}>
            {!sortedMode ? (
              <button className="btn" onClick={handleFilterSort} style={{ width: "100%" }}>
                Filter / Sort
              </button>
            ) : (
              <button className="btn secondary" onClick={handleReset} style={{ width: "100%" }}>
                Reset to Inbox
              </button>
            )}
          </div>
        </section>

        <section className="profiles-grid">
          {ANALYSTS.map(p => (
            <div key={p.id} className="profile-card">
              <div className="profile-head">
                <div className="avatar">{p.name[0]}</div>
                <div>
                  <div className="profile-name">{p.name}</div>
                  <div className="profile-role">{p.role === "coach" ? "Coach" : "Analyst"}</div>
                </div>
              </div>

              <div className="tag-row" style={{ margin: "8px 0 12px" }}>
                {p.tags.map((t,i)=><span key={i} className="pill tag">{t}</span>)}
              </div>

              <ul className="list compact">
                {(p.id === "coach" ? byAssignee.coach :
                  p.id === "alice" ? byAssignee.alice :
                  p.id === "bob"   ? byAssignee.bob   :
                                     byAssignee.cara
                ).map(e => (
                  <li key={e.id} className={`item fade-in`}>
                    <EmailRow email={e} compact />
                  </li>
                ))}
                {((p.id === "coach" && byAssignee.coach.length===0) ||
                  (p.id === "alice" && byAssignee.alice.length===0) ||
                  (p.id === "bob"   && byAssignee.bob.length===0) ||
                  (p.id === "cara"  && byAssignee.cara.length===0)) && (
                    <div className="empty">No assignments yet.</div>
                )}
              </ul>

              <button className="btn secondary" onClick={() => openBoard(p.id)} style={{ width:"100%", marginTop: 12 }}>
                Open Board as {p.name}
              </button>
            </div>
          ))}
        </section>
      </div>
    </div>
  );
}

function EmailRow({ email, compact=false }) {
  return (
    <div style={{ 
      display: 'flex', 
      alignItems: 'center', 
      justifyContent: 'space-between',
      width: '100%'
    }}>
      <div style={{ flex: 1 }}>
        <div className="title">{email.subject}</div>
        {!compact && (
          <div className="sub">
            {email.from?.name || ""} &lt;{email.from?.email}&gt;
          </div>
        )}
        <div className="meta-row">
          <span className="pill time">{new Date(email.at).toLocaleString()}</span>
          {!!(email.tags && email.tags.length) && (
            <span className="pill tagline">
              {email.tags.map((t,i)=><span key={i} className="pill tag">{t}</span>)}
            </span>
          )}
        </div>
      </div>
      {email.hasAttachments && (
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
  );
}
