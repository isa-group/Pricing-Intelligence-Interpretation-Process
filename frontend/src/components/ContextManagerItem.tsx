import { PricingContextItem } from "../types";
import OpenInNewIcon from "./OpenInNewIcon";
import TrashIcon from "./TrashIcon";

const SPHERE_EDITOR = import.meta.env.VITE_SPHERE_BASE_URL + "/editor";

interface ContextManagerItemProps {
  item: PricingContextItem;
  onRemove: (id: string) => void;
}

const ORIGIN_LABEL: Record<PricingContextItem["origin"], string> = {
  user: "Manual",
  detected: "Detected",
  preset: "Preset",
  agent: "Agent",
  sphere: "SPHERE"
};

function ContextManagerItem({ item, onRemove }: ContextManagerItemProps) {
  const formatSphereEditorLink = (url: string) =>
    `${SPHERE_EDITOR}?pricingUrl=${url}`;

  return (
    <li className="context-item">
      <div>
        <span className="context-item-label">{item.label}</span>
        <span className="context-item-meta">
          {item.kind === "url" ? "URL" : "YAML"} &middot;{" "}
          {ORIGIN_LABEL[item.origin]}
        </span>
      </div>
      <button
        type="button"
        className="context-remove"
        onClick={() => onRemove(item.id)}
      >
        <TrashIcon width={24} height={24} />
      </button>
      {item.kind === "yaml" && (
        <a
          className="context-item-editor-link"
          target="_blank"
          href={formatSphereEditorLink(item.value)}
        >
          <OpenInNewIcon width={24} height={24} />
        </a>
      )}
    </li>
  );
}

export default ContextManagerItem;
