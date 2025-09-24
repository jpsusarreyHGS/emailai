const API_BASE_URL = 'http://localhost:7071/api';

export async function fetchEmails(status = null) {
  const url = status 
    ? `${API_BASE_URL}/emails?status=${status}`
    : `${API_BASE_URL}/emails`;
  
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch emails: ${response.statusText}`);
  }
  
  const data = await response.json();
  return data.emails || [];
}

export async function fetchEmailsByAgent(assignedAgent) {
  const url = `${API_BASE_URL}/emails?assigned_agent=${assignedAgent}`;
  
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch emails for agent: ${response.statusText}`);
  }
  
  const data = await response.json();
  return data.emails || [];
}

export async function categorizeEmails() {
  const response = await fetch(`${API_BASE_URL}/emails/categorize`, {
    method: 'POST',
  });
  
  if (!response.ok) {
    throw new Error(`Failed to categorize emails: ${response.statusText}`);
  }
  
  const data = await response.json();
  return data;
}

export async function ingestEmails() {
  const response = await fetch(`${API_BASE_URL}/emails/ingest`, {
    method: 'POST',
  });
  
  if (!response.ok) {
    throw new Error(`Failed to ingest emails: ${response.statusText}`);
  }
  
  const data = await response.json();
  return data;
}

export async function runOcrForEmail(emailId) {
  const res = await fetch(`${API_BASE_URL}/emails/${emailId}/attachments/ocr`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`OCR failed: ${res.statusText}`);
  return res.json();
}

export async function generateDraftForEmail(emailId) {
  const res = await fetch(`${API_BASE_URL}/emails/${emailId}/draft`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Draft failed: ${res.statusText}`);
  return res.json();
}

export async function fetchEmailDoc(emailId) {
  const res = await fetch(`${API_BASE_URL}/emails/${emailId}/fetch`);
  if (!res.ok) throw new Error(`Fetch email failed: ${res.statusText}`);
  return res.json();
}

export async function saveEmailOcrEdits({ id, filename, merchant, date, total, model, store_number }) {
  const res = await fetch(`${API_BASE_URL}/emails/save-edits`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id, filename, merchant, date, total, model, store_number })
  });
  if (!res.ok) throw new Error(`Save edits failed: ${res.statusText}`);
  return res.json();
}

export async function saveDraft(emailId, body) {
  const res = await fetch(`${API_BASE_URL}/emails/save-edits`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id: emailId, draft_body: body })
  });
  if (!res.ok) throw new Error(`Save draft failed: ${res.statusText}`);
  return res.json();
}

export async function updateEmailTicket(emailId, ticket) {
  const res = await fetch(`${API_BASE_URL}/emails/${emailId}/ticket`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ticket })
  });
  if (!res.ok) throw new Error(`Update ticket failed: ${res.statusText}`);
  return res.json();
}
