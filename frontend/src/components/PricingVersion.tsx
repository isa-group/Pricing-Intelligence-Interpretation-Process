import { usePricingVersions } from "../hooks/useVersion";
import { fetchPricingYaml } from "../sphere";
import { ContextItemInput } from "../types";
import PricingVersionLoader from "./PricingVersionLoader";

interface PricingVersionProps {
  owner: string;
  name: string;
  collectionName?: string | null;
  onContextAdd: (input: ContextItemInput) => void;
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
    owner: string,
    name: string,
    collectionName: string | null
  ) =>
    `(SPHERE) ${collectionName ? collectionName + "/" : ""}${name} uploaded by ${owner}`;

  const calculateTotalVersionLabel = () => {
    const res = "version";
    if (totalVersions === 1) {
      return res;
    }
    return res + "s";
  };

  const handleAddSpherePricing = async (url: string) => {
    const yamlFile = await fetchPricingYaml(url);
    onContextAdd({
      kind: "yaml",
      label: calculateLabel(owner, name, collectionName ?? null),
      value: yamlFile,
      origin: "sphere",
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
              onClick={() => handleAddSpherePricing(item.yaml)}
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
