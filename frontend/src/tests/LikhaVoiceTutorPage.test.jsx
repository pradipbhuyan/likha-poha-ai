import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import LikhaVoiceTutorPage from "../pages/LikhaVoiceTutorPage";
import { answerDoubt, getDoubtSuggestions } from "../api/doubt";

vi.mock("../api/syllabus", () => ({
  getSyllabus: vi.fn(async () => ({
    syllabus: {
      "Grade 9": { CBSE: { Science: ["Matter in Our Surroundings"] } },
    },
  })),
}));

vi.mock("../api/doubt", () => ({
  answerDoubt: vi.fn(),
  getDoubtSuggestions: vi.fn(),
}));

vi.mock("../components/likha/LikhaVoicePlayer", () => ({
  default: ({ historyId, onFollowUpReady }) => (
    <div>
      Voice player for {historyId || "unavailable"}
      <button type="button" onClick={onFollowUpReady}>Finish explanation</button>
    </div>
  ),
}));

const user = {
  role: "student",
  username: "student_one",
  grade: "Grade 9",
  board: "CBSE",
  accessCbse: true,
};

async function selectLessonContext() {
  fireEvent.change(await screen.findByLabelText("Subject"), { target: { value: "Science" } });
  fireEvent.change(screen.getByLabelText("Chapter"), {
    target: { value: "Matter in Our Surroundings" },
  });
}

describe("LikhaVoiceTutorPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    delete window.SpeechRecognition;
    delete window.webkitSpeechRecognition;
    getDoubtSuggestions.mockResolvedValue({ doubt_suggestions: [] });
    answerDoubt.mockResolvedValue({
      success: true,
      answer: "A shadow is dark because an opaque object blocks light.",
      source_type: "TEXTBOOK_EXCERPT",
      history_id: "history-42",
      sources: [],
      textbook_visuals: [],
      mentor_suggestions: [],
    });
  });

  test("submits typed questions through the existing secured doubt pipeline", async () => {
    render(<LikhaVoiceTutorPage user={user} />);
    await selectLessonContext();

    const input = await screen.findByLabelText(/your question for likha/i);
    fireEvent.change(input, { target: { value: "Why is a shadow dark?" } });
    fireEvent.click(screen.getByRole("button", { name: /^ask likha$/i }));

    await waitFor(() => {
      expect(answerDoubt).toHaveBeenCalledWith(expect.objectContaining({
        username: "student_one",
        grade: "Grade 9",
        mode: "CBSE",
        board: "CBSE",
        question: "Why is a shadow dark?",
        display_question: "Why is a shadow dark?",
        save_to_history: true,
        require_textbook_grounding: true,
      }));
    });
  });

  test("shows source information and only enables response playback after an answer", async () => {
    render(<LikhaVoiceTutorPage user={user} />);
    await selectLessonContext();

    fireEvent.change(await screen.findByLabelText(/your question for likha/i), {
      target: { value: "Why is a shadow dark?" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^ask likha$/i }));

    expect(await screen.findByText("Textbook-grounded answer")).toBeInTheDocument();
    expect(screen.getByText(/opaque object blocks light/i)).toBeInTheDocument();
    expect(screen.getByText("Voice player for history-42")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /finish explanation/i }));
    expect(await screen.findByText(/do you have a follow-up question/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /speak follow-up/i })).toBeInTheDocument();
  });

  test("shows a recoverable error from the existing answer endpoint", async () => {
    answerDoubt.mockResolvedValueOnce({
      success: false,
      message: "No matching answer is available right now.",
    });

    render(<LikhaVoiceTutorPage user={user} />);
    await selectLessonContext();

    fireEvent.change(await screen.findByLabelText(/your question for likha/i), {
      target: { value: "Explain reflection" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^ask likha$/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("No matching answer is available right now.");
  });

  test("sends a completed voice transcript directly to Likha", async () => {
    class MockRecognition {
      start() {
        this.onstart?.();
        this.onresult?.({
          results: [[{ transcript: "Why is a shadow dark?" }]],
        });
        this.onend?.();
      }

      stop() {}
      abort() {}
    }
    window.SpeechRecognition = MockRecognition;

    render(<LikhaVoiceTutorPage user={user} />);
    await selectLessonContext();

    fireEvent.click(await screen.findByRole("button", { name: /speak your question/i }));

    await waitFor(() => {
      expect(answerDoubt).toHaveBeenCalledWith(expect.objectContaining({
        question: "Why is a shadow dark?",
        display_question: "Why is a shadow dark?",
        save_to_history: true,
        require_textbook_grounding: true,
      }));
    });
  });

  test("sends the active session history with a voice follow-up", async () => {
    let recognitionCount = 0;
    class MockRecognition {
      start() {
        recognitionCount += 1;
        const transcript = recognitionCount === 1 ? "What is reflection?" : "Why does that happen?";
        this.onstart?.();
        this.onresult?.({ results: [[{ transcript }]] });
        this.onend?.();
      }

      stop() {}
      abort() {}
    }
    window.SpeechRecognition = MockRecognition;

    render(<LikhaVoiceTutorPage user={user} />);
    await selectLessonContext();

    fireEvent.click(await screen.findByRole("button", { name: /speak your question/i }));
    await waitFor(() => expect(answerDoubt).toHaveBeenCalledTimes(1));

    fireEvent.click(await screen.findByRole("button", { name: /finish explanation/i }));
    fireEvent.click(screen.getByRole("button", { name: /speak follow-up/i }));

    await waitFor(() => {
      expect(answerDoubt).toHaveBeenLastCalledWith(expect.objectContaining({
        question: "Why does that happen?",
        is_follow_up: true,
        conversation_history: [{
          question: "What is reflection?",
          answer: "A shadow is dark because an opaque object blocks light.",
        }],
      }));
    });
  });

  test("requires a selected subject and chapter before asking Likha", async () => {
    render(<LikhaVoiceTutorPage user={user} />);

    fireEvent.change(await screen.findByLabelText(/your question for likha/i), {
      target: { value: "Summarise this lesson." },
    });
    fireEvent.click(screen.getByRole("button", { name: /^ask likha$/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/choose both a subject and chapter/i);
    expect(answerDoubt).not.toHaveBeenCalled();
  });

  test("does not submit Hindi-script speech while English recognition is selected", async () => {
    class MockRecognition {
      start() {
        this.onstart?.();
        this.onresult?.({
          results: [[{ transcript: "मुझे प्रकाश के बारे में बताइए" }]],
        });
        this.onend?.();
      }

      stop() {}
      abort() {}
    }
    window.SpeechRecognition = MockRecognition;

    render(<LikhaVoiceTutorPage user={user} />);

    fireEvent.click(await screen.findByRole("button", { name: /speak your question/i }));

    expect(await screen.findByText(/choose hindi under voice language/i)).toBeInTheDocument();
    expect(answerDoubt).not.toHaveBeenCalled();
  });

  test("keeps typed questions available when browser voice input is unsupported", async () => {
    render(<LikhaVoiceTutorPage user={user} />);

    expect(await screen.findByText(/voice input is not available/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/your question for likha/i)).not.toBeDisabled();
    expect(screen.getByRole("button", { name: /speak your question/i })).toBeDisabled();
  });
});
