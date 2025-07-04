import React, { useState } from 'react';

export default function Editor() {
  const [value, setValue] = useState('');
  return (
    <div className="p-4">
      <textarea value={value} onChange={e => setValue(e.target.value)} className="border w-full" />
    </div>
  );
}
