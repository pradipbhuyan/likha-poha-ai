import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import PlatformChat from "../components/PlatformChat";
import { getChatSettings, getChatContacts, getChatRooms } from "../api/platformChat";

vi.mock("../api/platformChat", () => ({
  getChatSettings: vi.fn(),
  getChatContacts: vi.fn(),
  getChatRooms: vi.fn(),
  getOrCreateRoom: vi.fn(),
  getRoomMessages: vi.fn(),
  sendMessage: vi.fn(),
  markRoomRead: vi.fn(),
  uploadChatFile: vi.fn(),
  subscribeToRoom: vi.fn(() => () => {}),
}));

const STUDENT_USER = { id: "student-1", role: "student", username: "ghagu" };

async function openContactsView() {
  render(<PlatformChat user={STUDENT_USER} />);
  const launcher = await screen.findByTitle("Messages");
  fireEvent.click(launcher);
  const newButton = await screen.findByText("+ New");
  fireEvent.click(newButton);
}

describe("PlatformChat — contacts loading", () => {
  beforeEach(() => {
    getChatSettings.mockResolvedValue({ success: true, can_use_chat: true, allow_files: false, allow_voice: false });
    getChatRooms.mockResolvedValue({ success: true, rooms: [] });
  });

  test(
    "REGRESSION: never gets stuck on 'Loading contacts...' when the fetch " +
    "succeeds with zero contacts (e.g. a student with no assigned teacher " +
    "or linked parent yet)",
    async () => {
      getChatContacts.mockResolvedValue({ success: true, contacts: [] });

      await openContactsView();

      await waitFor(() => {
        expect(screen.getByText(/no contacts available yet/i)).toBeInTheDocument();
      });
      expect(screen.queryByText(/loading contacts/i)).not.toBeInTheDocument();
    }
  );

  test(
    "REGRESSION: never gets stuck on 'Loading contacts...' when the fetch " +
    "rejects (network error, 401, etc.)",
    async () => {
      getChatContacts.mockRejectedValue(new Error("Network error"));

      await openContactsView();

      await waitFor(() => {
        expect(screen.queryByText(/loading contacts/i)).not.toBeInTheDocument();
      });
      // Surfaces as an error banner rather than an infinite spinner.
      expect(screen.getByText(/could not load contacts/i)).toBeInTheDocument();
    }
  );

  test("shows the contact list once contacts load successfully", async () => {
    getChatContacts.mockResolvedValue({
      success: true,
      contacts: [{ id: "teacher-1", username: "Mrs. Sharma", role: "teacher", grade: null }],
    });

    await openContactsView();

    await waitFor(() => {
      expect(screen.getByText("Mrs. Sharma")).toBeInTheDocument();
    });
    expect(screen.queryByText(/loading contacts/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/no contacts available yet/i)).not.toBeInTheDocument();
  });
});
