import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";

import LikhaVoicePlayer from "../components/likha/LikhaVoicePlayer";
import { speakDoubtAnswer } from "../api/likhaVoiceTutor";

vi.mock("../api/likhaVoiceTutor", () => ({
  speakDoubtAnswer: vi.fn(),
}));

let lastAudio;
let speechSynthesis;
let AudioContextMock;

beforeEach(() => {
  lastAudio = null;
  speakDoubtAnswer.mockReset();
  speakDoubtAnswer.mockResolvedValue({
    success: true,
    audio_url: "https://cdn.example.com/likha-answer.mp3",
    has_more: false,
  });

  speechSynthesis = {
    cancel: vi.fn(),
    getVoices: vi.fn(() => []),
    pause: vi.fn(),
    resume: vi.fn(),
    speak: vi.fn(),
  };

  function MockAudio(src) {
    this.src = src;
    this.paused = false;
    this.ended = false;
    this.playbackRate = 1;
    this.onplay = null;
    this.onended = null;
    this.onerror = null;
    this.pause = vi.fn(() => {
      this.paused = true;
    });
    this.play = vi.fn(async () => {
      this.paused = false;
    });
    lastAudio = this;
  }

  AudioContextMock = vi.fn();

  vi.stubGlobal("Audio", MockAudio);
  vi.stubGlobal("AudioContext", AudioContextMock);
  vi.stubGlobal("speechSynthesis", speechSynthesis);
  vi.stubGlobal(
    "SpeechSynthesisUtterance",
    function MockSpeechSynthesisUtterance() {}
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("LikhaVoicePlayer", () => {
  test("resumes the same neural audio instance without rebuilding Web Audio", async () => {
    render(
      <LikhaVoicePlayer
        historyId="history-1"
        answer="Plants need sunlight to make their food."
        language="en-IN"
      />
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Listen to Likha" })
    );

    await waitFor(() => expect(lastAudio).not.toBeNull());
    const audio = lastAudio;

    act(() => {
      audio.onplay();
    });

    fireEvent.click(screen.getByRole("button", { name: "Pause" }));

    expect(audio.pause).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "Resume" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Resume" }));

    expect(lastAudio).toBe(audio);
    expect(audio.play).toHaveBeenCalledTimes(2);
    expect(speakDoubtAnswer).toHaveBeenCalledTimes(1);
    expect(AudioContextMock).not.toHaveBeenCalled();
  });
});
