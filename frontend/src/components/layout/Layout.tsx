import React, { useEffect, useState, useCallback } from "react";
import { Outlet } from "react-router-dom";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";
import { fetchHealth, fetchSystemStatus } from "../../api/system";
import { HealthResponse, SystemStatusResponse } from "../../types/system";

export const Layout: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [systemStatus, setSystemStatus] = useState<SystemStatusResponse | null>(null);
  const [isBackendConnected, setIsBackendConnected] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const loadStatus = useCallback(async () => {
    setIsLoading(true);
    try {
      const [healthData, statusData] = await Promise.all([
        fetchHealth().catch(() => null),
        fetchSystemStatus().catch(() => null),
      ]);

      if (healthData) {
        setHealth(healthData);
        setIsBackendConnected(true);
      } else {
        setIsBackendConnected(false);
      }

      if (statusData) {
        setSystemStatus(statusData);
      }
    } catch {
      setIsBackendConnected(false);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStatus();
    // Heartbeat poll every 15 seconds
    const interval = setInterval(loadStatus, 15000);
    return () => clearInterval(interval);
  }, [loadStatus]);

  return (
    <div className="min-h-screen bg-[#0B0F17] flex flex-col font-sans">
      <Header
        health={health}
        isBackendConnected={isBackendConnected}
        isLoading={isLoading}
        onRefresh={loadStatus}
      />
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 p-6 md:p-8 max-w-7xl mx-auto w-full overflow-y-auto">
          {/* Provide system status context to outlet */}
          <Outlet context={{ health, systemStatus, isBackendConnected, isLoading, reload: loadStatus }} />
        </main>
      </div>
    </div>
  );
};
