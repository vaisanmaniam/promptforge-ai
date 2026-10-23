import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Layout } from "./components/layout/Layout";
import { DashboardPage } from "./pages/DashboardPage";
import { PromptIntelligencePage } from "./pages/PromptIntelligencePage";
import { RequirementsPage } from "./pages/RequirementsPage";
import { VerificationPage } from "./pages/VerificationPage";
import { RegressionPage } from "./pages/RegressionPage";
import { RepairPage } from "./pages/RepairPage";
import { ModelLabPage } from "./pages/ModelLabPage";

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<DashboardPage />} />
          <Route path="prompt-intelligence" element={<PromptIntelligencePage />} />
          <Route path="requirements" element={<RequirementsPage />} />
          <Route path="verification" element={<VerificationPage />} />
          <Route path="regression" element={<RegressionPage />} />
          <Route path="repair" element={<RepairPage />} />
          <Route path="models" element={<ModelLabPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

export default App;
