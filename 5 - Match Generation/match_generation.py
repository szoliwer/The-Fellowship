#!/usr/bin/env python3
"""
Step 5 - Match Generation  (The Fellowship)

IN : every user's ranked research ideas (Step 4 output, JSON).
OUT: suggested pairs of researchers, each labelled "similar", "complementary"
     or "both", with a score, a reason and a warm intro for each side (JSON).

How it works - a 4-stage funnel (cheap math first, careful AI judgement last):

  1. PROFILE  For each person, list what they can OFFER a collaborator and what
              they NEED. One Claude call per person (keyword fallback offline).
  2. SCORE    Turn every phrase into an "embedding" (a list of numbers where
              phrases with similar meaning end up close together). Then:
                similarity      = how close two people's research topics are
                complementarity = how close one person's NEEDS are to the
                                  other person's OFFERS
  3. JUDGE    Only each person's best few candidates go to Claude, which scores
              both signals 0-10, rejects "different and not complementary"
              pairs, and writes the reason + warm intros.
  4. ASSIGN   Each person gets up to K matches, mixing similar and
              complementary ones when both exist.

Run (from inside the "5 - Match Generation" folder):
  python match_generation.py samples/sample_ideas.json samples/sample_matches.json --users samples/sample_users.json --offline
  python match_generation.py data/ideas.json data/matches.json --users data/users.json   # full mode, needs API key
  add  --previous data/old_matches.json  to never suggest a pair twice across runs

Accepts both input shapes: the Step 3/4 spec in the repo (one idea per row with
"summary", "type", "keywords", "score") and per-chat packages ("main_idea",
"insights", "raw_text", "rank_score").

People are always called by their username (Step 0 "pseudonym") in reasons and
intros, never "A"/"B" and never by their private real name.

Privacy: the raw chat text in each idea package is never read by this step,
never sent to Claude and never written to the output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# 0. Settings: the knobs you are most likely to tune
# ---------------------------------------------------------------------------
@dataclass
class Settings:
    matches_per_user: int = 5        # most suggestions any one person sees
    candidates_per_signal: int = 5   # per person: best N by similarity + best N by complementarity get judged
    candidate_floor: float = 0.20    # pre-score (0-1) needed to be judged at all
    min_match_score: float = 0.50    # final score (0-1) needed to be suggested
    judge_weight: float = 0.70       # how much the final score trusts Claude vs. the vector math
    both_bonus: float = 0.20         # extra credit when a pair is similar AND complementary
    top_ideas_per_user: int = 15     # only use each person's N most central ideas (Step 4 rank)
    profile_model: str = "claude-haiku-4-5-20251001"  # cheap + fast: one call per person
    judge_model: str = "claude-sonnet-5-5"            # smarter: one call per candidate pair
    embedding_model: str = "all-MiniLM-L6-v2"         # free, runs locally (sentence-transformers)
    offline: bool = False            # True = no API calls, no model download
    cache_file: str = "data/llm_cache.json"  # Claude answers saved here, so re-runs cost nothing
    workers: int = 4                 # Claude calls running at the same time


# ---------------------------------------------------------------------------
# Data shapes
# ---------------------------------------------------------------------------
@dataclass
class Idea:
    idea_id: str
    user_id: str
    main_idea: str
    insights: list
    rank: float = 1.0                                  # 0-1, from Step 4
    offers: list = field(default_factory=list)         # optional, if Step 3 already lists skills
    needs: list = field(default_factory=list)          # optional, if Step 3 already lists needs
    kind: str = ""                                     # Step 3 "type": interest/open_question/project/skill/need


@dataclass
class Phrase:
    text: str
    idea_id: str
    weight: float                                      # how central the source idea is (0-1)


@dataclass
class Person:
    user_id: str
    name: str                                          # username shown to others (Step 0 "pseudonym")
    ideas: list
    topics: list = field(default_factory=list)         # Phrase: main ideas + insights
    offers: list = field(default_factory=list)         # Phrase: what they can give
    needs: list = field(default_factory=list)          # Phrase: what they are missing
    summary: str = ""
    profile_source: str = ""
    looking_for: list = field(default_factory=list)    # Step 0: collaborator / co-founder / mentor / peer
    match_types: set = field(default_factory=lambda: {"similar", "complementary"})  # Step 0 preference


def log(msg=""):
    print(msg, flush=True)


# ---------------------------------------------------------------------------
# Loading Step 4 output
# ---------------------------------------------------------------------------
def _first(d, *keys, default=None):
    """Return the first key that exists (lets us accept small naming differences from Step 4)."""
    for k in keys:
        if d.get(k) not in (None, "", []):
            return d[k]
    return default


SKILL_TYPES = {"skill", "skills", "offer", "offers"}
NEED_TYPES = {"need", "needs"}


def _as_user_dict(users):
    """Step 0 records may come as a list, a dict keyed by user_id, or a single record."""
    if isinstance(users, dict) and "user_id" in users:
        users = [users]
    if isinstance(users, list):
        return {str(u["user_id"]): u for u in users if isinstance(u, dict) and "user_id" in u}
    return {str(k): v for k, v in (users or {}).items()}


def display_name(rec, uid):
    """The name other users see in reasons and intros: the Step 0 username ("pseudonym").
    Older sample files call it "name". Falls back to the user ID.
    Never reads rec["private"] (real name, email, affiliation): that stays private (D-002)."""
    return str(rec.get("pseudonym") or rec.get("name") or uid).strip()


def load_people(path, s: Settings, users_path=None) -> list:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    users, packages = {}, data
    if isinstance(data, dict):
        users = _as_user_dict(data.get("users"))
        packages = data.get("ideas", [])
    if users_path:                                      # Step 0 user records (usernames, preferences, consent)
        users.update(_as_user_dict(json.loads(Path(users_path).read_text(encoding="utf-8"))))

    by_user = {}
    for n, p in enumerate(packages):
        uid = str(_first(p, "user_id", "user"))
        insights = _first(p, "insights", "subtopics", "specific_insights", "keywords", default=[])
        if isinstance(insights, str):
            insights = [insights]
        idea = Idea(
            idea_id=str(_first(p, "idea_id", "id", default=f"{uid}_idea{n}")),
            user_id=uid,
            main_idea=str(_first(p, "main_idea", "summary", "idea", "title", default="")).strip(),
            insights=[str(x).strip() for x in insights if str(x).strip()],
            rank=float(_first(p, "rank_score", "score", "rank", default=1.0)),
            offers=list(_first(p, "offers", "skills", default=[])),
            needs=list(_first(p, "needs", default=[])),
            kind=str(p.get("type", "")).strip().lower(),
        )
        # Step 3 spec: a row of type "skill" IS an offer, a row of type "need" IS a need.
        # Its keywords are short, precise versions of the same skill/need, so they count too.
        if idea.kind in SKILL_TYPES:
            idea.offers = [x for x in [idea.main_idea] + idea.insights if x] + idea.offers
        if idea.kind in NEED_TYPES:
            idea.needs = [x for x in [idea.main_idea] + idea.insights if x] + idea.needs
        # NOTE: p["raw_text"] is deliberately ignored (privacy rule, see docstring).
        by_user.setdefault(uid, []).append(idea)

    top = max((i.rank for ideas in by_user.values() for i in ideas), default=1.0)
    people, no_consent = [], []
    for uid, ideas in by_user.items():
        rec = users.get(uid) or {}
        if (rec.get("consent") or {}).get("analyse_chats") is False:
            no_consent.append(uid)                      # never match someone who withdrew consent
            continue
        for i in ideas:                                 # put ranks on a 0-1 scale
            i.rank = float(np.clip(i.rank / top if top > 1 else i.rank, 0, 1))
        ideas = sorted(ideas, key=lambda i: i.rank, reverse=True)[: s.top_ideas_per_user]
        person = Person(uid, display_name(rec, uid), ideas)
        person.looking_for = [str(x) for x in (rec.get("looking_for") or [])]
        wanted = {str(t).lower() for t in (rec.get("match_types") or [])} & {"similar", "complementary"}
        if wanted:
            person.match_types = wanted
        for i in ideas:
            if i.kind in NEED_TYPES:                    # a need is not something they work on
                continue
            if i.main_idea:
                person.topics.append(Phrase(i.main_idea, i.idea_id, i.rank))
            person.topics += [Phrase(t, i.idea_id, i.rank * 0.8) for t in i.insights]
        people.append(person)
    if no_consent:
        log(f"  (skipped {len(no_consent)} user(s) without consent to analyse chats)")
    return people


# ---------------------------------------------------------------------------
# Claude helper (with a cache so you never pay twice for the same question)
# ---------------------------------------------------------------------------
def load_env():
    """Read ANTHROPIC_API_KEY from a .env file in this folder or the repo root."""
    for p in (HERE / ".env", HERE.parent / ".env"):
        if p.exists():
            for line in p.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


def parse_json(text):
    text = re.sub(r"```(?:json)?", "", text or "")
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        return None
    try:
        return json.loads(text[start: end + 1])
    except json.JSONDecodeError:
        return None


class Claude:
    def __init__(self, s: Settings):
        import anthropic                                # imported here so offline mode doesn't need it
        self.client = anthropic.Anthropic()             # reads ANTHROPIC_API_KEY from the environment
        self.path = HERE / s.cache_file
        self.cache = json.loads(self.path.read_text()) if self.path.exists() else {}
        self.lock = threading.Lock()
        self.new_calls = 0

    def ask_json(self, model, system, prompt, max_tokens=1200):
        key = hashlib.sha256(f"{model}\n{system}\n{prompt}".encode()).hexdigest()
        with self.lock:
            if key in self.cache:
                return self.cache[key]
        try:
            resp = self.client.messages.create(
                model=model, max_tokens=max_tokens, system=system,
                messages=[{"role": "user", "content": prompt}])
            text = "".join(getattr(b, "text", "") for b in resp.content)
        except Exception as e:                          # network/API problem: fall back, don't crash
            log(f"  ! Claude call failed ({type(e).__name__}: {e}) - using vector fallback for this item")
            return None
        data = parse_json(text)
        if data is not None:
            with self.lock:
                self.cache[key] = data
                self.new_calls += 1
        return data

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.cache, indent=1, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Stage 1 - PROFILE: what each person offers and needs
# ---------------------------------------------------------------------------
PROFILE_SYSTEM = """You help a platform that introduces scientific researchers to each other.
You will see one researcher's research ideas, distilled from their AI chat history.
List what this researcher can OFFER a collaborator and what they NEED from one.

Rules:
- Phrase offers and needs the SAME way: as the capability itself, so they can be compared directly.
  Good: "Bayesian deconvolution of noisy time series", "long-term coral reef monitoring dataset".
  Bad: "needs help with stats", "is good at modelling".
- OFFERS: methods, tools, datasets, instruments, field sites, domain expertise or access they clearly HAVE.
- NEEDS: specific gaps or bottlenecks slowing their work: missing methods, data, tools, expertise, samples or access.
- Use only what the ideas support. Do not invent. 0-6 items per list; fewer, specific items beat many vague ones.
- Tag each item with the idea_id it comes from.
- No names, institutions or personal details. Do not quote the source text.

Return JSON only, no other text:
{"summary": "one neutral sentence on what this researcher works on (third person, no names)",
 "offers": [{"idea_id": "...", "text": "..."}],
 "needs": [{"idea_id": "...", "text": "..."}]}"""

NEED_CUES = ("need", "looking for", "lack", "bottleneck", "struggl", "stuck", "no reliable way",
             "don't know how", "do not know how", "would help", "missing", "least reliable",
             "slow and expensive", "slow to", "unclear how")
OFFER_CUES = ("i built", "we built", "i developed", "we developed", "i develop", "we develop",
              "we have", "i have", "our ", "expertise in", "experience with", "our lab", "we record",
              "we run", "i run", "open-source", "dataset", "years of", "we benchmark", "lets us")


def profile_offline(p: Person):
    """Fallback without Claude: sort insights into needs/offers using cue words. Crude, demo only."""
    for idea in p.ideas:
        for t in idea.insights:
            low = t.lower()
            if any(c in low for c in NEED_CUES):        # check needs first: "we have no way..." is a need
                p.needs.append(Phrase(t, idea.idea_id, idea.rank))
            elif any(c in low for c in OFFER_CUES):
                p.offers.append(Phrase(t, idea.idea_id, idea.rank))
    p.summary = "; ".join([i.main_idea for i in p.ideas if i.kind not in NEED_TYPES][:2])
    p.profile_source = "keyword-fallback"


def profile_with_claude(p: Person, llm: Claude, s: Settings):
    prompt = "Research ideas for one researcher (most central first):\n\n" + "\n".join(
        f"idea_id: {i.idea_id} (centrality {i.rank:.2f}, type: {i.kind or 'n/a'})\n  main idea: {i.main_idea}\n"
        f"  details: {'; '.join(i.insights)}" for i in p.ideas)
    data = llm.ask_json(s.profile_model, PROFILE_SYSTEM, prompt)
    if not data:
        return profile_offline(p)
    rank_of = {i.idea_id: i.rank for i in p.ideas}

    def phrases(key):
        out = []
        for it in (data.get(key) or [])[:8]:
            it = it if isinstance(it, dict) else {"text": str(it)}
            text, iid = str(it.get("text", "")).strip(), str(it.get("idea_id", ""))
            if text:
                out.append(Phrase(text, iid, rank_of.get(iid, 0.5)))
        return out

    p.offers, p.needs = phrases("offers"), phrases("needs")
    p.summary = str(data.get("summary", "")).strip()
    p.profile_source = "claude"


def build_profiles(people, llm, s: Settings):
    def one(p):
        given = [i for i in p.ideas if i.offers or i.needs]
        if given:                                       # Step 3 already extracted skills/needs: use them
            for i in given:
                p.offers += [Phrase(str(t), i.idea_id, i.rank) for t in i.offers]
                p.needs += [Phrase(str(t), i.idea_id, i.rank) for t in i.needs]
            p.summary = "; ".join([i.main_idea for i in p.ideas if i.kind not in NEED_TYPES][:2])
            p.profile_source = "step-3-fields"
        elif llm:
            profile_with_claude(p, llm, s)
        else:
            profile_offline(p)
    with ThreadPoolExecutor(max(1, s.workers)) as pool:
        list(pool.map(one, people))


# ---------------------------------------------------------------------------
# Stage 2 - SCORE: vectors for every phrase, then two scores per pair
# ---------------------------------------------------------------------------
GENERIC = {"need", "looking", "help", "want", "would", "could", "work", "working", "use", "using",
           "used", "research", "project", "study", "problem", "way", "really", "also", "new",
           "method", "methods", "approach", "expertise", "experience", "someone", "people", "lab",
           "team", "better", "able", "know", "reliable", "reliably", "data", "model", "models", "good",
           "field", "real", "world", "large", "long", "term", "based"}


def _tokens(text):
    """Keyword tokenizer for the offline fallback: drop filler words, crude word stems."""
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
    out = []
    for w in re.findall(r"[a-z][a-z0-9]+", text.lower()):
        if w in ENGLISH_STOP_WORDS or w in GENERIC or len(w) < 3:
            continue
        if w.endswith("s") and len(w) > 4:
            w = w[:-1]
        out.append(w[:7])                               # "classify"/"classifier" -> "classif"
    return out


class Embedder:
    """Meaning-vectors. Uses a free local model if installed, else keyword vectors (TF-IDF)."""

    def __init__(self, s: Settings, corpus):
        if not s.offline:
            try:
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer(s.embedding_model)
                # cosine values below LO count as "unrelated", above HI as "near-identical"
                self.name, self.lo, self.hi = s.embedding_model, 0.20, 0.70
                return
            except Exception as e:
                log(f"  (sentence-transformers unavailable: {type(e).__name__}; using keyword vectors)")
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.model = TfidfVectorizer(tokenizer=_tokens, lowercase=False, token_pattern=None,
                                     sublinear_tf=True).fit(corpus or ["empty"])
        self.name, self.lo, self.hi = "keyword-tfidf (offline fallback)", 0.05, 0.40

    def encode(self, texts):
        if self.name.startswith("keyword"):
            v = self.model.transform(texts).toarray()
        else:
            v = self.model.encode(texts, normalize_embeddings=True)
        v = np.asarray(v, dtype=np.float32)
        norms = np.linalg.norm(v, axis=1, keepdims=True)
        return v / np.where(norms == 0, 1, norms)

    def scale(self, raw):
        """Map a raw cosine onto 0-1 so thresholds mean the same thing for any embedder."""
        return float(np.clip((raw - self.lo) / (self.hi - self.lo), 0, 1))


def attach_vectors(people, emb: Embedder):
    slots = [(p, kind) for p in people for kind in ("topics", "offers", "needs")]
    texts = [ph.text for p, kind in slots for ph in getattr(p, kind)]
    vecs = emb.encode(texts) if texts else np.zeros((0, 1))
    k = 0
    for p, kind in slots:
        n = len(getattr(p, kind))
        setattr(p, f"{kind}_vec", vecs[k:k + n])
        setattr(p, f"{kind}_w", np.array([ph.weight for ph in getattr(p, kind)], dtype=np.float32))
        k += n


def _centrality(w):
    return 0.75 + 0.25 * w                              # less-central ideas count up to 25% less


def similarity(a: Person, b: Person, emb: Embedder):
    """Average of the 3 closest topic pairs (closer + more central = higher)."""
    if not len(a.topics) or not len(b.topics):
        return 0.0, None
    M = (a.topics_vec @ b.topics_vec.T) * _centrality(np.sqrt(np.outer(a.topics_w, b.topics_w)))
    i, j = np.unravel_index(M.argmax(), M.shape)
    top3 = np.sort(M.ravel())[-3:]
    return emb.scale(top3.mean()), (a.topics[i], b.topics[j])


def coverage(needer: Person, giver: Person):
    """How well the giver's offers cover the needer's single best-covered need."""
    if not len(needer.needs) or not len(giver.offers):
        return 0.0, None
    M = needer.needs_vec @ giver.offers_vec.T
    best = M.max(axis=1) * _centrality(needer.needs_w)
    i = int(best.argmax())
    return float(best[i]), (needer.needs[i], giver.offers[int(M[i].argmax())])


def complementarity(a: Person, b: Person, emb: Embedder):
    """Strongest direction counts most; a two-way exchange scores higher."""
    ab, link_ab = coverage(a, b)                        # b has what a needs
    ba, link_ba = coverage(b, a)                        # a has what b needs
    raw = 0.7 * max(ab, ba) + 0.3 * min(ab, ba)
    links = {"b_helps_a": link_ab if emb.scale(ab) > 0 else None,
             "a_helps_b": link_ba if emb.scale(ba) > 0 else None}
    return emb.scale(raw), links


def score_all_pairs(people, emb: Embedder):
    pre = {}
    for x, a in enumerate(people):
        for b in people[x + 1:]:
            s_val, topic_pair = similarity(a, b, emb)
            c_val, links = complementarity(a, b, emb)
            pre[(a.user_id, b.user_id)] = {"sim": s_val, "comp": c_val,
                                           "topic_pair": topic_pair, "links": links}
    return pre


def pick_candidates(people, pre, s: Settings, skip=frozenset()):
    """Per person: best N partners by similarity + best N by complementarity (if above the floor).
    Pairs in `skip` (already suggested in an earlier run) are left out entirely."""
    chosen = set()
    for p in people:
        mine = [(k, v) for k, v in pre.items() if p.user_id in k and frozenset(k) not in skip]
        for signal in ("sim", "comp"):
            mine.sort(key=lambda kv: kv[1][signal], reverse=True)
            chosen |= {k for k, v in mine[: s.candidates_per_signal] if v[signal] >= s.candidate_floor}
    return sorted(chosen)


# ---------------------------------------------------------------------------
# Stage 3 - JUDGE: Claude checks each candidate pair and writes the reason
# ---------------------------------------------------------------------------
JUDGE_SYSTEM = """You decide whether two scientific researchers should be introduced, and why.

Score two things from 0 to 10.
SIMILARITY - are they working on the same problem, system or method?
  0-2 different fields; 3-4 same broad field, different questions; 5-7 overlapping questions or methods; 8-10 essentially the same problem.
COMPLEMENTARITY - does one have something specific the other needs?
  Score 6+ only if a concrete method, dataset, tool, instrument, expertise or access held by one researcher
  addresses a concrete need or bottleneck of the other, so working together would plausibly move at least one project forward.
  Vague benefits ("fresh perspective", "both use data", "interdisciplinary exchange") score 0-2.
VERDICT - "both" if both scores >= 6; "similar" if only similarity >= 6; "complementary" if only complementarity >= 6;
  otherwise "no_match". Different AND not complementary is always "no_match". When unsure, choose "no_match":
  a bad introduction costs more than a missed one.

Names: each researcher has a username. In every text you write (reason, intros, offers, topics), refer to a
researcher only by their username, spelled exactly as given. Never write "A", "B", "Researcher A", "Researcher B",
"the first researcher" or "the second researcher". The letters a and b appear only in the JSON field names;
the FIELD KEY in the message says which username each letter stands for.

Writing rules: use only the information given; never invent facts; never quote chat text; no personal details beyond research topics.
Intros: 1-2 warm, specific sentences addressed to the reader as "you", naming the other person by their username, ending with a concrete first topic to discuss.
If a researcher lists what they are looking for (collaborator, co-founder, mentor, peer), frame their intro around that. It does not change the scores.

Return JSON only, no other text:
{"similarity": 0, "complementarity": 0, "verdict": "no_match",
 "shared_topics": ["up to 3 short phrases"], "a_can_offer_b": "", "b_can_offer_a": "",
 "reason": "one neutral sentence", "intro_for_a": "", "intro_for_b": ""}"""


def describe(p: Person) -> str:
    lines = [f"RESEARCHER {p.name}"]
    if p.summary:
        lines.append(f"Summary: {p.summary}")
    lines.append("Research ideas (most central first):")
    for i in p.ideas[:8]:
        details = "; ".join(i.insights[:4])
        tag = f"[{i.kind}] " if i.kind else ""
        lines.append(f"- {tag}{i.main_idea}" + (f" | details: {details}" if details else ""))
    lines.append("Can offer: " + ("; ".join(x.text for x in p.offers) or "(none listed)"))
    lines.append("Needs: " + ("; ".join(x.text for x in p.needs) or "(none listed)"))
    if p.looking_for:
        lines.append("Looking for: " + ", ".join(p.looking_for))
    return "\n".join(lines)


def field_key(a: Person, b: Person) -> str:
    """Tells Claude which username each JSON field letter stands for, so the letters never reach the text."""
    return (f'FIELD KEY (for the JSON field names only; never write these letters in your text):\n'
            f'- a = {a.name}, b = {b.name}\n'
            f'- a_can_offer_b: what {a.name} can offer {b.name}; b_can_offer_a: what {b.name} can offer {a.name}\n'
            f'- intro_for_a is read by {a.name} (so it names {b.name}); '
            f'intro_for_b is read by {b.name} (so it names {a.name})')


def use_usernames(text: str, a: Person, b: Person) -> str:
    """Safety net: if Claude still wrote "Researcher A" / "user B" etc., put the username back in."""
    names = {"A": a.name, "B": b.name}
    return re.sub(r"\b(?i:researcher|person|user)\s+([AB])\b", lambda m: names[m.group(1)], text)


def verdict_from(sim, comp, t):
    if sim >= t and comp >= t:
        return "both"
    if sim >= t:
        return "similar"
    if comp >= t:
        return "complementary"
    return "no_match"


def judge_with_claude(a, b, pre, llm: Claude, s: Settings):
    hints = []
    if pre["topic_pair"]:
        x, y = pre["topic_pair"]
        hints.append(f'Closest topics: {a.name} "{x.text}" <-> {b.name} "{y.text}"')
    for key, (needer, giver) in (("b_helps_a", (a, b)), ("a_helps_b", (b, a))):
        if pre["links"].get(key):
            need, offer = pre["links"][key]
            hints.append(f'Possible need/offer link: {needer.name} needs "{need.text}" '
                         f'<-> {giver.name} offers "{offer.text}"')
    prompt = (describe(a) + "\n\n" + describe(b) + "\n\n" + field_key(a, b) +
              "\n\nHints from our vector search (may be wrong, judge for yourself):\n" +
              ("\n".join(f"- {h}" for h in hints) or "- none"))
    d = llm.ask_json(s.judge_model, JUDGE_SYSTEM, prompt)
    if not d:
        return None

    def num(x):
        try:
            return float(np.clip(float(x), 0, 10)) / 10
        except (TypeError, ValueError):
            return 0.0

    sim, comp = num(d.get("similarity")), num(d.get("complementarity"))
    verdict = verdict_from(sim, comp, 0.6)
    if str(d.get("verdict", "")).lower() == "no_match":
        verdict = "no_match"                            # if Claude says no, it's no
    return {"judged_by": "claude", "sim": sim, "comp": comp, "verdict": verdict,
            "shared_topics": [use_usernames(str(t), a, b) for t in (d.get("shared_topics") or [])][:3],
            **{k: use_usernames(str(d.get(k, "")).strip(), a, b) for k in
               ("a_can_offer_b", "b_can_offer_a", "reason", "intro_for_a", "intro_for_b")}}


def judge_with_vectors(a, b, pre):
    """Offline/fallback judge: vector scores + template text. Placeholder quality."""
    sim, comp = pre["sim"], pre["comp"]
    verdict = verdict_from(sim, comp, 0.5)
    out = {"judged_by": "vectors-only", "sim": sim, "comp": comp, "verdict": verdict,
           "shared_topics": [], "a_can_offer_b": "", "b_can_offer_a": "",
           "reason": "", "intro_for_a": "", "intro_for_b": ""}
    reasons, intro_a, intro_b = [], [], []
    if verdict in ("similar", "both") and pre["topic_pair"]:
        main = {i.idea_id: i.main_idea for i in a.ideas + b.ideas}
        x, y = (main.get(ph.idea_id, ph.text) for ph in pre["topic_pair"])
        out["shared_topics"] = [x if len(x) <= len(y) else y]
        reasons.append("they work on closely related topics")
        intro_a.append(f'{b.name} works on something close to your research: "{y}".')
        intro_b.append(f'{a.name} works on something close to your research: "{x}".')
    if verdict in ("complementary", "both"):
        for key, needer, giver, intros in (("b_helps_a", a, b, (intro_a, intro_b)),
                                           ("a_helps_b", b, a, (intro_b, intro_a))):
            link = pre["links"].get(key)
            if link:
                need, offer = link
                out["a_can_offer_b" if key == "a_helps_b" else "b_can_offer_a"] = offer.text
                reasons.append(f"{giver.name} may have what {needer.name} needs")
                intros[0].append(f'{giver.name} may have what you need. You noted: "{need.text}" '
                                 f'They bring: "{offer.text}"')
                intros[1].append(f'{needer.name} needs something you have: "{need.text}"')
    text = " and ".join(reasons) or "weak overlap"
    out["reason"] = text[0].upper() + text[1:] + "."
    out["intro_for_a"], out["intro_for_b"] = " ".join(intro_a), " ".join(intro_b)
    return out


def judge_all(cands, people, pre, llm, s: Settings):
    who = {p.user_id: p for p in people}

    def one(key):
        a, b = who[key[0]], who[key[1]]
        return key, ((llm and judge_with_claude(a, b, pre[key], llm, s))
                     or judge_with_vectors(a, b, pre[key]))
    with ThreadPoolExecutor(max(1, s.workers)) as pool:
        return dict(pool.map(one, cands))


# ---------------------------------------------------------------------------
# Stage 4 - ASSIGN: combine scores, give each person their top K
# ---------------------------------------------------------------------------
def combine(pre_v, j, s: Settings):
    w = s.judge_weight if j["judged_by"] == "claude" else 0.0
    sim = (1 - w) * pre_v["sim"] + w * j["sim"]
    comp = (1 - w) * pre_v["comp"] + w * j["comp"]
    return sim, comp, min(1.0, max(sim, comp) + s.both_bonus * min(sim, comp))


def linked_ideas(pre_v):
    """Spec field `shared_or_linked_ideas`: pairs of [user_a's idea_id, user_b's idea_id]."""
    pairs = []
    if pre_v["topic_pair"]:                             # their closest research topics
        pairs.append([pre_v["topic_pair"][0].idea_id, pre_v["topic_pair"][1].idea_id])
    if pre_v["links"].get("b_helps_a"):                 # a's need <-> b's offer
        need, offer = pre_v["links"]["b_helps_a"]
        pairs.append([need.idea_id, offer.idea_id])
    if pre_v["links"].get("a_helps_b"):                 # a's offer <-> b's need
        need, offer = pre_v["links"]["a_helps_b"]
        pairs.append([offer.idea_id, need.idea_id])
    out = []
    for p in pairs:
        if all(p) and p not in out:
            out.append(p)
    return out


def type_ok(person: Person, match_type: str) -> bool:
    """Respect Step 0 `match_types`. A "both" match suits anyone who wants either kind."""
    return bool(person.match_types) if match_type == "both" else match_type in person.match_types


def assign(judged, pre, people, s: Settings, first_id=1):
    who = {p.user_id: p for p in people}
    pool, unwanted = [], 0
    for (ua, ub), j in judged.items():
        sim, comp, score = combine(pre[(ua, ub)], j, s)
        if j["verdict"] == "no_match" or score < s.min_match_score:
            continue
        if not (type_ok(who[ua], j["verdict"]) and type_ok(who[ub], j["verdict"])):
            unwanted += 1                               # one side didn't ask for this kind of match
            continue
        pool.append({
            "user_a": ua, "user_b": ub, "match_type": j["verdict"],
            "score": round(score, 3), "similarity": round(sim, 3), "complementarity": round(comp, 3),
            "shared_or_linked_ideas": linked_ideas(pre[(ua, ub)]),
            "reason": j["reason"],
            "status": "suggested",
            "shared_topics": j["shared_topics"],
            "a_can_offer_b": j["a_can_offer_b"], "b_can_offer_a": j["b_can_offer_a"],
            "intro_for_a": j["intro_for_a"], "intro_for_b": j["intro_for_b"],
            "judged_by": j["judged_by"],
            "debug": {"vector_similarity": round(pre[(ua, ub)]["sim"], 3),
                      "vector_complementarity": round(pre[(ua, ub)]["comp"], 3),
                      "judge_similarity": round(j["sim"], 3), "judge_complementarity": round(j["comp"], 3)},
        })
    if unwanted:
        log(f"                 dropped {unwanted} match(es) of a type one side didn't ask for (Step 0 match_types)")
    pool.sort(key=lambda m: m["score"], reverse=True)

    # Each person picks their top K. If those are all one kind but a match of the other kind
    # exists further down, swap it in so people see both similar AND complementary researchers.
    # A pair is kept if it makes EITHER person's list, and is then shown to BOTH people
    # (Step 6 needs both sides to see it so they can both accept).
    keep = set()
    users = {u for m in pool for u in (m["user_a"], m["user_b"])}
    for u in users:
        mine = [i for i, m in enumerate(pool) if u in (m["user_a"], m["user_b"])]
        pick = mine[: s.matches_per_user]
        kinds = {pool[i]["match_type"] for i in pick}
        if s.matches_per_user >= 2 and len(pick) == s.matches_per_user and "both" not in kinds:
            for wanted in ("complementary", "similar"):
                if wanted not in kinds:
                    extra = next((i for i in mine[s.matches_per_user:] if pool[i]["match_type"] == wanted), None)
                    if extra is not None:
                        pick[-1] = extra
                    break
        keep.update(pick)

    matches = []
    for n, m in enumerate((m for i, m in enumerate(pool) if i in keep), first_id):
        matches.append({"match_id": f"m_{n:04d}", **m})  # match_id first, like the spec
    by_user = {}
    for m in matches:
        for u in (m["user_a"], m["user_b"]):
            by_user.setdefault(u, []).append(m["match_id"])
    return matches, by_user


def load_previous(path):
    """Pairs already suggested in an earlier run (any status), and the next free match number."""
    if not path or not Path(path).exists():
        if path:
            log(f"  (no previous matches file at {path} - starting fresh)")
        return frozenset(), 1
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    old = data.get("matches", []) if isinstance(data, dict) else data
    pairs = frozenset(frozenset((m["user_a"], m["user_b"])) for m in old)
    nums = [int(m["match_id"][2:]) for m in old if re.fullmatch(r"m_\d+", str(m.get("match_id", "")))]
    return pairs, max(nums, default=0) + 1


# ---------------------------------------------------------------------------
# Run everything
# ---------------------------------------------------------------------------
def _spread(values):
    if not values:
        return "n/a"
    v = np.array(values)
    return f"min {v.min():.2f} | median {np.median(v):.2f} | max {v.max():.2f}"


def run(in_path, out_path, s: Settings, users_path=None, previous_path=None):
    load_env()
    people = load_people(in_path, s, users_path)
    log(f"Loaded {len(people)} people and {sum(len(p.ideas) for p in people)} ideas from {in_path}")

    llm = None
    if not s.offline:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            log("  (no ANTHROPIC_API_KEY found - Claude steps will use the offline fallback)")
        else:
            try:
                llm = Claude(s)
            except ImportError:
                log("  (anthropic package not installed - run: pip install -r requirements.txt)")

    build_profiles(people, llm, s)
    sources = {}
    for p in people:
        sources[p.profile_source] = sources.get(p.profile_source, 0) + 1
    log(f"Stage 1 PROFILE  {sources}")

    corpus = [ph.text for p in people for kind in ("topics", "offers", "needs") for ph in getattr(p, kind)]
    emb = Embedder(s, corpus)
    attach_vectors(people, emb)
    pre = score_all_pairs(people, emb)
    skip, first_id = load_previous(previous_path)
    cands = pick_candidates(people, pre, s, skip)
    log(f"Stage 2 SCORE    vectors: {emb.name} | pairs scored: {len(pre)} | sent to judge: {len(cands)}"
        + (f" | skipped as already suggested: {sum(1 for k in pre if frozenset(k) in skip)}" if skip else ""))
    log(f"                 similarity      {_spread([v['sim'] for v in pre.values()])}")
    log(f"                 complementarity {_spread([v['comp'] for v in pre.values()])}")

    judged = judge_all(cands, people, pre, llm, s)
    rejected = sum(1 for j in judged.values() if j["verdict"] == "no_match")
    by_judge = {}
    for j in judged.values():
        by_judge[j["judged_by"]] = by_judge.get(j["judged_by"], 0) + 1
    log(f"Stage 3 JUDGE    judged: {by_judge} | rejected as no_match: {rejected}")

    matches, by_user = assign(judged, pre, people, s, first_id)
    log(f"Stage 4 ASSIGN   matches: {len(matches)} | people with at least one match: "
        f"{len(by_user)}/{len(people)}")
    if llm:
        llm.save()
        log(f"                 new Claude calls this run: {llm.new_calls} (others came from cache)")

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "claude" if llm else "offline",
        "embedder": emb.name,
        "settings": asdict(s),
        "people": {p.user_id: {"name": p.name, "summary": p.summary} for p in people},
        "matches": matches,
        "by_user": by_user,
    }
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"Wrote {out_path}\n")

    names = {p.user_id: p.name for p in people}
    for p in people:
        log(p.name)
        ids = by_user.get(p.user_id, [])
        if not ids:
            log("   (no matches)")
        for m in (m for m in matches if m["match_id"] in ids):
            other = m["user_b"] if m["user_a"] == p.user_id else m["user_a"]
            log(f"   {m['score']:.2f}  {m['match_type']:<13} {names[other]}")
    return result


def main():
    ap = argparse.ArgumentParser(description="Step 5: match researchers on similarity + complementarity")
    ap.add_argument("input", help="Step 4 output (JSON)")
    ap.add_argument("output", help="where to write the matches (JSON)")
    ap.add_argument("--users", help="Step 0 user records (JSON): usernames, match preferences, consent")
    ap.add_argument("--previous", help="an earlier matches file: pairs in it are never suggested again")
    ap.add_argument("--offline", action="store_true", help="no API calls or model downloads (demo/testing)")
    ap.add_argument("--k", type=int, help="max matches per person (default 5)")
    ap.add_argument("--min-score", type=float, help="minimum final score 0-1 (default 0.5)")
    args = ap.parse_args()
    s = Settings(offline=args.offline)
    if args.k:
        s.matches_per_user = args.k
    if args.min_score is not None:
        s.min_match_score = args.min_score
    run(args.input, args.output, s, args.users, args.previous)


if __name__ == "__main__":
    main()
