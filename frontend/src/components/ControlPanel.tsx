import { ChangeEvent, FormEvent, useRef, useState } from "react";
import ContextManager from "./ContextManager";
import type { ContextInputType, PricingContextItem } from "../types";
import SearchPricings from "./SearchPricings";
import Modal from "./Modal";

interface Props {
  question: string;
  detectedPricingUrls: string[];
  contextItems: PricingContextItem[];
  isSubmitting: boolean;
  isSubmitDisabled: boolean;
  onQuestionChange: (value: string) => void;
  onSubmit: (event: FormEvent) => void;
  onFileSelect: (files: FileList | null) => void;
  onContextAdd: (input: ContextInputType) => void;
  onContextRemove: (id: string) => void;
  onSphereContextRemove: (sphereId: string) => void;
  onContextClear: () => void;
}

function ControlPanel({
  question,
  detectedPricingUrls,
  contextItems,
  isSubmitting,
  isSubmitDisabled,
  onQuestionChange,
  onSubmit,
  onFileSelect,
  onContextAdd,
  onContextRemove,
  onSphereContextRemove,
  onContextClear,
}: Props) {
  const [showPricingModal, setPricingModal] = useState<boolean>(false);

  const handleQuestionChange = (event: ChangeEvent<HTMLTextAreaElement>) => {
    onQuestionChange(event.target.value);
  };

  const handleOpenModal = () => setPricingModal(true);
  const handleCloseModal = () => setPricingModal(false);

  const fileRef = useRef<HTMLInputElement>(null);

  const handleChooseFile = () => {
    if (fileRef.current !== null) {
      fileRef.current.click();
    }
  };

  return (
    <>
      <form className="control-form" onSubmit={onSubmit}>
        <label>
          Question
          <textarea
            name="question"
            required
            rows={4}
            value={question}
            onChange={handleQuestionChange}
            placeholder="Which is the best available subscription for a team of five users?"
          />
        </label>

        <ContextManager
          items={contextItems}
          detectedUrls={detectedPricingUrls}
          onAdd={onContextAdd}
          onRemove={onContextRemove}
          onClear={onContextClear}
        />
        <h3>Add Pricing Context</h3>

        <div className="pricing-actions">
          <section className="ipricing-upload">
            <input
              ref={fileRef}
              style={{display: "none"}}
              type="file"
              accept=".yaml,.yml"
              multiple
              onChange={(event: ChangeEvent<HTMLInputElement>) => {
                const files = event.target.files ?? null;
                onFileSelect(files);
              }}
            />

            <button type="button" className="ipricing-file-selector" onClick={handleChooseFile}>
              Select files
            </button>
            <h3>Upload pricing YAML (optional)</h3>
            <p style={{margin: "1em auto"}} className="help-text">
              Uploaded YAMLs appear in the pricing context above so you can
              remove them at any time.
            </p>
          </section>

          <section className="search-ipricings">
            <button
              type="button"
              className="context-add-url"
              onClick={handleOpenModal}
            >
              Search pricings
            </button>
            <h3>Add SPHERE iPricing (optional)</h3>
            <p style={{ margin: "1em auto" }} className="help-text">
              Add iPricings with our SPHERE integration (our iPricing
              repository).
            </p>
            <p style={{ margin: "1em auto" }} className="help-text">
              You can further customize the search if you type a pricing name in
              the search bar.
            </p>
            <Modal open={showPricingModal} onClose={handleCloseModal}>
              <SearchPricings
                onContextAdd={onContextAdd}
                onContextRemove={onSphereContextRemove}
              />
            </Modal>
          </section>
        </div>

        <div className="control-actions">
          <button type="submit" disabled={isSubmitDisabled}>
            {isSubmitting ? "Processing..." : "Ask"}
          </button>
        </div>
      </form>
    </>
  );
}

export default ControlPanel;
