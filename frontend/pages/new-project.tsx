import React, { useState } from 'react';
import { useRouter } from 'next/router';

export default function NewProject() {
  const [id, setId] = useState('');
  const [name, setName] = useState('');
  const router = useRouter();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    await fetch('/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id, name, user: 'admin' }),
    });
    router.push('/projects');
  }

  return (
    <form onSubmit={submit} className="p-4 flex flex-col gap-2">
      <input value={id} onChange={e => setId(e.target.value)} placeholder="id" className="border" />
      <input value={name} onChange={e => setName(e.target.value)} placeholder="name" className="border" />
      <button type="submit">Create Project</button>
    </form>
  );
}
