import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";

import AvatarNarrator from "../components/AvatarNarrator";
import { getChapterNarration } from "../api/lesson";

vi.mock("../api/lesson", () => ({
  getChapterNarration: vi.fn(),
}));

const milestone = {
  title: "A Kind Word",
  blocks: [
    {
      type: "concept",
      title: "Words can help",
      body_md: "Kind words can make another person feel seen and respected.",
    },
  ],
};

let lastAudio;
let lastUtterance;
let speechSynthesis;

beforeEach(() => {
  window.localStorage.clear();
  lastAudio = null;
  lastUtterance = null;
  getChapterNarration.mockReset();
  getChapterNarration.mockResolvedValue({
    success: true,
    audio_url: "https://cdn.example.com/neerja.mp3",
    voice: "en-IN-NeerjaNeural",
  });
  speechSynthesis = {
    cancel: vi.fn(),
    getVoices: vi.fn(() => [
      { lang: "en-IN", name: "Indian English" },
      { lang: "en-IN", name: "Microsoft Neerja Online (Natural)" },
      { lang: "en-IN", name: "Tara" },
      { lang: "hi-IN", name: "Microsoft Swara Online (Natural)" },
    ]),
    pause: vi.fn(),
    resume: vi.fn(),
    speak: vi.fn((utterance) => {
      lastUtterance = utterance;
    }),
  };

  function MockSpeechSynthesisUtterance(text) {
    this.text = text;
    this.lang = "";
    this.rate = 1;
    this.pitch = 1;
    this.voice = null;
    this.onstart = null;
    this.onend = null;
    this.onerror = null;
  }

  function MockAudio(src) {
    this.src = src;
    this.onended = null;
    this.onerror = null;
    this.onplay = null;
    this.pause = vi.fn();
    this.play = vi.fn(async () => {});
    lastAudio = this;
  }

  vi.stubGlobal("Audio", MockAudio);
  vi.stubGlobal("speechSynthesis", speechSynthesis);
  vi.stubGlobal("SpeechSynthesisUtterance", MockSpeechSynthesisUtterance);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("AvatarNarrator", () => {
  test("renders only for the controlled Grade 6 English POC", () => {
    const { rerender } = render(
      <AvatarNarrator
        grade="Grade 6"
        mode="CBSE"
        subject="English"
        chapter="The Power of Kind Words"
        milestone={milestone}
        milestoneIndex={0}
      />
    );

    expect(screen.getByLabelText("Likha narrated lesson preview")).toBeInTheDocument();
    expect(screen.queryByText("GRADE 6 ENGLISH POC")).not.toBeInTheDocument();

    rerender(
      <AvatarNarrator
        grade="Grade 6"
        mode="CBSE"
        subject="Science"
        chapter="The Power of Kind Words"
        milestone={milestone}
        milestoneIndex={0}
      />
    );

    expect(screen.queryByLabelText("Likha narrated lesson preview")).not.toBeInTheDocument();
  });

  test.each([
    ["Grade 5", "English"],
    ["Grade 5", "Hindi"],
    ["Grade 7", "English"],
    ["Grade 7", "Hindi"],
    ["Grade 8", "English"],
    ["Grade 8", "Hindi"],
  ])("renders Likha for %s %s", (grade, subject) => {
    render(
      <AvatarNarrator
        grade={grade}
        mode="CBSE"
        subject={subject}
        chapter="A Chapter"
        milestone={milestone}
        milestoneIndex={0}
      />
    );

    expect(screen.getByLabelText("Likha narrated lesson preview")).toBeInTheDocument();
  });

  test("plays a first-visit neural welcome in Neerja or Swara without starting lesson narration", async () => {
    const { rerender } = render(
      <AvatarNarrator
        grade="Grade 6"
        mode="CBSE"
        subject="English"
        chapter="The Power of Kind Words"
        milestone={milestone}
        milestoneIndex={0}
      />
    );

    expect(
      screen.getByRole("button", { name: "Tap to hear Likha’s welcome" })
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: "Tap to hear Likha’s welcome" })
    );

    expect(
      screen.getByRole("button", { name: "Getting Likha ready…" })
    ).toBeDisabled();

    await waitFor(() =>
      expect(getChapterNarration).toHaveBeenCalledWith({
        grade: "Grade 6",
        mode: "CBSE",
        subject: "English",
        chapter: "The Power of Kind Words",
        milestoneIndex: 0,
        narrationPath: "welcome",
      })
    );
    expect(lastAudio.src).toBe("https://cdn.example.com/neerja.mp3");
    expect(speechSynthesis.speak).not.toHaveBeenCalled();

    act(() => {
      lastAudio.onplay();
    });
    expect(
      screen.getByRole("button", { name: "Tap to hear Likha’s welcome" })
    ).toBeEnabled();

    act(() => {
      lastAudio.onended();
    });

    expect(
      window.localStorage.getItem(
        "likha-narrator-welcomed:Grade 6:English:The Power of Kind Words"
      )
    ).toBe("true");

    rerender(
      <AvatarNarrator
        grade="Grade 6"
        mode="CBSE"
        subject="Hindi"
        chapter="पाठ एक"
        milestone={milestone}
        milestoneIndex={0}
      />
    );

    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Tap to hear Likha’s welcome" })
      ).toBeInTheDocument()
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Tap to hear Likha’s welcome" })
    );

    await waitFor(() =>
      expect(getChapterNarration).toHaveBeenLastCalledWith({
        grade: "Grade 6",
        mode: "CBSE",
        subject: "Hindi",
        chapter: "पाठ एक",
        milestoneIndex: 0,
        narrationPath: "welcome",
      })
    );
    expect(lastAudio.src).toBe("https://cdn.example.com/neerja.mp3");
    expect(speechSynthesis.speak).not.toHaveBeenCalled();
  });

  test("prefers cached Neerja MP3 playback and supports pause, resume, and stop", async () => {
    render(
      <AvatarNarrator
        grade="Grade 6"
        mode="CBSE"
        subject="English"
        chapter="The Power of Kind Words"
        milestone={milestone}
        milestoneIndex={0}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Play narration" }));

    await waitFor(() => expect(getChapterNarration).toHaveBeenCalledWith({
      grade: "Grade 6",
      mode: "CBSE",
      subject: "English",
      chapter: "The Power of Kind Words",
      milestoneIndex: 0,
      narrationPath: "milestone",
    }));
    expect(lastAudio.src).toBe("https://cdn.example.com/neerja.mp3");
    expect(speechSynthesis.speak).not.toHaveBeenCalled();

    act(() => {
      lastAudio.onplay();
    });

    const pauseButton = await screen.findByRole("button", { name: "Pause narration" });
    expect(pauseButton).toHaveTextContent("Pause");
    expect(screen.getByText("Likha is narrating…")).toBeInTheDocument();

    fireEvent.click(pauseButton);

    expect(lastAudio.pause).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "Resume narration" })).toBeInTheDocument();
    expect(screen.getByText("Narration paused.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Resume narration" }));

    expect(lastAudio.play).toHaveBeenCalledTimes(2);
    act(() => {
      lastAudio.onplay();
    });
    expect(screen.getByRole("button", { name: "Pause narration" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Stop/i }));

    expect(speechSynthesis.cancel).toHaveBeenCalled();
    expect(screen.queryByText(/Free browser narration/i)).not.toBeInTheDocument();
  });

  test("shows a friendly animated preparation state while Neerja audio is loading", async () => {
    let resolveNarration;
    getChapterNarration.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveNarration = resolve;
        })
    );

    render(
      <AvatarNarrator
        grade="Grade 6"
        mode="CBSE"
        subject="English"
        chapter="The Power of Kind Words"
        milestone={milestone}
        milestoneIndex={0}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Play narration" }));

    expect(await screen.findByRole("status")).toHaveTextContent(
      "Getting Likha ready"
    );
    expect(screen.getByRole("status")).toHaveTextContent(
      "Likha is preparing your narration…"
    );
    expect(screen.getByAltText("Likha is preparing your narration"))
      .toBeInTheDocument();
    expect(
      document.querySelector(".likha-narrator-avatar.is-preparing")
    ).toBeInTheDocument();

    await act(async () => {
      resolveNarration({
        success: true,
        audio_url: "https://cdn.example.com/neerja.mp3",
      });
    });
  });

  test("generates only the chapter path selected by the learner", async () => {
    const narrationPaths = [
      {
        id: "milestone-0",
        label: "A Kind Word",
        milestone,
        milestoneIndex: 0,
        narrationPath: "milestone",
      },
      {
        id: "wrap-up",
        label: "Wrap-up",
        milestoneIndex: 0,
        narrationPath: "wrap_up",
        text: "Wrap-up. Kind words build trust.",
      },
    ];

    render(
      <AvatarNarrator
        grade="Grade 6"
        mode="CBSE"
        subject="English"
        chapter="The Power of Kind Words"
        milestone={milestone}
        milestoneIndex={0}
        narrationPaths={narrationPaths}
      />
    );

    fireEvent.change(screen.getByLabelText("Chapter path to narrate"), {
      target: { value: "wrap-up" },
    });

    expect(getChapterNarration).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Play narration" }));

    await waitFor(() =>
      expect(getChapterNarration).toHaveBeenCalledWith({
        grade: "Grade 6",
        mode: "CBSE",
        subject: "English",
        chapter: "The Power of Kind Words",
        milestoneIndex: 0,
        narrationPath: "wrap_up",
      })
    );
  });

  test("keeps playing when the scroll spy changes the active milestone", async () => {
    const nextMilestone = {
      title: "A Second Kind Word",
      blocks: [
        {
          type: "concept",
          title: "Words build trust",
          body_md: "Respectful language helps friendships grow.",
        },
      ],
    };

    const { rerender } = render(
      <AvatarNarrator
        grade="Grade 6"
        mode="CBSE"
        subject="English"
        chapter="The Power of Kind Words"
        milestone={milestone}
        milestoneIndex={0}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Play narration" }));
    await waitFor(() => expect(lastAudio).not.toBeNull());

    act(() => {
      lastAudio.onplay();
    });
    const cancelCallsBeforeScroll = speechSynthesis.cancel.mock.calls.length;

    rerender(
      <AvatarNarrator
        grade="Grade 6"
        mode="CBSE"
        subject="English"
        chapter="The Power of Kind Words"
        milestone={nextMilestone}
        milestoneIndex={1}
      />
    );

    expect(lastAudio.pause).not.toHaveBeenCalled();
    expect(speechSynthesis.cancel).toHaveBeenCalledTimes(cancelCallsBeforeScroll);
    expect(screen.getByRole("button", { name: "Pause narration" })).toBeInTheDocument();
  });

  test("uses Swara's Hindi browser fallback for Grade 6 Hindi", async () => {
    getChapterNarration.mockResolvedValue({ success: false, audio_url: null });

    render(
      <AvatarNarrator
        grade="Grade 6"
        mode="CBSE"
        subject="Hindi"
        chapter="पाठ एक"
        milestone={milestone}
        milestoneIndex={0}
      />
    );

    expect(screen.getByLabelText("Likha narrated lesson preview")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Play narration" }));

    await waitFor(() => expect(speechSynthesis.speak).toHaveBeenCalledTimes(1));
    expect(lastUtterance.lang).toBe("hi-IN");
    expect(lastUtterance.voice.name).toContain("Swara");
    expect(getChapterNarration).toHaveBeenCalledWith({
      grade: "Grade 6",
      mode: "CBSE",
      subject: "Hindi",
      chapter: "पाठ एक",
      milestoneIndex: 0,
      narrationPath: "milestone",
    });
  });

  test("falls back to Tara browser speech when Neerja audio is unavailable", async () => {
    getChapterNarration.mockResolvedValue({ success: false, audio_url: null });

    render(
      <AvatarNarrator
        grade="Grade 6"
        mode="CBSE"
        subject="English"
        chapter="The Power of Kind Words"
        milestone={milestone}
        milestoneIndex={0}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Play narration" }));

    await waitFor(() => expect(speechSynthesis.speak).toHaveBeenCalledTimes(1));
    expect(lastUtterance.voice.name).toContain("Tara");
    expect(lastUtterance.rate).toBe(1.05);
    expect(lastUtterance.pitch).toBe(1.08);
  });

  test("cancels narration when unmounted", () => {
    const { unmount } = render(
      <AvatarNarrator
        grade="Grade 6"
        mode="CBSE"
        subject="English"
        chapter="The Power of Kind Words"
        milestone={milestone}
        milestoneIndex={0}
      />
    );

    unmount();

    expect(speechSynthesis.cancel).toHaveBeenCalled();
  });
});
