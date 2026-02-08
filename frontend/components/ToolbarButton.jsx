import React from 'react';
export function toolbarButton(icon, command, active, title = '', disabled = false) {
    return (<button type="button" role="button" aria-label={title} className={`p-2 rounded ${active ? 'bg-indigo-100' : ''} ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`} onClick={command} title={title} disabled={disabled}>
      {icon}
    </button>);
}
