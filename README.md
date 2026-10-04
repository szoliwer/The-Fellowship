# The Fellowship

**An AI-native discovery network that matches people on what they're actually thinking about, not on static profiles.**

Most networking tools match people on job titles, schools, and self-written bios. Those go stale fast and don't say much about what someone is working through right now. The Fellowship starts from a better signal: the conversations people already have with AI assistants.

Users choose to import their LLM chat histories (ChatGPT, Claude, Gemini, and so on). We filter out the noise, pull out the ideas and interests underneath, and rank them. Then we match users whose ideas are **similar** (working on the same problem) or **complementary** (one person has what the other needs). Each match comes with a short warm intro explaining *why* the two people should talk, so the first conversation starts in the right place.

> Built live at a hackathon by a team of four.

---

## How it works: the 7-step pipeline

| # | Step | What it does | Folder |
|---|------|--------------|--------|
| 0 | **User Registration** | Sign up, give consent, set basic preferences (what kinds of matches they want). | [`0 - User Registration`](./0%20-%20User%20Registration/) |
| 1 | **Data Collection** | User uploads chat exports from the LLM tools they choose. We read them into one common format. | [`1 - Data Collection`](./1%20-%20Data%20Collection/) |
| 2 | **Noise Filter** | Throw out the chatter that says nothing about the person (debugging a typo, "write me an email", recipes) and remove sensitive personal details. | [`2 - Noise Filter`](./2%20-%20Noise%20Filter/) |
| 3 | **Idea Generation** | Turn the remaining conversations into a short list of the user's real ideas, questions, interests and skills. | [`3 - Idea Generation`](./3%20-%20Idea%20Generation/) |
| 4 | **Idea Ranking** | Score each idea for how central and current it is to this person (how often, how recently, how deeply they engage with it). | [`4 - Idea Ranking`](./4%20-%20Idea%20Ranking/) |
| 5 | **Match Generation** | Compare users' ranked ideas and score pairs on similarity and complementarity. Produce a ranked list of suggested matches. | [`5 - Match Generation`](./5%20-%20Match%20Generation/) |
| 6 | **Matching Interface** | Show a user their suggested matches. They accept or pass, and on a mutual accept both see a warm intro explaining why they matched. | [`6 - Matching Interface`](./6%20-%20Matching%20Interface/) |

```
 Register ─► Upload chats ─► Filter noise ─► Extract ideas ─► Rank ideas ─► Match people ─► Accept + warm intro
   (0)           (1)             (2)             (3)              (4)             (5)               (6)
```

Each step's output becomes the next step's input. Every step folder has its own `README.md` that describes what goes in, what comes out, and keeps a running log of **decisions**, **progress**, and **code fixes** for that step.

---

## Repository layout

```
The Fellowship/
├── README.md                  ← you are here: project overview
├── CLAUDE.md                  ← the "harness": context + rules for any AI assistant working in this repo
├── .gitignore                 ← keeps secrets and real user data out of GitHub
├── app.py                     ← the shared app: joins the steps' screens (see "Run the app")
├── pipeline/                  ← glue between steps + labelled placeholders (see pipeline/README.md)
├── requirements.txt           ← what the shared app needs installed
├── .env.example               ← template for .env (your Anthropic API key; .env is git-ignored)
├── .streamlit/config.toml     ← app settings: this laptop only, no usage statistics
├── data/                      ← (git-ignored, on your laptop only) accounts, uploads, pipeline files
├── docs/
│   ├── PROGRESS.md            ← team status board: who's doing what, what's done
│   ├── DECISIONS.md           ← project-wide decisions (stack, data format, privacy, etc.)
│   └── HOW_WE_WORK.md         ← GitHub Desktop workflow for the team
├── 0 - User Registration/
│   └── README.md              ← step spec + decisions / progress / fixes log
├── 1 - Data Collection/
├── 2 - Noise Filter/
├── 3 - Idea Generation/
├── 4 - Idea Ranking/
├── 5 - Match Generation/
└── 6 - Matching Interface/
```

---

## Privacy principles

People's AI chats are personal. These rules hold even for the hackathon demo:

1. **Opt-in only.** Users choose which exports to upload. Nothing is pulled automatically.
2. **Raw chats never leave the pipeline.** Other users only ever see high-level ideas and the warm intro, never chat text.
3. **Mutual consent to connect.** Contact details are shared only after both people accept.
4. **No real user data in GitHub.** Use sample or synthetic chats for development. Real exports go in `data/`, which is git-ignored.

---

## Getting started (team)

1. Open **GitHub Desktop** → make sure *The-Fellowship* is the current repository → click **Fetch origin** / **Pull**.
2. Make sure you're on **`main`**. The whole team works there. Always pull before you start.
3. Read [`CLAUDE.md`](./CLAUDE.md) (the ground rules) and [`docs/PROGRESS.md`](./docs/PROGRESS.md) (who's on what).
4. Work inside the folder for your step. Log what you did in that step's `README.md`.
5. When you're ready to save to GitHub, follow [`docs/HOW_WE_WORK.md`](./docs/HOW_WE_WORK.md).

## Run the app

In Terminal, from the repo folder (GitHub Desktop: *Repository → Open in Terminal*):

1. First time only: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`. For privacy screening (Step 2), also copy `.env.example` to `.env` and paste your Anthropic API key into it.
2. Every time: `.venv/bin/streamlit run app.py`, then open http://localhost:8501

The menu along the top takes you through the whole flow, one page per step, and a green **Next** button in the bottom-right corner of each page takes you to the next step:

| Page | Step | What you do |
|---|---|---|
| (landing page) | 0 | **Create your account**, **Log in**, or **Try a demo** (each opens a pop-up) |
| Import | 1 | upload a ChatGPT/Claude export, .md/.txt, or load the **Demo history**; remove chats you don't want |
| Privacy | 2 | **Screen** your chats: personal parts removed or chats held back |
| Ideas | 3 | **Find my ideas** from your screened chats |
| Review | 4 | untick anything you don't want used, then **Use … for matching** |
| Matches | 5 | **Find matches** for everyone who approved ideas |
| Discover | 6 | **Connect** or **Pass**; when both say yes, both see a warm introduction |
| Messages | 6 | chat with people where you both said yes (the warm intro is pinned at the top) |
| (your username) | 0 | your account: what others see, log out |

**Test the whole flow** with the two demo researchers, in two browser windows (one normal, one private):
`researcher_014` and `cellbio_027` each go through Import → Privacy → Ideas → Review (Demo history → Screen → Find my ideas → Use for matching), then either one runs **Matches**, and both open **Discover** and press **Connect**, then **Message** each other (two browser windows, one per researcher). Steps 2, 3 and 5 call Claude: one full run costs well under $1 (repeat runs on unchanged chats are cached).

Placeholders (marked in the code and docs, not on screen, so the demo looks finished): the ranking between Steps 3 and 4 (`pipeline/ranking.py`) and the Discover and Messages pages (`pipeline/discover_page.py`, `pipeline/messages_page.py`, until Step 6's own pages exist). Everything you create is stored in `data/` on your laptop only.

## Team

| Name | Role / Steps owned |
|------|--------------------|
| Oliver | _TBD_ |
| _Teammate 2_ | _TBD_ |
| _Teammate 3_ | _TBD_ |
| _Teammate 4_ | _TBD_ |
