import TurndownService from "turndown";

// Configure Turndown with custom options
const turndownService = new TurndownService({
  headingStyle: "atx",
  bulletListMarker: "-",
});

// Custom rule to remove code elements completely
turndownService.addRule("removeCode", {
  filter: ["code", "pre"],
  replacement: function () {
    return ""; // Return empty string to remove code completely
  },
});

// Remove elements that are not visible
turndownService.remove(function (node: any) {
  return (
    node.style?.visibility === "hidden" || node.style?.display === "none"
  );
});

/**
 * Preprocesses HTML by cloning the DOM and cleaning it up
 */
function preprocessHtml(): string {
  const tempDiv = document.createElement("div");
  tempDiv.innerHTML = document.documentElement.outerHTML;

  // Remove any extension UI elements
  const extensionElements = tempDiv.querySelectorAll(
    "#launcher-root, [data-extension-ui], .chat-container, .chat-quote"
  );
  extensionElements.forEach((el) => el.remove());

  // Update all input values in the clone to match their current DOM state
  tempDiv.querySelectorAll("input, textarea").forEach((element) => {
    const selector = element.id
      ? `#${CSS.escape(element.id)}`
      : element.getAttribute("name")
      ? `[name="${CSS.escape(element.getAttribute("name") || "")}"]`
      : null;

    if (selector) {
      const originalElement = document.querySelector(selector) as
        | HTMLInputElement
        | HTMLTextAreaElement;
      if (originalElement) {
        element.setAttribute("value", originalElement.value);
      }
    }
  });

  return tempDiv.innerHTML;
}

/**
 * Converts the current page to markdown
 */
export function getPageMarkdown(): string {
  try {
    const htmlContent = preprocessHtml();
    if (!htmlContent) return "";

    // Convert HTML to Markdown and clean up
    const markdown = turndownService
      .remove(["img", "script", "style", "svg", "noscript"])
      .turndown(htmlContent)
      .replace(/!\[.*?\]\(.*?\)/g, "") // Remove images
      .replace(/(\n\s*){3,}/g, "\n\n") // Replace 3+ newlines with exactly 2
      .trim();

    return markdown;
  } catch (error) {
    console.error("Failed to convert page to markdown:", error);
    return "";
  }
}

// Cache for markdown generation to avoid regenerating too frequently
let markdownCache: { content: string; timestamp: number } | null = null;
const CACHE_TTL = 2000; // 2 seconds

/**
 * Gets page markdown with caching to avoid excessive regeneration
 */
export function getCachedPageMarkdown(): string {
  const now = Date.now();
  
  if (markdownCache && now - markdownCache.timestamp < CACHE_TTL) {
    return markdownCache.content;
  }

  const content = getPageMarkdown();
  markdownCache = { content, timestamp: now };
  return content;
}