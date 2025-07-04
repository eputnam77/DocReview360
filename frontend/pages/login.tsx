import React from 'react';

export default function Login() {
  return (
    <form method="post" action="/login" className="flex flex-col items-center gap-2">
      <input name="username" placeholder="username" className="border" />
      <input name="password" type="password" placeholder="password" className="border" />
      <button type="submit">Login</button>
    </form>
  );
}
