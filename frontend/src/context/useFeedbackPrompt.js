import { useContext } from "react";
import { FeedbackPromptContext } from "./feedbackPromptContextObject";

/** Returns { triggerFeedbackPrompt } from the nearest FeedbackPromptProvider. */
export function useFeedbackPrompt() {
  const ctx = useContext(FeedbackPromptContext);
  if (!ctx) {
    // Graceful fallback outside the provider (e.g. unit tests)
    return { triggerFeedbackPrompt: () => {} };
  }
  return ctx;
}
