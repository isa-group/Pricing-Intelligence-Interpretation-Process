import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import ChatTranscript from "./components/ChatTranscript";
import ControlPanel from "./components/ControlPanel";
import type {
  ChatMessage,
  PricingContextItem,
  PromptPreset,
  ContextInputType,
  NotificationUrlEvent,
  ChatRequest,
} from "./types";
import { PROMPT_PRESETS } from "./prompts";
import { ThemeContext, ThemeType } from "./context/themeContext";
import {
  chatWithAgent,
  createContextBodyPayload,
  deleteYamlPricing,
  extractHttpReferences,
  extractPricingUrls,
  uploadYamlPricing,
  diffPricingContextWithQuestionUrls,
} from "./utils";
import { PricingContext } from "./context/pricingContext";
import { url } from "inspector";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8086";

function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [contextItems, setContextItems] = useState<PricingContextItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [theme, setTheme] = useState<ThemeType>("dark");

  useEffect(() => {
    const eventSource = new EventSource(`${API_BASE_URL}/events`);

    eventSource.onopen = () => console.log("Connection established");

    eventSource.addEventListener("url_transform", (event: MessageEvent) => {
      const notification: NotificationUrlEvent = JSON.parse(event.data);
      setContextItems((previous) =>
        previous.map((item) =>
          item.kind === "url" && item.id === notification.id
            ? { ...item, transform: "done", value: notification.yaml_content }
            : item
        )
      );
    });
    return () => eventSource.close();
  }, []);

  const detectedPricingUrls = useMemo(
    () => extractPricingUrls(question),
    [question]
  );

  const isSubmitDisabled = useMemo(() => {
    const hasQuestion = Boolean(question.trim());
    return isLoading || !hasQuestion;
  }, [question, isLoading]);

  const getNotUploadedUserAndPresetItems = () =>
    contextItems.filter(
      (item) =>
        item.origin &&
        item.kind === "yaml" &&
        (item.origin === "user" || item.origin === "preset") &&
        !item.uploaded
    );

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    if (typeof window !== "undefined") {
      window.localStorage.setItem("pricing-theme", theme);
    }

    const itemsToUpload = getNotUploadedUserAndPresetItems();
    if (itemsToUpload.length > 0) {
      const uploadPromises = itemsToUpload.map((item) =>
        uploadYamlPricing(item.id, item.value)
      );
      Promise.all(uploadPromises)
        .then((uploadedItems) => {
          setContextItems((previousItems) =>
            previousItems.map((item) =>
              uploadedItems.includes(item.id)
                ? { ...item, uploaded: true }
                : item
            )
          );
        })
        .catch((err) => console.error("Upload failed", err));
    }
  }, [theme, contextItems]);

  const createPricingContextItems = (
    contextInputItems: ContextInputType[]
  ): PricingContextItem[] =>
    contextInputItems
      .map((item) => ({
        ...item,
        value: item.value.trim(),
        id: crypto.randomUUID(),
      }))
      .filter(
        (item) =>
          !contextItems.some(
            (stateItem) =>
              stateItem.kind === item.kind && stateItem.value === item.value
          )
      );

  const addContextItems = (inputs: ContextInputType[]) => {
    if (inputs.length === 0) {
      return;
    }

    const newPricingContextItems: PricingContextItem[] =
      createPricingContextItems(inputs);

    setContextItems((previous) => [...previous, ...newPricingContextItems]);
  };

  const addContextItem = (input: ContextInputType) => {
    addContextItems([input]);
  };

  const removeContextItem = (id: string) => {
    const deletePromises = contextItems
      .filter(
        (item) =>
          item.id === id &&
          item.kind === "yaml" &&
          item.origin &&
          (item.origin === "user" || item.origin === "preset")
      )
      .map((item) => deleteYamlPricing(item.id));
    if (deletePromises.length > 0) {
      Promise.all(deletePromises);
    }
    setContextItems((previous) => previous.filter((item) => item.id !== id));
  };

  const clearContext = () => {
    setContextItems([]);
  };

  const toggleTheme = () => {
    setTheme((previous: "light" | "dark") =>
      previous === "dark" ? "light" : "dark"
    );
  };

  const handleFilesSelected = (files: FileList | null) => {
    if (!files || files.length === 0) {
      return;
    }

    const fileArray = Array.from(files);
    Promise.all(
      fileArray.map((file) =>
        file.text().then((content) => ({ name: file.name, content }))
      )
    )
      .then((results) => {
        const inputs: ContextInputType[] = results
          .filter((result) => Boolean(result.content.trim()))
          .map((result) => ({
            kind: "yaml",
            label: result.name,
            value: result.content,
            origin: "user",
            uploaded: false,
          }));

        if (inputs.length > 0) {
          addContextItems(inputs);
        }

        if (inputs.length !== results.length) {
          setMessages((prev) => [
            ...prev,
            {
              id: crypto.randomUUID(),
              role: "assistant",
              content:
                "One or more uploaded files were empty and were skipped.",
              createdAt: new Date().toISOString(),
            },
          ]);
        }
      })
      .catch((error) => {
        console.error("Failed to read YAML file", error);
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            content: "Could not read the uploaded file. Please try again.",
            createdAt: new Date().toISOString(),
          },
        ]);
      });
  };

  const handlePromptSelect = (preset: PromptPreset) => {
    setQuestion(preset.question);
    if (preset.context.length > 0) {
      addContextItems(
        preset.context.map((entry) => ({
          kind: entry.kind,
          label: entry.label,
          value: entry.value,
          uploaded: false,
          origin: "preset",
        }))
      );
    }
  };

  const handleNewConversation = () => {
    setMessages([]);
    setQuestion("");
    setContextItems([]);
    setIsLoading(false);
  };

  const getUrlItems = () =>
    contextItems
      .filter((item) => item.kind === "url")
      .map((item) => ({ id: item.id, url: item.url }));

  const getUniqueYamlFiles = () =>
    Array.from(
      new Set(
        contextItems
          .filter((item) => item.kind === "yaml")
          .map((item) => item.value)
      )
    );

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (isSubmitDisabled) return;

    const trimmedQuestion = question.trim();
    if (!trimmedQuestion) return;

    const newlyDetected = diffPricingContextWithQuestionUrls(
      contextItems,
      detectedPricingUrls
    );
    if (newlyDetected.length > 0) {
      addContextItems(
        newlyDetected.map((url) => ({
          kind: "url",
          url: url,
          label: url,
          value: url,
          origin: "detected",
          uploaded: false,
          transform: "pending",
        }))
      );
    }

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmedQuestion,
      createdAt: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    setContextItems((prev) =>
      prev.map((item) =>
        item.kind === "url" ? { ...item, transform: "pending" } : item
      )
    );

    try {
      const requestBody: ChatRequest = {
        question: trimmedQuestion,
        ...createContextBodyPayload(getUrlItems(), getUniqueYamlFiles()),
      };
      const data = await chatWithAgent(requestBody);

      const assistantMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: data.answer ?? "No response available.",
        createdAt: new Date().toISOString(),
        metadata: {
          plan: data.plan ?? undefined,
          result: data.result ?? undefined,
        },
      };
      setMessages((prev) => [...prev, assistantMessage]);

      const planReferences = extractHttpReferences(data?.plan);
      const resultReferences = extractHttpReferences(data?.result);
      const agentDiscoveredUrls = [...planReferences, ...resultReferences];
      if (agentDiscoveredUrls.length > 0) {
        addContextItems(
          agentDiscoveredUrls.map((url) => ({
            kind: "url",
            url: url,
            label: url,
            value: url,
            origin: "agent",
            uploaded: false,
            transform: "not-started",
          }))
        );
      }
    } catch (error) {
      const assistantMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: `Error: ${(error as Error).message}`,
        createdAt: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } finally {
      setIsLoading(false);
      setQuestion("");
    }
  };

  return (
    <PricingContext.Provider value={contextItems}>
      <ThemeContext.Provider value={theme}>
        <div className="app">
          <header className="header-bar">
            <div>
              <h1>H.A.R.V.E.Y. Pricing Assistant</h1>
              <p>
                Ask about optimal subscriptions and pricing insights using the
                Holistic Analysis and Regulation Virtual Expert for You
                (H.A.R.V.E.Y.) agent.
              </p>
            </div>
            <div className="header-actions">
              <button
                type="button"
                className="session-reset"
                onClick={handleNewConversation}
                disabled={isLoading}
              >
                New conversation
              </button>
              <button
                type="button"
                className="theme-toggle"
                onClick={toggleTheme}
                aria-label="Toggle color theme"
              >
                {theme === "dark"
                  ? "Switch to light mode"
                  : "Switch to dark mode"}
              </button>
            </div>
          </header>
          <main>
            <section className="chat-panel">
              <ChatTranscript
                messages={messages}
                isLoading={isLoading}
                promptPresets={PROMPT_PRESETS}
                onPresetSelect={handlePromptSelect}
              />
            </section>
            <section className="control-panel">
              <ControlPanel
                question={question}
                detectedPricingUrls={detectedPricingUrls}
                contextItems={contextItems}
                isSubmitting={isLoading}
                isSubmitDisabled={isSubmitDisabled}
                onQuestionChange={setQuestion}
                onSubmit={handleSubmit}
                onFileSelect={handleFilesSelected}
                onContextAdd={addContextItem}
                onContextRemove={removeContextItem}
                onContextClear={clearContext}
              />
            </section>
          </main>
        </div>
      </ThemeContext.Provider>
    </PricingContext.Provider>
  );
}

export default App;
