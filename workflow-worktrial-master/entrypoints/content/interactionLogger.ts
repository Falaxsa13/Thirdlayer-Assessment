import { browser } from "wxt/browser";
import { InteractionEvent, buildElementDescriptor } from "../types/interactions";
import { getCachedPageMarkdown } from "./pageConverter";

// Track previous values to detect changes
const previousValues = new WeakMap<Element, string>();

// Track last non-empty highlighted text to gate clear events
let lastHighlightSelection = "";

/**
 * Sends an interaction event to the background script
 */
function sendInteractionEvent(
  event: Omit<InteractionEvent, "tabId" | "windowId">
) {
  console.log("[Content] ====================================");
  console.log("[Content] Sending interaction event");
  console.log("[Content]   Type:", event.type);
  console.log("[Content]   ID:", event.id);
  console.log("[Content]   URL:", event.url || window.location.href);
  console.log("[Content]   Title:", event.title || document.title);
  console.log("[Content]   Timestamp:", new Date(event.timestamp).toISOString());
  console.log("[Content]   Payload:", event.payload);
  console.log("[Content] ====================================");
  
  browser.runtime
    .sendMessage({
      type: "dex-interaction",
      payload: event,
    })
    .then(() => {
      console.log("[Content] ✅ Successfully sent event:", event.type);
    })
    .catch((error) => {
      console.error("[Content] ❌ Failed to send interaction event:", error);
    });
}

/**
 * Checks if an element is interactive
 */
function isInteractiveElement(element: Element): boolean {
  if (!(element instanceof HTMLElement)) return false;

  const interactiveElements = new Set([
    "a",
    "button",
    "details",
    "embed",
    "input",
    "label",
    "menu",
    "menuitem",
    "object",
    "select",
    "textarea",
    "summary",
  ]);

  const interactiveRoles = new Set([
    "button",
    "menu",
    "menuitem",
    "link",
    "checkbox",
    "radio",
    "slider",
    "tab",
    "tabpanel",
    "textbox",
    "combobox",
    "grid",
    "listbox",
    "option",
    "progressbar",
    "scrollbar",
    "searchbox",
    "switch",
    "tree",
    "treeitem",
    "spinbutton",
    "tooltip",
  ]);

  const tagName = element.tagName.toLowerCase();
  const role = element.getAttribute("role");
  const ariaRole = element.getAttribute("aria-role");
  const tabIndex = element.getAttribute("tabindex");

  const hasInteractiveRole =
    interactiveElements.has(tagName) ||
    (role !== null && interactiveRoles.has(role)) ||
    (ariaRole !== null && interactiveRoles.has(ariaRole)) ||
    (tabIndex !== null && tabIndex !== "-1");

  if (hasInteractiveRole) return true;

  const hasClickHandler =
    (element as HTMLElement).onclick !== null ||
    element.getAttribute("onclick") !== null ||
    element.hasAttribute("ng-click") ||
    element.hasAttribute("@click") ||
    element.hasAttribute("v-on:click");

  const hasAriaProps =
    element.hasAttribute("aria-expanded") ||
    element.hasAttribute("aria-pressed") ||
    element.hasAttribute("aria-selected") ||
    element.hasAttribute("aria-checked");

  const isDraggable =
    (element as HTMLElement).draggable ||
    element.getAttribute("draggable") === "true";

  return hasAriaProps || hasClickHandler || isDraggable;
}

/**
 * Handles click events on interactive elements
 */
function handleClick(event: MouseEvent) {
  console.log("[Content] Click detected!");
  
  let target = event.target as Element | null;
  if (!target) {
    console.log("[Content] No target for click");
    return;
  }

  // Skip our own UI elements
  if (target.closest("#launcher-root, [data-extension-ui]")) {
    console.log("[Content] Skipping extension UI click");
    return;
  }

  // Walk up the DOM tree to find the nearest interactive element
  let interactiveEl: Element | null = target;
  while (interactiveEl && !isInteractiveElement(interactiveEl)) {
    interactiveEl = interactiveEl.parentElement;
  }

  if (!interactiveEl) {
    console.log("[Content] No interactive element found for click");
    return; // Nothing interactive found
  }

  console.log("[Content] Interactive element found:", interactiveEl.tagName);
  const element = buildElementDescriptor(interactiveEl);

  sendInteractionEvent({
    id: crypto.randomUUID(),
    type: "click",
    timestamp: Date.now(),
    payload: {
      element,
    },
  });
}

/**
 * Handles focus events to track initial value
 */
function handleFocus(event: FocusEvent) {
  const target = event.target as HTMLElement;
  if (!target || target.closest("#launcher-root, [data-extension-ui]")) {
    return;
  }

  // Skip password fields for privacy
  if (target instanceof HTMLInputElement && target.type === "password") {
    return;
  }

  // Store initial value when field is focused - trim it to match comparison
  const currentValue = (
    (target as HTMLInputElement).value ||
    target.textContent ||
    ""
  ).trim();
  previousValues.set(target, currentValue);
}

/**
 * Handles blur events to detect text changes
 */
function handleBlur(event: FocusEvent) {
  const target = event.target as HTMLElement;
  if (!target || target.closest("#launcher-root, [data-extension-ui]")) {
    return;
  }

  // Skip password fields for privacy
  if (target instanceof HTMLInputElement && target.type === "password") {
    return;
  }

  const currentValue = (
    (target as HTMLInputElement).value ||
    target.textContent ||
    ""
  ).trim();
  const previousValue = previousValues.get(target) || "";

  // Only log if value actually changed and is non-empty
  if (
    currentValue !== previousValue &&
    currentValue.length > 0 &&
    previousValues.has(target)
  ) {
    sendInteractionEvent({
      id: crypto.randomUUID(),
      type: "type",
      timestamp: Date.now(),
      payload: {
        element: buildElementDescriptor(target),
        text: currentValue.trim(),
        previousText: previousValue.trim(),
      },
    });
  }

  // Clean up
  previousValues.delete(target);
}

/**
 * Handles Enter key to detect form submission
 */
function handleKeyDown(event: KeyboardEvent) {
  if (event.key !== "Enter") return;

  const target = event.target as HTMLElement;
  if (!target || target.closest("#launcher-root, [data-extension-ui]")) {
    return;
  }

  // Skip password fields for privacy
  if (target instanceof HTMLInputElement && target.type === "password") {
    return;
  }

  const currentValue = (
    (target as HTMLInputElement).value ||
    target.textContent ||
    ""
  ).trim();
  const previousValue = previousValues.get(target) || "";

  // Only log if we have a value and it changed
  if (
    currentValue.length > 0 &&
    currentValue !== previousValue &&
    previousValues.has(target)
  ) {
    sendInteractionEvent({
      id: crypto.randomUUID(),
      type: "type",
      timestamp: Date.now(),
      payload: {
        element: buildElementDescriptor(target),
        text: currentValue.trim(),
        previousText: previousValue.trim(),
        triggeredBy: "enter",
      },
    });

    // Update the stored value so we don't log it again on blur
    previousValues.set(target, currentValue);
  }
}

/**
 * Handles mouse up for selection tracking
 */
function handleMouseUp() {
  // Small delay to let the browser update selection state
  setTimeout(() => {
    const selection = window.getSelection();
    const selectedText = selection?.toString().trim() || "";

    if (!selectedText || !selection || selection.isCollapsed) {
      if (lastHighlightSelection !== "") {
        sendInteractionEvent({
          id: crypto.randomUUID(),
          type: "highlight",
          timestamp: Date.now(),
          payload: {
            highlight_cleared: true,
            previous_content: lastHighlightSelection,
          },
        });
        lastHighlightSelection = "";
      }
      return;
    }

    // Try to get the element containing the selection
    const range = selection.getRangeAt(0);
    const container = range.commonAncestorContainer;
    const element =
      container instanceof Element ? container : container.parentElement;

    if (element && !element.closest("#launcher-root, [data-extension-ui]")) {
      sendInteractionEvent({
        id: crypto.randomUUID(),
        type: "highlight",
        timestamp: Date.now(),
        payload: {
          element: buildElementDescriptor(element),
          selectedText: selectedText.trim(),
        },
      });
      lastHighlightSelection = selectedText.trim();
    }
  }, 0);
}

/**
 * Handles copy events
 */
function handleCopy(event: ClipboardEvent) {
  const target = event.target as Element;
  if (target && target.closest("#launcher-root, [data-extension-ui]")) {
    return;
  }

  // Try to get the actual selected text first
  const selection = window.getSelection();
  let copiedText = "";

  if (selection && !selection.isCollapsed) {
    copiedText = selection.toString();
  } else {
    // Fallback to clipboard data if no selection
    copiedText = event.clipboardData?.getData("text/plain") || "";
  }

  const activeElement = document.activeElement;

  sendInteractionEvent({
    id: crypto.randomUUID(),
    type: "copy",
    timestamp: Date.now(),
    payload: {
      element: activeElement
        ? buildElementDescriptor(activeElement)
        : undefined,
      text: copiedText.trim(),
    },
  });
}

/**
 * Handles paste events
 */
function handlePaste(event: ClipboardEvent) {
  const target = event.target as Element;
  if (target && target.closest("#launcher-root, [data-extension-ui]")) {
    return;
  }

  const clipboardText = event.clipboardData?.getData("text/plain") || "";

  sendInteractionEvent({
    id: crypto.randomUUID(),
    type: "paste",
    timestamp: Date.now(),
    payload: {
      element: buildElementDescriptor(target),
      text: clipboardText.trim(),
    },
  });
}

/**
 * Initializes all interaction logging
 */
export function initializeInteractionLogger() {
  console.log("[Content] Starting interaction logger initialization...");
  try {
    // Click tracking
    document.addEventListener("click", handleClick, true);
    console.log("[Content] Click listener added");

    // Text change tracking
    document.addEventListener("focus", handleFocus, true);
    document.addEventListener("blur", handleBlur, true);
    document.addEventListener("keydown", handleKeyDown, true);
    console.log("[Content] Text change listeners added");

    // Selection/highlighting tracking
    document.addEventListener("mouseup", handleMouseUp, true);
    console.log("[Content] Selection listener added");

    // Copy/paste tracking
    document.addEventListener("copy", handleCopy, true);
    document.addEventListener("paste", handlePaste, true);
    console.log("[Content] Copy/paste listeners added");

    console.log("[Content] Interaction logging initialized successfully!");

    // Send initial page load event with markdown
    setTimeout(() => {
      console.log("[Content] Sending initial page-load event...");
      const markdown = getCachedPageMarkdown();
      sendInteractionEvent({
        id: crypto.randomUUID(),
        type: "page-load",
        timestamp: Date.now(),
        url: window.location.href,
        title: document.title,
        payload: {
          url: window.location.href,
          title: document.title,
          markdown: markdown.substring(0, 1000), // Truncate for initial testing
        },
      });
    }, 1000); // Wait a bit for page to fully load
  } catch (error) {
    console.error("[Content] Failed to initialize interaction logging:", error);
  }
}