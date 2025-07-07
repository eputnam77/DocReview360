import React, { useEffect, useState } from 'react';

export default function Dashboard() {
  const [widgets, setWidgets] = useState<{assigned:number;active:number;pending_approvals:number}>({assigned:0,active:0,pending_approvals:0});
  const [projects, setProjects] = useState<Array<{id:string;name:string;docs:number;pending_approvals:number}>>([]);

  useEffect(() => {
    fetch('/dashboard/widgets').then(r => r.json()).then(setWidgets);
    fetch('/reports/dashboard').then(r => r.json()).then(setProjects);
  }, []);

  return (
    <div className="p-4 space-y-4">
      <h1 className="text-xl font-bold">Dashboard</h1>
      <p>Welcome to DocuFlow. Use the quick links below to jump between the demo pages.</p>
      <ul className="list-disc pl-5 space-y-1">
        <li><a href="/reviewtrackertable" className="underline">Review Tracker</a></li>
        <li><a href="/doceditor" className="underline">Document Editor</a></li>
        <li><a href="/editor" className="underline">Classic Editor</a></li>
        <li><a href="/index" className="underline">Home</a></li>
        <li><a href="/new-project" className="underline">Create Project</a></li>
      </ul>

      <div>
        <h2 className="font-semibold">Widget Summary</h2>
        <p>Assigned: {widgets.assigned}</p>
        <p>Active: {widgets.active}</p>
        <p>Pending Approvals: {widgets.pending_approvals}</p>
      </div>

      <div>
        <h2 className="font-semibold">Project Dashboard</h2>
        <table className="border w-full">
          <thead>
            <tr>
              <th className="border px-2">Project</th>
              <th className="border px-2">Docs</th>
              <th className="border px-2">Pending</th>
            </tr>
          </thead>
          <tbody>
            {projects.map(p => (
              <tr key={p.id}>
                <td className="border px-2">{p.name}</td>
                <td className="border px-2">{p.docs}</td>
                <td className="border px-2">{p.pending_approvals}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
