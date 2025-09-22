import React, { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import HgsLogo from "../assets/HgsLogo.svg";
import EmailDetail from "../components/EmailDetail";
import EmailList from "../components/EmailList";
import { fetchEmailsByAgent } from "../utils/api";
import "./Dashboard.css";

const ROSTER = {
  agent_001: { id: "agent_001", name: "Coach Gerver" },
  agent_002: { id: "agent_002", name: "Alice Thompson" },
  agent_003: { id: "agent_003", name: "Bob Hernandez" },
  agent_004: { id: "agent_004", name: "Cara Park" },
};

export default function Dashboard() {
  const navigate = useNavigate();
  const { state } = useLocation();

  const selectedProfile = state?.profile || ROSTER.agent_001;

  const [emails, setEmails] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(null);

  // Function to refresh emails
  const refreshEmails = async () => {
    try {
      setLoading(true);
      setError(null);
      
      console.log('Refreshing emails for agent:', selectedProfile.id);
      
      // Fetch emails assigned to this agent
      const agentEmails = await fetchEmailsByAgent(selectedProfile.id);
      
      console.log('Received emails:', agentEmails.length);
      
      // Transform backend email format to Dashboard format
      const transformedEmails = agentEmails.map((email, idx) => {
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
          id: email.id || `EML-${idx + 1}`,
          subject: email.subject || 'No Subject',
          from: {
            name: fromName,
            email: fromEmail
          },
          body: email.body?.content || email.body || '',
          attachments: email.attachments || [],
          received_at: email.receivedDateTime || new Date().toISOString(),
          messageId: email.id || `msg-${idx + 1}`,
          assignee: { id: selectedProfile.id, name: selectedProfile.name },
          tags: email.tags || [],
          ticket: email.ticket || 'new', // Default to 'new' if no ticket status
          labels: email.labels || null, // Include labels for category display
          hasAttachments: !!(email.attachments && email.attachments.length > 0)
        };
      });
      
      console.log('Transformed emails:', transformedEmails);
      setEmails(transformedEmails);
    } catch (err) {
      console.error('Failed to refresh emails:', err);
      setError(err.message);
      setEmails([]); // Set empty array on error
    } finally {
      setLoading(false);
    }
  };

  // Fetch emails for the selected agent on component mount
  useEffect(() => {
    async function loadEmails() {
      try {
        setLoading(true);
        setError(null);
        
        console.log('Fetching emails for agent:', selectedProfile.id);
        
        // Fetch emails assigned to this agent
        const agentEmails = await fetchEmailsByAgent(selectedProfile.id);
        
        console.log('Received emails:', agentEmails.length);
        
        // Transform backend email format to Dashboard format
        const transformedEmails = agentEmails.map((email, idx) => {
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
            id: email.id || `EML-${idx + 1}`,
            subject: email.subject || 'No Subject',
            from: {
              name: fromName,
              email: fromEmail
            },
            body: email.body?.content || email.body || '',
            attachments: email.attachments || [],
            received_at: email.receivedDateTime || new Date().toISOString(),
            messageId: email.id || `msg-${idx + 1}`,
            assignee: { id: selectedProfile.id, name: selectedProfile.name },
            tags: email.tags || [],
            ticket: email.ticket || 'new', // Default to 'new' if no ticket status
            labels: email.labels || null, // Include labels for category display
            hasAttachments: !!(email.attachments && email.attachments.length > 0)
          };
        });
        
        console.log('Transformed emails:', transformedEmails);
        setEmails(transformedEmails);
      } catch (err) {
        console.error('Failed to load emails:', err);
        setError(err.message);
        setEmails([]); // Set empty array on error
      } finally {
        setLoading(false);
      }
    }
    
    loadEmails();
  }, [selectedProfile.id, selectedProfile.name]);

  // Split emails into three columns based on ticket field
  const newEmails = useMemo(() => {
    return emails.filter(email => email.ticket === 'new');
  }, [emails]);

  const openEmails = useMemo(() => {
    return emails.filter(email => email.ticket === 'open');
  }, [emails]);

  const closedEmails = useMemo(() => {
    return emails.filter(email => email.ticket === 'closed');
  }, [emails]);

  const handleOpenEmail = (emailId) => {
    const email = emails.find(e => e.id === emailId);
    if (email) {
      // Convert email to ticket format for EmailDetail component
      const ticket = {
        id: email.id,
        email_id: email.id,
        subject: email.subject,
        sender: email.from,
        received_at: email.received_at,
        status: "awaiting_review",
        email_body: email.body,
        attachments: (email.attachments || []).map((attachment, i) => ({
          sasUrl: attachment.blobPath || `mock/blob/${i}`,
          blob: attachment.blobPath || `mock/blob/${i}`,
          name: attachment.name || `attachment_${i}`
        })),
        extracted: {
          merchant: "Unknown",
          date: new Date().toISOString().slice(0, 10),
          total: 0,
          model: "—",
          storeNumber: "—",
        },
        scores: { confidence: 85, dup_score: 15, fraud_score: 5 },
        validation: { status: "pass", rules_passed: ["basic_validation"], rules_failed: [] },
        draft_reply: {
          template: "response",
          body: `Hi ${email.from?.name || "Customer"},\n\nThank you for your email. We will review your request and get back to you shortly.\n\nBest regards,\nSupport Team`,
        },
        thread: [
          { id: email.messageId, direction: "in", subject: email.subject, body: email.body, at: email.received_at }
        ],
        assignee: email.assignee,
        tags: email.tags || []
      };
      setSelected(ticket);
    }
  };

  const handleSave = (ticketId, draftBody) => {
    // For now, just update the selected ticket
    if (selected && selected.id === ticketId) {
      setSelected(prev => ({
        ...prev,
        draft_reply: { ...prev.draft_reply, body: draftBody }
      }));
    }
  };

  const handleSend = (ticketId, draftBody) => {
    // For now, just close the detail view
    // In a real implementation, this would call an API to send the email
    setSelected(null);
  };

  const handleSimulateReply = (ticketId) => {
    // For now, just close the detail view
    // In a real implementation, this would simulate a customer reply
    setSelected(null);
  };

  const handleBackHome = () => setSelected(null);

  const viewTitle = `${selectedProfile.name} Dashboard`;
  const roleSubtitle = `Agent ID: ${selectedProfile.id}`;

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
        <div style={{ display: 'flex', gap: '8px' }}>
          <button 
            className="btn secondary"
            onClick={refreshEmails}
            disabled={loading}
            style={{ 
              background: '#1976d2',
              color: 'white',
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.6 : 1
            }}
          >
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
          <button className="btn secondary" onClick={() => navigate("/")}>
            ← Back to Home
          </button>
        </div>
      </div>

      {loading ? (
        <div className="loading">Loading emails...</div>
      ) : error ? (
        <div className="error">
          <p>Error loading emails: {error}</p>
          <button onClick={() => window.location.reload()}>Retry</button>
        </div>
      ) : !selected ? (
        <div className="board">
          <section className="column">
            <h2>New Emails ({newEmails.length})</h2>
            <EmailList
              items={newEmails.map(e => ({
                id: e.id,
                title: e.subject,
                subtitle: `${e.from?.name || ""} <${e.from?.email || ""}>`,
                at: e.received_at,
                tags: e.tags,
                labels: e.labels,
                hasAttachments: e.hasAttachments
              }))}
              onOpen={handleOpenEmail}
            />
          </section>

          <section className="column">
            <h2>Open Emails ({openEmails.length})</h2>
            <EmailList
              items={openEmails.map(e => ({
                id: e.id,
                title: e.subject,
                subtitle: `${e.from?.name || ""} <${e.from?.email || ""}>`,
                at: e.received_at,
                tags: e.tags,
                labels: e.labels,
                hasAttachments: e.hasAttachments
              }))}
              onOpen={handleOpenEmail}
            />
          </section>

          <section className="column">
            <h2>Closed Emails ({closedEmails.length})</h2>
            <EmailList
              items={closedEmails.map(e => ({
                id: e.id,
                title: e.subject,
                subtitle: `${e.from?.name || ""} <${e.from?.email || ""}>`,
                at: e.received_at,
                tags: e.tags,
                labels: e.labels,
                hasAttachments: e.hasAttachments
              }))}
              onOpen={handleOpenEmail}
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