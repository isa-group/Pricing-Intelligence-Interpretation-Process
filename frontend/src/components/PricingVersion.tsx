import { usePricingVersions } from "../hooks/useVersion";
import { fetchPricingYaml } from "../sphere";
import { SphereContextItemInput } from "../types";
import PricingVersionLoader from "./PricingVersionLoader";

interface PricingVersionProps {
  owner: string;
  name: string;
  collectionName?: string | null;
  onContextAdd: (input: SphereContextItemInput) => void;
}

function PricingVersions({
  owner,
  name,
  collectionName,
  onContextAdd,
}: PricingVersionProps) {
  const { loading, error, versions } = usePricingVersions(
    owner,
    name,
    collectionName
  );

  const totalVersions = versions?.versions.length;

  if (error) {
    return <div>Something went wrong...</div>;
  }

  if (loading) {
    return <PricingVersionLoader />;
  }

  const calculateLabel = (
    name: string,
    collectionName?: string | null
  ) =>
    `${collectionName ? collectionName + "/" : ""}${name}`;

  const calculateTotalVersionLabel = () => {
    const res = "version";
    if (totalVersions === 1) {
      return res;
    }
    return res + "s";
  };

  const handleAddSpherePricing = async (url: string, version: string) => {
    const yamlFile = await fetchPricingYaml(url);
    onContextAdd({
      kind: "yaml",
      label: calculateLabel(name, collectionName),
      value: yamlFile,
      origin: "sphere",
      owner: owner,
      yamlPath: url,
      pricingName: name,
      version: version,
      collection: collectionName ?? null,
    });
  };

  return (
    <>
      {totalVersions && (
        <span>
          {totalVersions} {calculateTotalVersionLabel()} available:
        </span>
      )}
      <ul className="pricing-versions">
        {versions?.versions.map((item) => (
          <li className="pricing-version" key={item.id}>
            <a className="version-label" href={item.yaml}>
              {item.version}
            </a>
            <button
              className="pricing-add-btn icon"
              onClick={() => handleAddSpherePricing(item.yaml, item.version)}
            >
              Add
            </button>
          </li>
        ))}
      </ul>
    </>
  );
}

export default PricingVersions;
