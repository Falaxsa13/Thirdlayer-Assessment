import { browser } from "wxt/browser";
import { setupInteractionListeners } from "./background/interactionManager";

export default defineBackground(() => {
  console.log("Background script started", { id: browser.runtime.id });

  // Set up interaction tracking
  setupInteractionListeners();
});
