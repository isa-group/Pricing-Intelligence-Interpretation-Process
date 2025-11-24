import { useEffect } from "react";
import { createPortal } from "react-dom";
import CrossIcon from "./CrossIcon";

interface ModalProps {
  open: boolean;
  children: React.ReactElement;
  onClose: () => void;
}

function Modal({ open, children, onClose }: ModalProps) {
  
    const handleCloseKeyboard = (event: KeyboardEvent) => {
    if (event.key === "Escape") {
      onClose();
    }
  };

  useEffect(() => {
    window.addEventListener("keydown", handleCloseKeyboard);
    return () => window.removeEventListener("keydown", handleCloseKeyboard);
  });

  if (!open) {
    return null;
  }

  return createPortal(
    <>
      <div className="modal-overlay" onClick={onClose}></div>
      <div className="modal-content">
        <button
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              onClose();
            }
          }}
          onClick={onClose}
        >
          <CrossIcon width={24} height={24} />
        </button>
        {children}
      </div>
    </>,
    document.getElementById("portal") as HTMLElement
  );
}

export default Modal;
