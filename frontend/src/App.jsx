import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import SortBoard from "./pages/SortBoard";
import Dashboard from "./pages/Dashboard";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Pre-dashboard (inbox + filter/sort + profile tiles) */}
        <Route path="/" element={<SortBoard />} />
        {/* Your previous 3-column board UI */}
        <Route path="/board" element={<Dashboard />} />
      </Routes>
    </BrowserRouter>
  );
}
