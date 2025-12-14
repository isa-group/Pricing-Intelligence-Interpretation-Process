import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "../../src/App";

const user = userEvent.setup({ applyAccept: true });

describe("Pricing Context Suite", () => {
  it("Given URLs should appear in context", async () => {
    render(<App />);

    fireEvent.change(screen.getByPlaceholderText("https://example.com/pricing"), {target: {value: "https://example.org/testing"}})
    await user.click(screen.getByRole("button", {name: "Add URL"}))
    const container = document.querySelector(".context-manager") as HTMLElement;

    await within(container).findByText("https://example.org/testing")
  });
  it("Given YAML files should appear in context", async () => {
    render(<App />);
    const files = [
      new File(["saasName: Test1\n"], "test1.yml"),
      new File(["saasName: Test2\n"], "test2.yaml"),
    ];

    const fileInput: HTMLInputElement = screen.getByLabelText(/Upload pricing/i);
    await user.upload(fileInput, files);

    const container = document.querySelector(".context-manager") as HTMLElement;
    const contextItems = await within(container).findAllByText(/test\d.ya?ml/i);
    expect(contextItems).toHaveLength(2);
  });
});
