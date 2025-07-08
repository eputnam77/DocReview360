import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { UploadDropzone } from '@/components/workflow';

type Props = { params: { id: string } };

export default function StartWorkflowPage({ params }: Props) {
  const [title, setTitle] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // TODO: wire up real submit logic
    console.log('start workflow', params.id, title);
  };

  return (
    <form id={`start-${params.id}`} className="space-y-4 p-4" onSubmit={handleSubmit}>
      <div className="space-y-2">
        <Label htmlFor="title">Title</Label>
        <Input id="title" value={title} onChange={e => setTitle(e.target.value)} />
      </div>
      <UploadDropzone />
      <Button type="submit">Start Workflow</Button>
    </form>
  );
}
