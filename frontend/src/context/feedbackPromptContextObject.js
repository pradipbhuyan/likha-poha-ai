import { createContext } from "react";

// Split into its own plain (non-component) module so FeedbackPromptContext.jsx
// exports only the provider component and useFeedbackPrompt.js exports only
// the hook — react-refresh/only-export-components requires each file that
// exports a component to export nothing else.
export const FeedbackPromptContext = createContext(null);
