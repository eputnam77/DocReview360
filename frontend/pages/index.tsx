import React from "react";
import { useQuery } from '@tanstack/react-query';
import { useCounterStore } from '../state/useStore';

export default function Home() {
  const { data } = useQuery({
    queryKey: ['ping'],
    queryFn: () => fetch('/api/ping').then(r => r.text()),
  });
  const count = useCounterStore(s => s.count);
  const increment = useCounterStore(s => s.increment);
  return (
    <div className="text-center">
      <p>{data}</p>
      <button onClick={increment}>Increment</button>
      <p>count: {count}</p>
    </div>
  );
}
