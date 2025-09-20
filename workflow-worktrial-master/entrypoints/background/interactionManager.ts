import { browser } from "wxt/browser";
import { InteractionEvent } from "../types/interactions";
import { config } from "../../src/config";

// Ring buffer implementation
class RingBuffer<T> {
  private items: T[] = [];
  private maxSize: number;

  constructor(maxSize: number) {
    this.maxSize = maxSize;
  }

  push(item: T): void {
    this.items.push(item);
    if (this.items.length > this.maxSize) {
      this.items.shift();
    }
  }

  getItems(): T[] {
    return [...this.items];
  }

  clear(): void {
    this.items = [];
  }
}

// Global event buffer (configurable size across all tabs)
const globalEvents = new RingBuffer<InteractionEvent>(config.ringBufferSize);

// Per-tab event buffers (configurable size per tab)
const perTabEvents = new Map<number, RingBuffer<InteractionEvent>>();

// Track last active tab per window to enrich tab-switch events
const windowActiveTabId = new Map<number, number>();

// Track last normalized URL per tab to emit page-load on SPA navigations
const lastNormalizedByTab = new Map<number, string>();
// Track last actual URL per tab to include as referrer in page-load payload
const lastActualUrlByTab = new Map<number, string>();

// Gmail URL detection and normalization
function isGmailUrl(urlString: string): boolean {
  try {
    const u = new URL(urlString);
    return u.hostname === "mail.google.com" && u.pathname.startsWith("/mail/");
  } catch {
    return false;
  }
}

// Normalize URL: origin + pathname; for Gmail include hash
function normalizeUrl(urlString: string): string {
  try {
    const u = new URL(urlString);
    return isGmailUrl(urlString)
      ? u.origin + u.pathname + (u.hash || "")
      : u.origin + u.pathname;
  } catch {
    return urlString;
  }
}

// Simple filter for internal/new-tab pages we don't want to log
function shouldIgnorePage(urlString: string | undefined): boolean {
  if (!urlString) return true;
  const lower = urlString.toLowerCase();
  if (
    lower === "about:blank" ||
    lower.startsWith("about:newtab") ||
    lower.startsWith("about:home")
  ) {
    return true;
  }
  try {
    const u = new URL(urlString);
    const scheme = u.protocol;
    const host = (u.host || "").toLowerCase();
    const internalSchemes = new Set([
      "chrome:",
      "edge:",
      "brave:",
      "moz-extension:",
      "chrome-extension:",
      "safari-extension:",
      "vivaldi:",
      "opera:",
      "chrome-search:",
    ]);
    if (internalSchemes.has(scheme)) return true;
    // Specific new tab hosts for chromium-based browsers
    if (
      (scheme === "chrome:" || scheme === "edge:" || scheme === "brave:") &&
      host === "newtab"
    )
      return true;
  } catch {
    // If URL can't be parsed, be conservative and ignore
    return true;
  }
  return false;
}

/**
 * Adds an event to both global and tab-specific buffers
 */
function addEvent(event: InteractionEvent): void {
  console.log("[Background] 📥 Adding event to buffers");
  console.log("[Background]   Event ID:", event.id);
  console.log("[Background]   Type:", event.type);
  console.log("[Background]   Tab ID:", event.tabId || "N/A");
  console.log("[Background]   Window ID:", event.windowId || "N/A");

  // Add to global buffer
  globalEvents.push(event);
  console.log(
    `[Background] 📊 Global Buffer: Added ${event.type} event. Total events: ${
      globalEvents.getItems().length
    }/${config.ringBufferSize}`
  );

  // Persist every event for retrieval
  try {
    const key = `ev:${event.id}`;
    browser.storage.local
      .set({ [key]: event })
      .then(() => {
        console.log(`[Background] 💾 Event stored with key: ${key}`);
      })
      .catch((err) => {
        console.error("[Background] ❌ Failed to store event:", err);
      });
  } catch (err) {
    console.error("[Background] ❌ Error storing event:", err);
  }

  // Add to tab-specific buffer if we have a tabId
  if (event.tabId) {
    let tabBuffer = perTabEvents.get(event.tabId);
    if (!tabBuffer) {
      tabBuffer = new RingBuffer<InteractionEvent>(config.ringBufferSize);
      perTabEvents.set(event.tabId, tabBuffer);
      console.log(`[Background] 📑 Created new buffer for tab ${event.tabId}`);
    }
    tabBuffer.push(event);
    console.log(
      `[Background] 📑 Tab ${event.tabId} Buffer: Added ${
        event.type
      } event. Total: ${tabBuffer.getItems().length}/${config.ringBufferSize}`
    );
  } else {
    console.log("[Background] ⚠️ No tab ID for this event");
  }
}

/**
 * Handles interaction events from content scripts
 */
function handleInteractionMessage(event: InteractionEvent, sender: any): void {
  console.log("[Background] ====================================");
  console.log("[Background] Received interaction from content");
  console.log("[Background] Event type:", event.type);
  console.log("[Background] Sender tab ID:", sender.tab?.id);
  console.log("[Background] Sender window ID:", sender.tab?.windowId);
  console.log("[Background] Sender URL:", sender.tab?.url);
  console.log("[Background] Event data:", event);

  // Enrich with tab and window info
  const enrichedEvent: InteractionEvent = {
    ...event,
    tabId: sender.tab?.id,
    windowId: sender.tab?.windowId,
    url: event.url || sender.tab?.url,
    title: event.title || sender.tab?.title,
  };

  console.log("[Background] Enriched event with metadata:");
  console.log("[Background]   - Tab ID:", enrichedEvent.tabId);
  console.log("[Background]   - Window ID:", enrichedEvent.windowId);
  console.log("[Background]   - URL:", enrichedEvent.url);
  console.log("[Background]   - Title:", enrichedEvent.title);
  console.log("[Background] ====================================");

  addEvent(enrichedEvent);
}

/**
 * Handles tab activation (switching tabs)
 */
function handleTabActivated(activeInfo: any): void {
  const { tabId: newTabId, windowId } = activeInfo;

  const oldTabId = windowActiveTabId.get(windowId);
  windowActiveTabId.set(windowId, newTabId);

  // Attempt to include URLs
  (async () => {
    let newTabUrl: string | undefined;
    let newTabTitle: string | undefined;
    let oldTabUrl: string | undefined;
    try {
      const newTab = await browser.tabs.get(newTabId);
      newTabUrl = newTab?.url || undefined;
      newTabTitle = newTab?.title || undefined;
    } catch {}
    if (oldTabId !== undefined) {
      try {
        const oldTab = await browser.tabs.get(oldTabId);
        oldTabUrl = oldTab?.url || undefined;
      } catch {}
    }

    const event: InteractionEvent = {
      id: crypto.randomUUID(),
      type: "tab-switch",
      timestamp: Date.now(),
      tabId: newTabId,
      windowId,
      url: newTabUrl,
      title: newTabTitle,
      payload: {
        prevTabId: oldTabId,
        currentTabId: newTabId,
        prevTabUrl: oldTabUrl,
        currentTabUrl: newTabUrl,
      },
    };

    addEvent(event);
    console.log("Tab switch logged", { oldTabId, newTabId });
  })();
}

/**
 * Emits a page-load InteractionEvent whenever a tab's normalized URL changes
 */
async function handleTabUpdated(
  tabId: number,
  changeInfo: any,
  tab: any
): Promise<void> {
  const urlString = changeInfo.url || tab.url;
  if (!urlString) return;

  const normalized = normalizeUrl(urlString);
  const previous = lastNormalizedByTab.get(tabId);
  if (previous === normalized) return;
  lastNormalizedByTab.set(tabId, normalized);

  // Ignore internal/new-tab pages
  if (shouldIgnorePage(urlString)) {
    console.log("Ignoring page-load for internal/new tab", {
      tabId,
      url: urlString,
    });
    return;
  }

  // Small delay for Gmail to update title
  if (isGmailUrl(urlString)) {
    await new Promise((r) => setTimeout(r, 100));
  }

  let latest: any = null;
  try {
    latest = await browser.tabs.get(tabId);
  } catch {}

  const effectiveUrl = latest?.url || tab.url || urlString;
  const effectiveTitle = latest?.title || tab.title;
  const effectiveWindowId = latest?.windowId ?? tab.windowId;
  const referrerUrl = lastActualUrlByTab.get(tabId);

  // Try to get markdown from content script
  let markdown = "";
  try {
    const response = await browser.tabs.sendMessage(tabId, {
      type: "get-page-markdown",
    });
    if ((response as any)?.success) {
      markdown = (response as any).markdown || "";
    }
  } catch {
    console.log("Could not get markdown from tab", tabId);
  }

  const event: InteractionEvent = {
    id: crypto.randomUUID(),
    type: "page-load",
    timestamp: Date.now(),
    tabId,
    windowId: effectiveWindowId,
    url: effectiveUrl,
    title: effectiveTitle,
    payload: {
      url: effectiveUrl,
      title: effectiveTitle,
      referrer: referrerUrl,
      markdown,
    },
  };

  addEvent(event);

  if (effectiveUrl) {
    lastActualUrlByTab.set(tabId, effectiveUrl);
  }
  console.log("Normalized URL changed; logged page-load", {
    tabId,
    url: effectiveUrl,
    normalized,
  });
}

/**
 * Handles tab removal and cleans up tab buffer
 */
function handleTabRemoved(tabId: number, removeInfo: any): void {
  // Try to get tab info before cleanup
  (async () => {
    let tabUrl: string | undefined;
    let tabTitle: string | undefined;
    try {
      const tab = await browser.tabs.get(tabId);
      tabUrl = tab?.url;
      tabTitle = tab?.title;
    } catch {
      // Tab is already removed
    }

    const event: InteractionEvent = {
      id: crypto.randomUUID(),
      type: "tab-removal",
      timestamp: Date.now(),
      tabId,
      windowId: removeInfo.windowId,
      url: tabUrl,
      title: tabTitle,
      payload: {
        tabId,
        url: tabUrl,
        title: tabTitle,
      },
    };

    addEvent(event);
    console.log("Tab removal logged", { tabId, url: tabUrl, title: tabTitle });
  })();

  // Clean up tab buffer
  if (perTabEvents.has(tabId)) {
    perTabEvents.delete(tabId);
    console.log(`Cleaned up buffer for tab ${tabId}`);
  }
  if (lastNormalizedByTab.has(tabId)) {
    lastNormalizedByTab.delete(tabId);
  }
  if (lastActualUrlByTab.has(tabId)) {
    lastActualUrlByTab.delete(tabId);
  }
}

/**
 * Get recent interactions from storage
 */
export async function getRecentInteractions(
  limit?: number
): Promise<InteractionEvent[]> {
  const actualLimit = limit || config.apiExportSize;
  console.log("[Background] Getting recent interactions from storage...");
  try {
    const allItems = await browser.storage.local.get(null);
    console.log(
      "[Background] Total items in storage:",
      Object.keys(allItems).length
    );

    const events: InteractionEvent[] = [];

    // Collect all events from storage
    for (const [key, value] of Object.entries(allItems)) {
      if (key.startsWith("ev:")) {
        events.push(value as InteractionEvent);
      }
    }

    console.log(`[Background] Found ${events.length} events in storage`);

    // Also check in-memory buffer
    const memoryEvents = globalEvents.getItems();
    console.log(
      `[Background] Found ${memoryEvents.length} events in memory buffer`
    );

    // Combine and deduplicate
    const allEvents = [...events, ...memoryEvents];
    const uniqueEvents = Array.from(
      new Map(allEvents.map((e) => [e.id, e])).values()
    );

    console.log(`[Background] Total unique events: ${uniqueEvents.length}`);

    // Sort by timestamp (newest first) and limit
    uniqueEvents.sort((a, b) => b.timestamp - a.timestamp);
    const result = uniqueEvents.slice(0, actualLimit);

    console.log(
      `[Background] Returning ${result.length} events (limit: ${actualLimit})`
    );
    return result;
  } catch (error) {
    console.error("[Background] Failed to get recent interactions:", error);
    return [];
  }
}

/**
 * Message listener for interaction events and data requests
 */
const handleMessage = (
  message: any,
  sender: any,
  sendResponse: (response?: any) => void
): true | void => {
  console.log("[Background] Received message:", message.type);

  if (message.type === "dex-interaction") {
    console.log("[Background] Processing interaction event...");
    handleInteractionMessage(message.payload, sender);
    return; // Don't keep the message channel open
  }

  // Handle requests for interaction data
  if (message.type === "get-recent-interactions") {
    console.log(
      "[Background] Getting recent interactions, limit:",
      message.limit || config.apiExportSize
    );
    getRecentInteractions(message.limit).then((interactions) => {
      console.log(
        "[Background] Sending interactions to popup:",
        interactions.length
      );
      sendResponse({ interactions });
    });
    return true; // Keep channel open for async response
  }
};

/**
 * Adds all interaction event listeners
 */
export function setupInteractionListeners(): void {
  console.log("[Background] Setting up interaction listeners...");

  // Message listener for interaction events
  if (!browser.runtime.onMessage.hasListener(handleMessage as any)) {
    browser.runtime.onMessage.addListener(handleMessage as any);
    console.log("[Background] Message listener added");
  }

  // Tab activation listener
  if (!browser.tabs.onActivated.hasListener(handleTabActivated)) {
    browser.tabs.onActivated.addListener(handleTabActivated);
    console.log("[Background] Tab activation listener added");
  }

  // Tab removal listener
  if (!browser.tabs.onRemoved.hasListener(handleTabRemoved)) {
    browser.tabs.onRemoved.addListener(handleTabRemoved);
    console.log("[Background] Tab removal listener added");
  }

  // Tab updated listener - detect normalized URL changes
  if (!browser.tabs.onUpdated.hasListener(handleTabUpdated)) {
    browser.tabs.onUpdated.addListener(handleTabUpdated);
    console.log("[Background] Tab updated listener added");
  }

  console.log("[Background] All interaction event listeners setup complete!");
}
