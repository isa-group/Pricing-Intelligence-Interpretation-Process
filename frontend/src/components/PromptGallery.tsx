import type { PromptPreset } from '../types';

interface Props {
  presets: PromptPreset[];
  onSelect: (preset: PromptPreset) => void;
  disabled?: boolean;
}

function PromptGallery({ presets, onSelect, disabled = false }: Props) {
  if (!presets || presets.length === 0) {
    return null;
  }

  return (
    <section className="prompt-gallery">
      <h3>Prompt presets</h3>
      <div className="prompt-list">
        {presets.map((preset) => (
          <button
            type="button"
            key={preset.id}
            className="prompt-card"
            onClick={() => onSelect(preset)}
            disabled={disabled}
            title={preset.description}
          >
            <span className="prompt-card-icon" aria-hidden="true">
              {preset.label.charAt(0).toUpperCase()}
            </span>
            <span className="prompt-card-content">
              <span className="prompt-title">{preset.label}</span>
              <span className="prompt-description">{preset.description}</span>
            </span>
            <span className="prompt-card-arrow" aria-hidden="true">
              ↗
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}

export default PromptGallery;
