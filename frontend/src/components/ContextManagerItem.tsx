import { PricingContextItem } from "../types";
import OpenInNewIcon from "./OpenInNewIcon";
import TrashIcon from "./TrashIcon";

const SPHERE_EDITOR = import.meta.env.VITE_SPHERE_BASE_URL + "/editor";
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8086";

interface ContextManagerItemProps {
  item: PricingContextItem;
  onRemove: (id: string) => void;
}

function computeOriginLabel(pricingContextItem: PricingContextItem): string {
  switch (pricingContextItem.origin) {
    case "user":
      return "Manual";
    case "detected":
      return "Detected";
    case "preset":
      return "Preset";
    case "agent":
      return "Agent";
    case "sphere":
      return "SPHERE";
    default:
      return "";
  }
}

function computeContextItemMetadata(
  pricingContextItem: PricingContextItem
): string {
  let res = `${pricingContextItem.kind.toUpperCase()} · ${computeOriginLabel(pricingContextItem)} `;
  switch (pricingContextItem.origin) {
    case "agent":
    case "detected":
    case "preset":
    case "user": {
      return res;
    }
    case "sphere": {
      res += `· ${pricingContextItem.owner} · ${pricingContextItem.version}`;
      return res;
    }
    default:
      return "";
  }
}

function ContextManagerItem({ item, onRemove }: ContextManagerItemProps) {
  const formatSphereEditorLink = (url: string) =>
    `${SPHERE_EDITOR}?pricingUrl=${url}`;

  const formatEditorLink = (): string => {
    switch(item.origin) {
      case "preset":
      case "user":
      case "detected":
      case "agent":
        return formatSphereEditorLink(`${API_BASE_URL}/static/${item.id}`)
      case "sphere":
        return formatSphereEditorLink(item.yamlPath)
      default:
        return "#"
    }
  }

  const isSphereEditorEnabled = (item.kind === "yaml") || (item.kind === "url" && item.transform === "done")

  return (
    <li className="context-item">
      <div>
        <span className="context-item-label">{item.label}</span>
        <span className="context-item-meta">
          {computeContextItemMetadata(item)}
        </span>
        {item.kind === "url" && item.transform === "not-started" && <p>URL waiting to be processed...</p>}
        {item.kind === "url" && item.transform === "pending" && <p>URL is being transform into an iPricing...</p>}
      </div>
      <button
        type="button"
        className="context-remove"
        onClick={() => onRemove(item.id)}
      >
        <TrashIcon width={24} height={24} />
      </button>
      {isSphereEditorEnabled && (
        <a
          className="context-item-editor-link"
          target="_blank"
          href={formatEditorLink()}
        >
          <OpenInNewIcon width={24} height={24} />
        </a>
      )}
    </li>
  );
}

export default ContextManagerItem;
