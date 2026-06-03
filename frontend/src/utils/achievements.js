export function calculateAchievements({
  testHistory = [],
  progress = null,
}) {
  /** Build dashboard achievement cards from test history and chapter progress. */
  const achievements = [];

  achievements.push({
    id: "active-learner",
    icon: "📚",
    title: "Active Learner",
    description: "Started your AI learning journey.",
    unlocked: true,
  });

  achievements.push({
    id: "ai-explorer",
    icon: "🤖",
    title: "AI Explorer",
    description: "Used AI tutor tools for learning support.",
    unlocked: true,
  });

  const mockTestsTaken = testHistory.length;

  achievements.push({
    id: "mock-test-warrior",
    icon: "🧪",
    title: "Mock Test Warrior",
    description: "Complete at least 1 mock test.",
    unlocked: mockTestsTaken >= 1,
  });

  const bestScore = testHistory.length
    ? Math.max(...testHistory.map((t) => Number(t.percentage || 0)))
    : 0;

  achievements.push({
    id: "olympiad-ready",
    icon: "🌟",
    title: "Olympiad Ready",
    description: "Score 90% or above in a test.",
    unlocked: bestScore >= 90,
  });

  achievements.push({
    id: "consistent-learner",
    icon: "🔥",
    title: "Consistent Learner",
    description: "Keep learning across multiple chapters.",
    unlocked: Boolean(progress?.completed),
  });

  return achievements;
}
