import API_BASE_URL from "./client";


export async function generateEducationalImage(prompt, username) {
  const response = await fetch(
    `${API_BASE_URL}/api/images/generate`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        prompt,
        username,
      }),
    }
  );

  if (!response.ok) {
    throw new Error("Image generation failed");
  }

  return response.json();
}