import React from 'react';
import { dummyData } from '../data';

const Dashboard: React.FC = () => {
  return (
    <div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {dummyData.startups.map((startup, index) => (
          <div key={index} className="bg-white rounded-lg shadow-lg p-6">
            <h3 className="text-lg font-bold mb-2">{startup.name}</h3>
            <p className="text-slate-600 mb-4">{startup.description}</p>
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-slate-500">Key Metric</span>
              <span className="text-sm font-bold text-blue-500">{startup.metric}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Dashboard;
