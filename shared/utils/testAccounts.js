const ALL_ACCESS_TEST_USERNAMES = new Set(["akshita.teststudent"]);

export function normalizeUsername(value) {
  return String(value || "").trim().toLowerCase();
}

export function isAllAccessTestUser(user) {
  return ALL_ACCESS_TEST_USERNAMES.has(normalizeUsername(user?.username));
}
