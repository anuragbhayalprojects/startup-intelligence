import React, { useState } from 'react';
import Sidebar from '@/components/Sidebar';
import Dashboard from './pages/Dashboard';
import Chat from './pages/Chat';

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState('dashboard');

  return (
    <div className="flex h-screen bg-slate-100 overflow-hidden text-slate-800 font-sans">
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="bg-white border-b border-slate-200/80 px-8 py-4 flex items-center justify-between flex-shrink-0">
          <div className="space-y-1">
            <h2 className="font-extrabold text-sm uppercase tracking-wider text-slate-900">
              Startup Intelligence & Pilots Registry
            </h2>
            <p className="text-slate-450 text-[11px] font-medium">
              Enterprise Suite
            </p>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-8">
          {activeTab === 'dashboard' && <Dashboard />}
          {activeTab === 'chat' && <Chat />}
        </main>
      </div>
    </div>
  );
};

export default App;
