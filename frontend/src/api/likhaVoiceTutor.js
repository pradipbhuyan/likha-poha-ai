import { authFetch } from "./authClient";

/** Request speech for a server-owned doubt-history answer only. */
export function speakDoubtAnswer({
  historyId,
  language = "en-IN",
  replyStyle = "full",
  includeFirstAnswerGreeting = false,
  progressive = false,
  segmentIndex = 0,
}) {
  return authFetch("/api/likha/speak-doubt-answer", {
    method: "POST",
    body: JSON.stringify({
      history_id: historyId,
      language,
      reply_style: replyStyle,
      include_first_answer_greeting: includeFirstAnswerGreeting,
      progressive,
      segment_index: segmentIndex,
    }),
  });
}
