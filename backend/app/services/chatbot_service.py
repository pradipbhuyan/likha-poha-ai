"""
Chatbot Service — LikhaPoha AI Platform FAQ
============================================
Answers visitor/user questions about the platform using a keyword-matched
FAQ knowledge base (zero token cost) or LLM fallback with platform context.

To add new FAQs: add entries to PLATFORM_FAQ below.
Each entry has:
  - keywords: list of lowercase trigger words/phrases
  - answer: the response text (Markdown supported)
  - suggestions: follow-up quick-reply chips to show
"""
from __future__ import annotations
import re

# ── Platform FAQ Knowledge Base ────────────────────────────────────────────────

PLATFORM_FAQ: list[dict] = [

    # ── Creator / Founder ─────────────────────────────────────────────────────
    {
        "keywords": ["who created", "who made", "who built", "who is the creator",
                     "who is the founder", "founder", "creator", "who started",
                     "who is behind", "who owns", "pradip", "akshita", "company",
                     "who developed", "when was it created", "history of likhapoha",
                     "mission", "why was it created", "origin"],
        "answer": (
            "**LikhaPoha AI** was created by a parent-engineer in Bangalore to solve "
            "a real problem: good CBSE tutoring is expensive, generic YouTube videos "
            "don't follow the syllabus, and parents have no visibility into what their "
            "child is actually learning.\n\n"
            "The platform was built on a simple idea — *what if a student had a patient "
            "AI teacher available any time, one that actually uses their NCERT textbook?*\n\n"
            "Today, LikhaPoha AI supports Class 5 to Class 10 CBSE students across all "
            "core subjects with step-wise AI lessons, instant doubt answering, 70,000+ "
            "practice questions, mock tests, and a real-time parent dashboard.\n\n"
            "It is an independent, affordable AI learning companion built for Indian families."
        ),
        "suggestions": ["Which grades are supported?", "How much does it cost?", "How do lessons work?"],
    },

    # ── What is LikhaPoha AI ──────────────────────────────────────────────────
    {
        "keywords": ["what is likhapoha", "what is this", "about this platform",
                     "tell me about", "what does this do", "what is likhap"],
        "answer": (
            "**LikhaPoha AI** is an AI-powered CBSE tutor for Class 5–10 students in India.\n\n"
            "It gives your child:\n"
            "- 📚 Step-wise AI lessons grounded in NCERT textbooks\n"
            "- 🤖 Instant doubt solving from the actual textbook\n"
            "- 📝 70,000+ CBSE practice questions and mock tests\n"
            "- 👨‍👩‍👧 Parent dashboard with real-time progress tracking\n\n"
            "Everything works on any phone browser — no app download needed."
        ),
        "suggestions": ["Which grades are supported?", "How much does it cost?", "Is it safe for children?"],
    },

    # ── Grades / Classes ──────────────────────────────────────────────────────
    {
        "keywords": ["which grade", "which class", "what grade", "what class",
                     "class 5", "class 6", "class 7", "class 8", "class 9", "class 10",
                     "supported grade",
                     "which standard", "std 9", "std 10", "grades supported",
                     "classes supported", "does it support"],
        "answer": (
            "LikhaPoha AI supports **Class 5 to Class 10** for CBSE.\n\n"
            "**Class 5–10:** Science, Maths, English, Social Science, Hindi\n\n"
        ),
        "suggestions": ["What subjects are available?", "How do lessons work?", "How much does it cost?"],
    },

    # ── Subjects ──────────────────────────────────────────────────────────────
    {
        "keywords": ["which subject", "what subject", "subjects available",
                     "maths", "science", "english", "hindi", "social science",
                     "physics", "chemistry", "biology", "economics", "history",
                     "geography", "political science", "accountancy", "business"],
        "answer": (
            "**Class 5–10 subjects:**\n"
            "Science · Mathematics · English · Social Science · Hindi\n\n"
            "no generic internet answers."
        ),
        "suggestions": ["Which grades are supported?", "How do lessons work?", "What is RAG?"],
    },

    # ── How lessons work ──────────────────────────────────────────────────────
    {
        "keywords": ["how does lesson", "how do lesson", "how lesson work",
                     "step lesson", "lesson step", "how to learn", "how to study",
                     "start lesson", "generate lesson", "ai lesson", "what is a lesson"],
        "answer": (
            "The AI breaks each chapter into **4–6 short, focused steps**:\n\n"
            "1. **What is this topic?** — Simple introduction\n"
            "2. **Deep explanation** — With real-world examples\n"
            "3. **Solved problems** — Step-by-step worked examples\n"
            "4. **Exam-style questions** — Practice at exam level\n"
            "5. **Quick revision** — Key points to remember\n"
            "6. **Exam tips** *(Class 10–12 only)*\n\n"
            "The AI studies your child's actual NCERT textbook first, then teaches "
            "it back in clear, simple language.\n\n"
            "Students can also 🔊 **listen** to the lesson aloud or ask the AI "
            "follow-up questions mid-lesson."
        ),
        "suggestions": ["How does doubt solving work?", "How does the parent dashboard work?", "How do mock tests work?"],
    },

    # ── Doubt solving ─────────────────────────────────────────────────────────
    {
        "keywords": ["doubt", "question solving", "ask question", "solve doubt",
                     "instant answer", "how doubt", "ai tutor answer"],
        "answer": (
            "The **Instant Doubt Solving** feature answers any chapter question in seconds.\n\n"
            "The AI reads your child's actual NCERT textbook and explains the answer "
            "in simple language — like a patient tutor sitting next to them.\n\n"
            "Students can ask:\n"
            "- 'What is photosynthesis?'\n"
            "- 'Explain Newton's second law with an example'\n"
            "- 'I don't understand this chapter — help me'\n\n"
            "The AI responds instantly, with diagrams, examples, and step-by-step breakdowns."
        ),
        "suggestions": ["Is the AI safe for children?", "What is the parent dashboard?", "How much does it cost?"],
    },

    # ── Mock tests ────────────────────────────────────────────────────────────
    {
        "keywords": ["mock test", "practice test", "question bank", "practice question",
                     "test", "exam prep", "mcq", "how many questions", "70000"],
        "answer": (
            "LikhaPoha AI has **70,000+ CBSE practice questions** across all grades and subjects.\n\n"
            "**Mock Test Studio lets students:**\n"
            "- Choose subject, chapter, difficulty (Easy / Medium / Hard)\n"
            "- Set number of questions and time limit\n"
            "- Toggle negative marking (for Board exam simulation)\n"
            "- Get instant scoring with detailed explanations\n\n"
            "Tests are chapter-specific so students can focus on exactly what they need to revise."
        ),
        "suggestions": ["How do lessons work?", "What is the parent dashboard?", "How much does it cost?"],
    },

    # ── Parent dashboard ──────────────────────────────────────────────────────
    {
        "keywords": ["parent dashboard", "parent", "track child", "child progress",
                     "weak area", "progress tracking", "parent view", "how does parent"],
        "answer": (
            "The **Parent Dashboard** is a real-time window into your child's learning:\n\n"
            "- 📊 **Score trend graphs** — See if scores are improving over time\n"
            "- ⚠️ **Weak area alerts** — Auto-notified when a chapter needs revision\n"
            "- 📚 **Subject performance** — Average scores per subject\n"
            "- 🕘 **Recent test history** — Last 5 mock tests with scores\n"
            "- 👨‍👩‍👧 **Family hub** — Manage up to 2 children from one account\n"
            "- 🔑 **Multi-parent access** — Both parents can view the same dashboard\n\n"
            "You always know what your child studied today — without asking them."
        ),
        "suggestions": ["How do I add a child?", "How much does it cost?", "Is it safe for children?"],
    },

    # ── Add child ─────────────────────────────────────────────────────────────
    {
        "keywords": ["add child", "create child", "second child", "child account",
                     "add student", "how many children", "two children", "multiple children"],
        "answer": (
            "**Adding a child is easy:**\n\n"
            "1. Log in as a Parent\n"
            "2. Go to **Parent Dashboard → Family Hub**\n"
            "3. Click **+ Add Child**\n"
            "4. Enter your child's name, email (optional), class, and set a password\n"
            "5. Share the login details with your child\n\n"
            "The **Family plan** supports up to **2 children** under one account.\n\n"
            "Your child can log in at **likhapoha.in** using their username or email."
        ),
        "suggestions": ["What is the parent dashboard?", "How much does it cost?", "How do lessons work?"],
    },

    # ── Pricing / Cost ────────────────────────────────────────────────────────
    {
        "keywords": ["how much", "price", "cost", "subscription", "plan", "free",
                     "rupee", "₹", "299", "499", "monthly", "pay", "payment", "offer"],
        "answer": (
            "**LikhaPoha AI Plans:**\n\n"
            "| Plan | Price | Best for |\n"
            "|------|-------|----------|\n"
            "| Try It Out | ₹99 / 8 days | First-time trial |\n"
            "| Standard | ₹299 / month | One student |\n"
            "| Family | ₹499 / month | Up to 2 children |\n\n"
            "All plans include **all subjects, all grades, unlimited doubt solving, "
            "mock tests, and parent dashboard**.\n\n"
            "💡 Have an offer code? Use it during signup to get free trial access."
        ),
        "suggestions": ["How do I sign up?", "What does the Family plan include?", "Is there a free trial?"],
    },

    # ── Free trial / offer code ───────────────────────────────────────────────
    {
        "keywords": ["free trial", "offer code", "trial", "free access", "coupon",
                     "discount", "promo", "invite code"],
        "answer": (
            "Yes! LikhaPoha AI offers **free trial access via offer codes**.\n\n"
            "**How to use an offer code:**\n"
            "1. Go to **likhapoha.in → Sign Up**\n"
            "2. Click **'I Have an Offer Code'**\n"
            "3. Enter your 8-character code\n"
            "4. Set your password and get instant access\n\n"
            "Offer codes are shared by teachers, school coordinators, and influencers.\n\n"
            "If you don't have a code, you can start with the **₹99 / 8-day trial plan**."
        ),
        "suggestions": ["How much does it cost?", "How do I sign up?", "What is included in the trial?"],
    },

    # ── Sign up / Registration ────────────────────────────────────────────────
    {
        "keywords": ["sign up", "register", "create account", "how to join",
                     "get started", "signup", "enrollment", "how to start"],
        "answer": (
            "**Getting started takes 2 minutes:**\n\n"
            "1. Go to **likhapoha.in**\n"
            "2. Click **Try Today** or **Sign Up**\n"
            "3. Choose your role: Student, Parent, or Teacher\n"
            "4. Enter your name, email, and grade\n"
            "5. Choose a plan (or use an offer code for free access)\n"
            "6. Set your password and start learning!\n\n"
            "No app download needed — works perfectly on any phone browser."
        ),
        "suggestions": ["How much does it cost?", "Do you have a free trial?", "Which grades are supported?"],
    },

    # ── Safety / Guardrail ────────────────────────────────────────────────────
    {
        "keywords": ["is it safe", "child safe", "safe for children",
                     "inappropriate", "guardrail", "off topic",
                     "block", "politics", "filter", "age appropriate"],
        "answer": (
            "Yes — LikhaPoha AI is completely **safe for children**.\n\n"
            "The AI only talks about CBSE school subjects. It automatically detects "
            "and blocks questions about politics, news, entertainment, or anything "
            "outside schoolwork — and politely redirects your child back to their studies.\n\n"
            "**What parents love:**\n"
            "- No social media, no distractions — pure academics\n"
            "- Every conversation is educational and age-appropriate\n"
            "- The AI never discusses current events, celebrities, or politics\n\n"
            "You can trust your child to use it independently."
        ),
        "suggestions": ["What is the parent dashboard?", "How do lessons work?", "How much does it cost?"],
    },

    # ── Mobile / App ──────────────────────────────────────────────────────────
    {
        "keywords": ["mobile", "app", "phone", "android", "ios", "download app",
                     "play store", "app store", "works on phone", "mobile app"],
        "answer": (
            "LikhaPoha AI is a **mobile-first progressive web app** — it works "
            "perfectly on any phone browser.\n\n"
            "**No app download needed!**\n\n"
            "To get an app-like experience on your phone:\n"
            "1. Open **likhapoha.in** in Chrome (Android) or Safari (iPhone)\n"
            "2. Tap the **Share** button → **Add to Home Screen**\n"
            "3. It will appear as an icon on your home screen like a regular app\n\n"
            "Works on Android, iPhone, iPad, laptop, and desktop — any device."
        ),
        "suggestions": ["How do I sign up?", "Which grades are supported?", "How much does it cost?"],
    },

    # ── NCERT / Textbook alignment ────────────────────────────────────────────
    {
        "keywords": ["ncert", "textbook", "cbse syllabus", "textbook based",
                     "is it ncert", "curriculum aligned", "syllabus"],
        "answer": (
            "**Yes — 100% NCERT aligned.**\n\n"
            "Every lesson and doubt answer is grounded in the **actual uploaded NCERT "
            "textbook** using RAG (Retrieval-Augmented Generation) technology.\n\n"
            "This means:\n"
            "- The AI reads your child's actual textbook chapter before explaining\n"
            "- Answers match what's in the NCERT book — not generic internet content\n"
            "- Practice questions follow the CBSE exam pattern\n\n"
            "NCERT PDFs for all classes (5–10) are uploaded and indexed in our system."
        ),
        "suggestions": ["How do lessons work?", "Which grades are supported?", "How much does it cost?"],
    },

    # ── Password / Login ───────────────────────────────────────────────────────
    {
        "keywords": ["forgot password", "reset password", "change password",
                     "login problem", "can't login", "cant login", "password"],
        "answer": (
            "**Forgot your password?**\n\n"
            "1. Go to **likhapoha.in**\n"
            "2. Click **Login** → **Forgot Password?**\n"
            "3. Enter your email address\n"
            "4. Check your inbox for a reset link\n\n"
            "**Already logged in?** Go to your Profile (top-right) → Change Password.\n\n"
            "If you signed up with an offer code and never set a password, "
            "check your email for the original **Set Password** link."
        ),
        "suggestions": ["How do I sign up?", "How much does it cost?", "How do I contact support?"],
    },

    # ── Contact / Support ─────────────────────────────────────────────────────
    {
        "keywords": ["contact", "support", "help", "email", "reach", "talk to",
                     "customer care", "whatsapp", "phone number"],
        "answer": (
            "Need help? Reach us at:\n\n"
            "📧 **Email:** likhapohaai@gmail.com\n\n"
            "We typically respond within a few hours. For urgent issues, "
            "email with your registered email address and describe your problem.\n\n"
            "For billing issues, please include your payment ID (from Razorpay)."
        ),
        "suggestions": ["How do I sign up?", "How much does it cost?", "How do I reset my password?"],
    },

    # ── Teacher dashboard ─────────────────────────────────────────────────────
    {
        "keywords": ["teacher", "teacher dashboard", "teacher account",
                     "assign student", "school teacher"],
        "answer": (
            "**Teachers** get a dedicated dashboard on LikhaPoha AI:\n\n"
            "- View progress of all assigned students\n"
            "- See test scores, subject performance, and weak areas\n"
            "- Track daily study activity\n\n"
            "**For schools:** Contact us at likhapohaai@gmail.com for bulk school accounts "
            "and a free demo. We offer customised pricing for schools with 50+ students."
        ),
        "suggestions": ["How do I contact support?", "How much does it cost?", "How do I sign up?"],
    },

    # ── Refund ────────────────────────────────────────────────────────────────
    {
        "keywords": ["refund", "cancel", "money back", "cancellation", "return"],
        "answer": (
            "For refund and cancellation policy, please visit our **Refund Policy** page "
            "at the bottom of the website.\n\n"
            "To request a refund, email **likhapohaai@gmail.com** with your "
            "payment ID and reason within 7 days of purchase.\n\n"
            "Refunds are processed within 5–7 business days to your original payment method."
        ),
        "suggestions": ["How do I contact support?", "How much does it cost?", "How do I sign up?"],
    },
]

# ── Default fallback suggestions ───────────────────────────────────────────────
DEFAULT_SUGGESTIONS = [
    "Which grades are supported?",
    "How much does it cost?",
    "How do lessons work?",
]

# ── Greeting responses ─────────────────────────────────────────────────────────
# Use full-word patterns to avoid "hi" matching inside "which", "child", etc.
GREETINGS = {"hello", "hey", "hii", "namaste", "helo",
             "good morning", "good evening", "good afternoon", "how are you"}
# Short single-word greetings need exact-word matching
GREETING_WORDS = {"hi", "yo", "sup"}

GREETING_RESPONSE = (
    "Hi! 👋 I'm LikhaPoha AI's assistant. I can help you learn about our "
    "CBSE AI tutoring platform.\n\n"
    "What would you like to know?"
)


def _normalise(text: str) -> str:
    """Lowercase, remove punctuation, collapse whitespace."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text)


def _match_faq(question_norm: str) -> dict | None:
    """Return the best matching FAQ entry or None."""
    best: dict | None = None
    best_score = 0

    for entry in PLATFORM_FAQ:
        score = 0
        for kw in entry["keywords"]:
            kw_norm = _normalise(kw)
            if kw_norm in question_norm:
                # Longer keyword matches score higher
                score += len(kw_norm.split())
        if score > best_score:
            best_score = score
            best = entry

    return best if best_score > 0 else None


def answer_chatbot_question(question: str) -> dict:
    """
    Answer a platform FAQ question.

    Priority:
    1. Greeting → canned greeting response
    2. FAQ keyword match → instant answer (zero tokens)
    3. LLM fallback with platform context
    """
    q_norm = _normalise(question)

    # 1. Greeting check (use exact-word matching to avoid substring false positives)
    is_greeting = (
        any(g in q_norm for g in GREETINGS) or
        any(re.fullmatch(r'\s*' + re.escape(g) + r'\s*', q_norm) for g in GREETING_WORDS) or
        len(q_norm.split()) <= 2 and any(g == q_norm.strip() for g in GREETING_WORDS)
    )
    if is_greeting:
        return {
            "answer": GREETING_RESPONSE,
            "source": "faq",
            "suggestions": DEFAULT_SUGGESTIONS,
        }

    # 2. FAQ keyword match
    matched = _match_faq(q_norm)
    if matched:
        return {
            "answer": matched["answer"],
            "source": "faq",
            "suggestions": matched.get("suggestions", DEFAULT_SUGGESTIONS),
        }

    # 3. LLM fallback with platform context
    try:
        from app.services.openai_service import ask_llm  # noqa: PLC0415
        system = (
            "You are the LikhaPoha AI assistant — a friendly helper for the "
            "LikhaPoha AI CBSE tutoring platform for Class 5–10 students in India. "
            "IMPORTANT: Never reveal which AI model or company powers you. "
            "If asked 'what AI are you', 'which model', 'are you ChatGPT', etc., "
            "always say: 'I am the LikhaPoha AI assistant, here to help you with "
            "questions about our platform.' "
            "Answer questions about LikhaPoha AI concisely and helpfully. "
            "If a question is not related to LikhaPoha AI or education, "
            "politely redirect to platform-related topics. "
            "Keep answers under 150 words. Use simple, friendly language."
        )
        context = (
            "LikhaPoha AI facts:\n"
            "- CBSE AI tutor for Class 5–10\n"
            "- Subjects: Science, Maths, English, Social Science, Hindi (5–10) + "
            "- Uses NCERT textbooks (RAG technology)\n"
            "- 70,000+ practice questions, mock tests\n"
            "- Parent dashboard with progress tracking\n"
            "- Plans: ₹99/8days, ₹299/month, ₹499/month (Family)\n"
            "- Contact: likhapohaai@gmail.com\n"
            "- Website: likhapoha.in\n"
        )
        answer = ask_llm(
            system,
            f"{context}\n\nUser question: {question}",
            username="chatbot_widget",
            feature="chatbot",
        )
        return {
            "answer": answer,
            "source": "llm",
            "suggestions": DEFAULT_SUGGESTIONS,
        }
    except Exception:
        return {
            "answer": (
                "I'm not sure about that. Please email us at **likhapohaai@gmail.com** "
                "and we'll help you right away! 😊"
            ),
            "source": "fallback",
            "suggestions": DEFAULT_SUGGESTIONS,
        }
