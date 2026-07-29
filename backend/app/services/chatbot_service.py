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
            "Today, LikhaPoha AI supports **Class 5 to Class 12 CBSE** students — including "
            "a Grade 11–12 Exam Prep Center for JEE Main, NEET UG, CUET UG, SAT, IELTS, and "
            "TOEFL iBT — with step-wise AI lessons, instant doubt answering, 140,000+ practice "
            "questions, mock tests, and a real-time parent dashboard.\n\n"
            "It is an independent, affordable AI learning companion built for Indian families."
        ),
        "suggestions": ["Which grades are supported?", "How much does it cost?", "How do lessons work?"],
    },

    # ── What is LikhaPoha AI ──────────────────────────────────────────────────
    {
        "keywords": ["what is likhapoha", "what is this", "about this platform",
                     "tell me about", "what does this do", "what is likhap"],
        "answer": (
            "**LikhaPoha AI** is an AI-powered CBSE tutor for Class 5–12 students in India.\n\n"
            "It gives your child:\n"
            "- 📚 Step-wise AI lessons grounded in NCERT textbooks\n"
            "- 🤖 Instant doubt solving from the actual textbook\n"
            "- 📝 140,000+ CBSE practice questions and mock tests\n"
            "- 🎯 A Grade 11–12 Exam Prep Center for JEE, NEET, CUET, SAT, IELTS & TOEFL iBT\n"
            "- 👨‍👩‍👧 Parent dashboard with real-time progress tracking\n\n"
            "Everything works on any phone browser — no app download needed."
        ),
        "suggestions": ["Which grades are supported?", "How much does it cost?", "Is it safe for children?"],
    },

    # ── Grades / Classes ──────────────────────────────────────────────────────
    {
        "keywords": ["which grade", "which class", "what grade", "what class",
                     "class 5", "class 6", "class 7", "class 8", "class 9", "class 10",
                     "class 11", "class 12", "grade 11", "grade 12",
                     "supported grade",
                     "which standard", "std 9", "std 10", "std 11", "std 12", "grades supported",
                     "classes supported", "does it support"],
        "answer": (
            "LikhaPoha AI supports **Class 5 to Class 12** for CBSE.\n\n"
            "**Class 5–10:** Science, Maths, English, Social Science, Hindi\n\n"
            "**Class 11–12:** Choose a stream — Science (PCM), Science (PCB/PCMB), "
            "Commerce, or Arts/Humanities — plus a dedicated **Exam Prep Center** for "
            "JEE Main, NEET UG, CUET UG, SAT, IELTS, and TOEFL iBT.\n\n"
        ),
        "suggestions": ["What subjects are available?", "What is the Exam Prep Center?", "How much does it cost?"],
    },

    # ── Subjects ──────────────────────────────────────────────────────────────
    {
        "keywords": ["which subject", "what subject", "subjects available",
                     "maths", "science", "english", "hindi", "social science",
                     "physics", "chemistry", "biology", "economics", "history",
                     "geography", "political science", "accountancy", "business",
                     "stream", "pcm", "pcb", "commerce", "humanities"],
        "answer": (
            "**Class 5–10 subjects:**\n"
            "Science · Mathematics · English · Social Science · Hindi\n\n"
            "**Class 11–12 subjects** (pick a stream at signup):\n"
            "- **Science (PCM):** Physics, Chemistry, Mathematics, English, Hindi\n"
            "- **Science (PCB / PCMB):** Physics, Chemistry, Biology (+ Maths for PCMB), English, Hindi\n"
            "- **Commerce:** Mathematics, Business Studies, Accountancy, Economics, English, Hindi\n"
            "- **Arts / Humanities:** History, Geography, Political Science, Sociology, English, Hindi\n\n"
            "Every lesson and answer is grounded in the actual NCERT textbook — no generic internet answers."
        ),
        "suggestions": ["Which grades are supported?", "How do lessons work?", "What is the Exam Prep Center?"],
    },

    # ── Exam Prep Center (Grade 11-12) ────────────────────────────────────────
    {
        "keywords": ["exam prep center", "exam prep", "jee", "neet", "cuet",
                     "sat", "ielts", "toefl", "competitive exam", "entrance exam",
                     "jee main", "neet ug", "cuet ug"],
        "answer": (
            "The **Exam Prep Center** (Grade 11 & 12) covers six exams:\n\n"
            "- 📐 **JEE Main** — NTA-style simulator, Physics/Chemistry/Maths question bank\n"
            "- 🔬 **NEET UG** — Physics/Chemistry/Biology with NCERT-exact terminology\n"
            "- 🏛️ **CUET UG** — All streams: Science, Commerce, Humanities\n"
            "- 🎓 **Digital SAT** — Reading & Writing, Math (adaptive-format practice)\n"
            "- 🌐 **IELTS Academic** — Listening, Reading, Writing & Speaking with band-score guidance\n"
            "- 📡 **TOEFL iBT** — Authentic academic passages and lecture-style listening\n\n"
            "Each exam has subject-wise topic-priority cards, a curated MCQ question bank, "
            "and **simulated full-length tests** with a floating countdown timer and question "
            "palette — just like the real exam interface."
        ),
        "suggestions": ["How much does it cost?", "What is the Study Planner?", "Which grades are supported?"],
    },

    # ── Board Papers ──────────────────────────────────────────────────────────
    {
        "keywords": ["board paper", "previous year paper", "past paper", "pyq",
                     "sample paper", "10 years"],
        "answer": (
            "**Board Papers** gives students **10 years of real CBSE board question papers** "
            "with answers, by grade and subject.\n\n"
            "- Read papers question-by-question or attempt them as a **timed 3-hour test**\n"
            "- Get instant scoring plus AI explanations for every answer\n"
            "- Track your attempt history across years to see improvement\n\n"
            "Included in the Premium and Family Premium plans."
        ),
        "suggestions": ["How do mock tests work?", "What is the Study Planner?", "How much does it cost?"],
    },

    # ── Study Planner ──────────────────────────────────────────────────────────
    {
        "keywords": ["study planner", "study plan", "exam countdown", "revision schedule",
                     "study schedule", "daily plan", "day plan"],
        "answer": (
            "The **AI Study Planner** builds a day-by-day revision schedule leading up to "
            "an exam date (CBSE boards, JEE, NEET, CUET, SAT, IELTS, or TOEFL).\n\n"
            "- Live countdown to your exam date with today's recommended task\n"
            "- AI-generated week-by-week plan (revision, practice, formula review, mock tests)\n"
            "- Daily checklist so you can mark tasks done or skipped and stay on track\n\n"
            "Great for students who know their exam date and want a structured lead-up plan."
        ),
        "suggestions": ["What is the Exam Prep Center?", "How do mock tests work?", "How much does it cost?"],
    },

    # ── Exemplar / Formula library ─────────────────────────────────────────────
    {
        "keywords": ["exemplar", "formula sheet", "formula library", "concepts library",
                     "cheat sheet", "quick revision sheet"],
        "answer": (
            "**Exemplar Research & Lessons** — AI-taught lessons based on NCERT Exemplar "
            "problems (the tougher, HOTS-style questions), for extra depth beyond the regular "
            "textbook.\n\n"
            "**Formula & Concepts library** — a searchable, syllabus-aligned sheet of every "
            "formula (Maths, Physics, Chemistry) or key concept (Biology) for your grade, with "
            "worked examples and quick tips.\n\n"
            "Free Tier users get a preview; full access (with worked examples) is part of "
            "Premium and Family Premium."
        ),
        "suggestions": ["How much does it cost?", "How do lessons work?", "What is the Exam Prep Center?"],
    },

    # ── Gamification ─────────────────────────────────────────────────────────
    {
        "keywords": ["badge", "leaderboard", "streak", "xp", "level", "rank",
                     "gamification", "achievement", "points"],
        "answer": (
            "LikhaPoha AI's **gamified dashboard** keeps students motivated:\n\n"
            "- 🏆 **XP, levels, and achievement badges** for completing lessons and tests\n"
            "- 🔥 **Daily streaks** for consistent study habits\n"
            "- 📊 **Class leaderboard** to see how you rank against classmates\n\n"
            "It turns everyday revision into something students actually want to keep up with."
        ),
        "suggestions": ["How do lessons work?", "What does the Parent Dashboard show?", "How much does it cost?"],
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
                     "test", "mcq", "how many questions", "90000", "70000"],
        "answer": (
            "LikhaPoha AI has **140,000+ practice questions** across Grade 5–12 CBSE subjects — "
            "plus dedicated question banks for JEE Main, NEET UG, CUET UG, SAT, IELTS, and TOEFL iBT.\n\n"
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
        "keywords": ["add child", "add a child", "create child", "second child", "child account",
                     "add student", "how many children", "two children", "multiple children",
                     "create student", "student account", "child login"],
        "answer": (
            "**How to add a child on LikhaPoha AI:**\n\n"
            "**Step 1 — Log in as Parent**\n"
            "Go to [likhapoha.in](https://likhapoha.in) and sign in with your parent account.\n\n"
            "**Step 2 — Open the Parent Dashboard**\n"
            "Click **Parent Dashboard** in the left sidebar.\n\n"
            "**Step 3 — Go to Family Learning Center**\n"
            "Scroll to the **Family Hub** section. You will see your linked children and parents.\n\n"
            "**Step 4 — Click + Add Child**\n"
            "Click the **+ Add Child** button (disabled if you already have 2 children — Family plan limit).\n\n"
            "**Step 5 — Fill in the child's details**\n"
            "- **Profile picture** (optional) — choose a preset avatar emoji or upload a photo\n"
            "- **Student Name** (required) — this becomes their username\n"
            "- **Student Email** (optional) — leave blank if your child has no email address; "
            "they can log in with username + password instead\n"
            "- **Child's Class** (required) — select Grade 5 to Grade 10\n"
            "- **Password** (required) — set a password you will share with your child\n\n"
            "**Step 6 — Click Create Student**\n"
            "A confirmation screen will appear with:\n"
            "- Username and password\n"
            "- A **one-click login link** — share this with your child for instant sign-in\n\n"
            "**Step 7 — Share login with your child**\n"
            "Your child can log in at **likhapoha.in** using their username OR email + password.\n\n"
            "💡 **Tips:**\n"
            "- You can add up to **2 children** under one Family account\n"
            "- The child can change their password anytime from their profile\n"
            "- Sit with your child for their first login and give a quick walkthrough"
        ),
        "suggestions": ["What does the Parent Dashboard show?", "How much does the Family plan cost?", "How do lessons work?"],
    },

    # ── Pricing / Cost ────────────────────────────────────────────────────────
    {
        "keywords": ["how much", "price", "cost", "subscription", "plan", "free",
                     "rupee", "₹", "299", "499", "monthly", "pay", "payment", "offer"],
        "answer": (
            "**LikhaPoha AI Plans:**\n\n"
            "| Plan | Price | Best for |\n"
            "|------|-------|----------|\n"
            "| Free Tier | ₹0 forever | Try the platform — 3 subjects, 5 doubts/day, basic mock tests |\n"
            "| Premium | ₹299 / month | One student, full unlimited access |\n"
            "| Family Premium | ₹499 / month | Up to 2 children, full unlimited access |\n"
            "| Premium — 6 Months | ₹1,495 | Save ₹299 vs monthly (1 month free) |\n"
            "| Premium — Annual | ₹2,999 | Save ₹589 vs monthly (2 months free) |\n"
            "| Family Premium — Annual | ₹4,999 | Save ₹989 vs monthly (2 months free) |\n\n"
            "Premium and Family Premium include all CBSE subjects/grades, unlimited AI lessons, "
            "doubts and mock tests, Exemplar Research, the Formula & Concepts library, 10 years "
            "of Board Papers, and — for Grade 11–12 — the full Exam Prep Center.\n\n"
            "💡 Have an offer code? Sign up free, then redeem it from the Subscription page."
        ),
        "suggestions": ["How do I sign up?", "What does the Family plan include?", "Do you have offer codes?"],
    },

    # ── Free trial / offer code ───────────────────────────────────────────────
    {
        "keywords": ["free trial", "offer code", "trial", "free access", "coupon",
                     "discount", "promo", "invite code"],
        "answer": (
            "Every new account starts on the **Free Tier** instantly — no payment or code "
            "needed at signup. It gives you 3 subjects, 5 doubt questions/day, and basic "
            "mock tests (5/day) to try the platform.\n\n"
            "**Have an offer code?** Use it to unlock full Premium access for the code's "
            "validity period:\n"
            "1. Sign up or log in (starts you on Free Tier)\n"
            "2. Go to **Subscription Plans** in the sidebar\n"
            "3. Click **'Have an Offer Code?'**\n"
            "4. Enter your 8-character code for instant access\n\n"
            "Offer codes are shared by teachers, school coordinators, and influencers."
        ),
        "suggestions": ["How much does it cost?", "How do I sign up?", "What's included in the Free Tier?"],
    },

    # ── Sign up / Registration ────────────────────────────────────────────────
    {
        "keywords": ["sign up", "register", "create account", "how to join",
                     "get started", "signup", "enrollment", "how to start"],
        "answer": (
            "**Getting started takes 2 minutes — free, no payment required:**\n\n"
            "1. Go to **likhapoha.in**\n"
            "2. Click **Try for Free** or **Sign Up**\n"
            "3. Choose your role: Student, Parent, or Teacher\n"
            "4. Enter your name, email, and grade (Grade 11–12 students also pick a stream)\n"
            "5. Set your password — you're instantly on the Free Tier\n"
            "6. Upgrade to Premium anytime, or redeem an offer code, from the Subscription page\n\n"
            "No app download needed — works perfectly on any phone browser."
        ),
        "suggestions": ["How much does it cost?", "Do you have offer codes?", "Which grades are supported?"],
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
            "NCERT PDFs for all classes (5–12) are uploaded and indexed in our system."
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
                     "assign student", "school teacher", "teacher features", "teacher tools",
                     "lesson plan creator", "teacher lesson plan"],
        "answer": (
            "**Teachers** get a full AI-powered workspace on LikhaPoha AI with 7 key features:\n\n"
            "📋 **Teacher Dashboard** — View assigned students, class progress, subject performance, and add teacher notes for any student.\n\n"
            "📖 **Lessons** — Browse AI step-wise lessons for any grade (5–10) and subject. Useful for lesson planning and checking content before teaching.\n\n"
            "❓ **Ask Doubt** — Use the AI doubt solver for any chapter — great for checking explanations you'll give in class.\n\n"
            "📝 **Create Test Paper** — Generate CBSE-aligned MCQ and subjective test papers for any grade/subject/chapter in seconds. Download the question paper + answer key.\n\n"
            "🗓️ **Lesson Plan Creator** — Generate a printable, duration-based lesson plan (30–90 min) for any grade (5–10)/subject/chapter. Free tier: 2 plans/day; paid: unlimited.\n\n"
            "📊 **Student Analytics** — See each student's score trend, subject performance (best/average/latest), and recent test activity. Sort by weakest students first.\n\n"
            "🎥 **Learn More** — Access NCERT reference videos, Exemplar problems, and Grammar resources for every subject.\n\n"
            "**For schools:** Contact us at likhapohaai@gmail.com for bulk accounts and a free demo."
        ),
        "suggestions": ["How do I create a test paper?", "How does student analytics work?", "How do I sign up as a teacher?"],
    },

    # ── Test paper creation ───────────────────────────────────────────────────
    {
        "keywords": ["test paper", "create test", "generate test", "exam paper",
                     "question paper", "mcq paper", "subjective questions", "print test",
                     "test paper download", "answer key"],
        "answer": (
            "**Create Test Paper** is an AI-powered teacher tool that generates CBSE-aligned test papers in seconds.\n\n"
            "**How it works:**\n"
            "1. Select **Grade** (5–10), **Subject**, and **Chapter**\n"
            "2. Choose **Question Type**: MCQ Only / Subjective Only / Mixed (60:40 split)\n"
            "3. Set **Difficulty**: Easy / Medium / Hard / Mixed\n"
            "4. Select **Number of Questions**: 5 to 30\n"
            "5. Optionally add School Name and Time Limit\n"
            "6. Click **Generate Test Paper** — AI creates questions using NCERT textbook content\n\n"
            "**Output:**\n"
            "- Live preview with answers highlighted\n"
            "- 🖨️ **Print Question Paper** — CBSE-format with Section A (MCQ) and Section B (Subjective + answer lines)\n"
            "- 🔑 **Print Answer Key** — Teacher-only sheet with correct answers and model answers\n\n"
            "Questions are grounded in NCERT textbook content for accuracy."
        ),
        "suggestions": ["How does student analytics work?", "What grades does it support?", "How do I sign up as a teacher?"],
    },

    # ── Teacher student analytics ─────────────────────────────────────────────
    {
        "keywords": ["student analytics", "student progress", "student performance",
                     "class analytics", "track students", "student scores", "weak students",
                     "class performance", "student report"],
        "answer": (
            "**Student Analytics** lets teachers monitor every assigned student's performance at a glance.\n\n"
            "**Class Overview (top of page):**\n"
            "- Total students, class average score, total tests taken, students needing attention (<50%)\n"
            "- Class subject chart showing average score per subject across all students\n\n"
            "**Per-Student Detail:**\n"
            "- Click any student from the roster to see their full analytics\n"
            "- Score trend line chart (test-by-test history)\n"
            "- Subject performance grouped bars: Best 🟢 / Average 🔵 / Latest 🟡 score\n"
            "- Recent test activity with subject, chapter, date, and score\n\n"
            "**Smart Sorting:**\n"
            "- Name A–Z · Best Score ↓ · Weakest First · Most Active\n"
            "- Filter by grade to focus on one class group\n\n"
            "Student scores are colour-coded: 🟢 Good (≥75%) · 🟡 Average (50–74%) · 🔴 Needs Help (<50%)"
        ),
        "suggestions": ["How do I create a test paper?", "What is the Teacher Dashboard?", "How do I sign up as a teacher?"],
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

    # 3. Current-affairs / political blocker — return redirect without calling LLM
    # This prevents the LLM from revealing its model identity for off-topic questions.
    try:
        from app.services.academic_guardrail_service import is_non_academic_question  # noqa: PLC0415
        if is_non_academic_question(question):
            return {
                "answer": (
                    "📚 I'm LikhaPoha AI's assistant, focused on helping you "
                    "with our CBSE tutoring platform.\n\n"
                    "For questions about current events or politics, please check "
                    "a news source. I'm here to help with questions about our "
                    "lessons, subjects, pricing, or how to get started!"
                ),
                "source": "faq",
                "suggestions": DEFAULT_SUGGESTIONS,
            }
    except Exception:
        pass

    # 3b. Check admin-approved Q&A from chatbot_approved_qa table
    try:
        from app.services.auth_service import admin_client as _sb  # noqa: PLC0415
        approved = _sb.table("chatbot_approved_qa").select("question,answer").eq("status","active").execute()
        for row in (approved.data or []):
            kw_norm = _normalise(row.get("question",""))
            # Simple word overlap matching
            q_words = set(q_norm.split())
            kw_words = set(kw_norm.split())
            overlap = len(q_words & kw_words)
            if overlap >= 2 and len(kw_words) > 0:
                if overlap / len(kw_words) >= 0.6:
                    return {
                        "answer": row["answer"],
                        "source": "faq",
                        "suggestions": DEFAULT_SUGGESTIONS,
                    }
    except Exception:
        pass

    # 4. Default: honest scope statement — log this unanswered question for admin review
    try:
        from app.services.auth_service import admin_client as _sb2  # noqa: PLC0415
        _sb2.table("unanswered_questions").insert({
            "question": question[:500],
            "source": "chatbot",
            "status": "pending",
        }).execute()
    except Exception:
        pass  # Never block the response

    return {
        "answer": (
            "I'm designed to answer questions about the **LikhaPoha AI platform** only.\n\n"
            "For anything else, please email **likhapohaai@gmail.com** and we'll help you."
        ),
        "source": "faq",
        "suggestions": DEFAULT_SUGGESTIONS,
    }
