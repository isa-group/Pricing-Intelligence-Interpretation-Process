import { useMemo, useState } from 'react';

import type { ContextItemInput, PricingContextItem } from '../types';

interface Props {
  items: PricingContextItem[];
  detectedUrls: string[];
  onAdd: (input: ContextItemInput) => void;
  onRemove: (id: string) => void;
  onClear: () => void;
}

const ORIGIN_LABEL: Record<PricingContextItem['origin'], string> = {
  user: 'Manual',
  detected: 'Detected',
  preset: 'Preset',
  agent: 'Agent'
};

function ContextManager({ items, detectedUrls, onAdd, onRemove, onClear }: Props) {
  const [urlInput, setUrlInput] = useState('');
  const [error, setError] = useState<string | null>(null);

  const availableDetected = useMemo(
    () => detectedUrls.filter((url) => !items.some((item) => item.kind === 'url' && item.value === url)),
    [detectedUrls, items]
  );

  const handleAddUrl = () => {
    const trimmed = urlInput.trim();
    if (!trimmed) {
      setError('Enter a URL to add it to the context.');
      return;
    }

    try {
      const normalized = new URL(trimmed).href;
      onAdd({ kind: 'url', label: normalized, value: normalized, origin: 'user' });
      setUrlInput('');
      setError(null);
    } catch {
      setError('Enter a valid http(s) URL.');
    }
  };

  return (
    <section className="context-manager">
      <header className="context-manager-header">
        <div>
          <h3>Pricing Context</h3>
          <p className="context-subtitle">Add URLs or YAML exports to ground H.A.R.V.E.Y.'s answers.</p>
        </div>
        <div className="context-controls">
          <span className="context-count">{items.length} selected</span>
          {items.length > 0 ? (
            <button type="button" className="context-clear" onClick={onClear}>
              Clear all
            </button>
          ) : null}
        </div>
      </header>

      <div className="context-list">
        {items.length === 0 ? (
          <p className="context-empty">No pricings selected. Add one to keep the conversation grounded.</p>
        ) : (
          <ul>
            {items.map((item) => (
              <li key={item.id} className="context-item">
                <div>
                  <span className="context-item-label">{item.label}</span>
                  <span className="context-item-meta">
                    {item.kind === 'url' ? 'URL' : 'YAML'} &middot; {ORIGIN_LABEL[item.origin]}
                  </span>
                </div>
                <button type="button" className="context-remove" onClick={() => onRemove(item.id)}>
                  Remove
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {availableDetected.length > 0 ? (
        <div className="context-detected">
          <span className="context-detected-title">Detected in question</span>
          <div className="context-detected-list">
            {availableDetected.map((url) => (
              <button
                type="button"
                key={url}
                className="context-detected-chip"
                onClick={() => onAdd({ kind: 'url', label: url, value: url, origin: 'detected' })}
              >
                Add {url}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      <div className="context-add-url">
        <input
          type="url"
          name="context-url"
          inputMode="url"
          value={urlInput}
          placeholder="https://example.com/pricing"
          onChange={(event) => {
            setUrlInput(event.target.value);
            setError(null);
          }}
          onKeyDown={(event) => {
            if (event.key === 'Enter') {
              event.preventDefault();
              handleAddUrl();
            }
          }}
        />
        <button type="button" onClick={handleAddUrl}>
          Add URL
        </button>
      </div>
      {error ? <p className="context-error">{error}</p> : null}
    </section>
  );
}

export default ContextManager;
