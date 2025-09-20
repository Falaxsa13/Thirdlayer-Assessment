export interface InteractionEvent {
  id: string; // uuid
  type:
    | "page-load"
    | "click"
    | "highlight"
    | "type"
    | "copy"
    | "paste"
    | "tab-switch"
    | "tab-removal";
  timestamp: number; // ms since epoch
  tabId?: number;
  windowId?: number;
  url?: string;
  title?: string;
  payload?: any; // event-specific details
}

/** Human-readable element data, always present when an element is involved */
export interface ElementDescriptor {
  tag: string; // 'button'
  text?: string; // visible text - trimmed
  id?: string;
  ariaLabel?: string;
  role?: string;
  url?: string;
}

/**
 * Builds a human-readable element descriptor for logging
 */
export function buildElementDescriptor(element: Element): ElementDescriptor {
  const descriptor: ElementDescriptor = {
    tag: element.tagName.toLowerCase(),
  };

  // Get visible text content
  const text = element.textContent?.trim();
  if (text && text.length > 0) {
    descriptor.text = text.length > 120 ? text.substring(0, 120) + "…" : text;
  }

  // Get identifying attributes
  if (element.id) {
    descriptor.id = element.id;
  }

  const ariaLabel = element.getAttribute("aria-label");
  if (ariaLabel) {
    descriptor.ariaLabel = ariaLabel;
  }

  const role = element.getAttribute("role");
  if (role) {
    descriptor.role = role;
  }

  // Include URL for anchors
  if (descriptor.tag === "a") {
    const anchor = element as HTMLAnchorElement;
    if (anchor && anchor.href) {
      descriptor.url = anchor.href;
    } else {
      const hrefAttr = element.getAttribute("href");
      if (hrefAttr) {
        // Let the browser resolve relative URLs if possible
        try {
          descriptor.url = new URL(hrefAttr, window.location.href).href;
        } catch {
          descriptor.url = hrefAttr;
        }
      }
    }
  }

  return descriptor;
}