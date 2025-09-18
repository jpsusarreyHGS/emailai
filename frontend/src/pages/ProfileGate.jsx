import React from "react";
import "./Dashboard.css";
import HgsLogo from "../assets/HgsLogo.svg";

const PEOPLE = [
  { id: "coach",  name: "Coach View", role: "coach",  expertise: ["All"] },
  { id: "alice",  name: "Alice",      role: "analyst", expertise: ["TV", "Display", "Screen"] },
  { id: "bob",    name: "Bob",        role: "analyst", expertise: ["Fridge", "Appliance", "Kitchen"] },
  { id: "cara",   name: "Cara",       role: "analyst", expertise: ["Soundbar", "Audio", "Speaker"] },
];

export default function ProfileGate({ onSelect }) {
  return (
    <div className="gate">
      <div className="header">
        <div className="brand">
          <img className="logo" src={HgsLogo} alt="EmailAI logo" />
          <div>
            <div className="title">EmailAI</div>
            <div className="subtitle">Select a profile to continue</div>
          </div>
        </div>
      </div>

      <div className="profiles">
        {PEOPLE.map(p => (
          <button key={p.id} className="profile-tile" onClick={() => onSelect(p)}>
            <div className="avatar">{p.name[0]}</div>
            <div className="profile-name">{p.name}</div>
            <div className="profile-role">{p.role === "coach" ? "Coach" : "Analyst"}</div>
            <div className="profile-tags">
              {p.expertise.map((x, i) => (
                <span key={i} className="pill tag">{x}</span>
              ))}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
