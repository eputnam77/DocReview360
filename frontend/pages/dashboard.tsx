import React, { useEffect, useState } from 'react';

export default function Dashboard() {
  const [widgets, setWidgets] = useState<{assigned:number;active:number;pending_approvals:number}>({assigned:0,active:0,pending_approvals:0});
  useEffect(() => {
    fetch('/dashboard/widgets').then(r => r.json()).then(setWidgets);
  }, []);
  return (
    <div className="p-4">
      <h1>Dashboard</h1>
      <p>Assigned: {widgets.assigned}</p>
      <p>Active: {widgets.active}</p>
      <p>Pending Approvals: {widgets.pending_approvals}</p>
    </div>
  );
}
