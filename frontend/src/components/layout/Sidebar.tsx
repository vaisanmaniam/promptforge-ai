import React from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  BrainCircuit,
  GitFork,
  ShieldCheck,
  TrendingUp,
  FlaskConical,
  Wrench,
  ExternalLink,
} from "lucide-react";

interface NavItem {
  name: string;
  path: string;
  icon: React.ReactNode;
  phase: string;
  implemented: boolean;
}

const navItems: NavItem[] = [
  {
    name: "Dashboard",
    path: "/",
    icon: <LayoutDashboard className="w-4 h-4" />,
    phase: "Phase 1",
    implemented: true,
  },
  {
    name: "Prompt Intelligence",
    path: "/prompt-intelligence",
    icon: <BrainCircuit className="w-4 h-4" />,
    phase: "Phase 2",
    implemented: true,
  },
  {
    name: "Requirements & Trace",
    path: "/requirements",
    icon: <GitFork className="w-4 h-4" />,
    phase: "Phase 3",
    implemented: true,
  },
  {
    name: "Verification & Sandbox",
    path: "/verification",
    icon: <ShieldCheck className="w-4 h-4" />,
    phase: "Phase 4",
    implemented: true,
  },
  {
    name: "Predictive Regression",
    path: "/regression",
    icon: <TrendingUp className="w-4 h-4" />,
    phase: "Phase 5",
    implemented: true,
  },
  {
    name: "Automated Code Repair",
    path: "/repair",
    icon: <Wrench className="w-4 h-4" />,
    phase: "Phase 6",
    implemented: true,
  },
  {
    name: "Model Lab",
    path: "/models",
    icon: <FlaskConical className="w-4 h-4" />,
    phase: "Diagnostics",
    implemented: true,
  },
];

export const Sidebar: React.FC = () => {
  return (
    <aside className="w-64 border-r border-[#1F2937] bg-[#0B0F17] flex flex-col justify-between p-4 min-h-[calc(100vh-4rem)]">
      <div className="space-y-6">
        <div>
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 px-3">
            Core Engineering Modules
          </span>
          <nav className="mt-2 space-y-1">
            {navItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                    isActive
                      ? "bg-cyan-500/10 text-cyan-300 border border-cyan-500/30"
                      : "text-slate-400 hover:text-slate-200 hover:bg-[#111827]"
                  }`
                }
              >
                <div className="flex items-center gap-2.5">
                  {item.icon}
                  <span>{item.name}</span>
                </div>
                {!item.implemented ? (
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#1E293B] text-slate-400 border border-[#334155]/60">
                    {item.phase}
                  </span>
                ) : (
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                )}
              </NavLink>
            ))}
          </nav>
        </div>
      </div>

      <div className="p-3 rounded-lg bg-[#111827] border border-[#1F2937] text-xs">
        <div className="flex items-center justify-between text-slate-400 mb-1">
          <span className="font-medium text-slate-300">FastAPI API Docs</span>
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noreferrer"
            className="text-cyan-400 hover:text-cyan-300 inline-flex items-center gap-1 text-[11px]"
          >
            Swagger <ExternalLink className="w-3 h-3" />
          </a>
        </div>
        <p className="text-[11px] text-slate-500">
          OpenAPI interactive specification running on localhost:8000
        </p>
      </div>
    </aside>
  );
};
