import React, { useState } from "react";
import { Shell, type NavPage } from "./components/Shell";
import { DashboardPage } from "./pages/DashboardPage";
import { AskArbiterPage } from "./pages/AskArbiterPage";
import { ClientsPage } from "./pages/ClientsPage";
import { AgentsPage } from "./pages/AgentsPage";
import { ToolsPage } from "./pages/ToolsPage";
import { SecurityPage } from "./pages/SecurityPage";
import { ReliabilityPage } from "./pages/ReliabilityPage";
import { ObservabilityPage } from "./pages/ObservabilityPage";
import { ArchitecturePage } from "./pages/ArchitecturePage";

export const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState<NavPage>("dashboard");
  const [selectedClientId, setSelectedClientId] = useState<string>("cli_1014");

  return (
    <Shell
      currentPage={currentPage}
      onSelectPage={setCurrentPage}
      selectedClientId={selectedClientId}
      onSelectClient={setSelectedClientId}
    >
      {currentPage === "dashboard" && <DashboardPage onNavigate={setCurrentPage} />}
      {currentPage === "ask" && (
        <AskArbiterPage
          selectedClientId={selectedClientId}
          onSelectClient={setSelectedClientId}
        />
      )}
      {currentPage === "clients" && (
        <ClientsPage
          onSelectClient={setSelectedClientId}
          onNavigate={setCurrentPage}
        />
      )}
      {currentPage === "agents" && <AgentsPage />}
      {currentPage === "tools" && <ToolsPage />}
      {currentPage === "security" && <SecurityPage />}
      {currentPage === "reliability" && <ReliabilityPage />}
      {currentPage === "observability" && <ObservabilityPage />}
      {currentPage === "architecture" && <ArchitecturePage />}
    </Shell>
  );
};

export default App;
