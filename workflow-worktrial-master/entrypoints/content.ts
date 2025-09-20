import { initializeInteractionLogger } from "./content/interactionLogger";
import { getCachedPageMarkdown } from "./content/pageConverter";
import { browser } from "wxt/browser";

export default defineContentScript({
  matches: ["<all_urls>"],
  runAt: "document_idle",
  main() {
    console.log("[Content] ========================================");
    console.log("[Content] Content script loaded on:", window.location.href);
    console.log("[Content] Document readyState:", document.readyState);
    console.log("[Content] ========================================");

    // Initialize interaction logging
    initializeInteractionLogger();

    // Listen for messages from background script
    browser.runtime.onMessage.addListener((message, _sender, sendResponse) => {
      console.log("[Content] Received message from background:", message.type);
      if (message.type === "get-page-markdown") {
        const markdown = getCachedPageMarkdown();
        sendResponse({ success: true, markdown });
        return true;
      }
    });
    
    console.log("[Content] Setup complete!");
  },
});
