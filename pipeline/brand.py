"""Look and feel shared by every page, recreated from the Lovable website design
(0 - User Registration/lovable codebase/…/src/routes/index.tsx and src/styles.css).
Colours and fonts are set in .streamlit/config.toml; this file holds the logo, the small
uppercase labels, the landing-page sections, the match card and the floating Next button.
Presentation only: no logic or data lives here."""

import html
from pathlib import Path

import streamlit as st

ASSETS = Path(__file__).resolve().parent / "assets"
LOGO, ICON = ASSETS / "logo.svg", ASSETS / "icon.svg"
NAME = "The Fellowship"

# (menu title, what the step is called), in order.
STEPS = [("Import", "Import chats"), ("Privacy", "Privacy check"), ("Ideas", "Find ideas"),
         ("Review", "Review ideas"), ("Matches", "Find matches"), ("Discover", "Connect")]

# Colour tokens from the Lovable design (converted from oklch).
C = {"bg": "#EAF3EC", "fg": "#101E16", "card": "#FCFEFC", "primary": "#166845", "primary_fg": "#F9FDFA",
     "muted_fg": "#55655B", "border": "#C1CFC5", "surface": "#F7FBF8", "peer": "#CCEEFF", "peer_fg": "#005B91",
     "peer_strong": "#1C90CB", "self": "#CDEED9", "complement": "#FFE3B3", "complement_fg": "#8B4B00"}

_CSS = f"""
<style>
/* Page frame: room for the fixed top menu and the floating Next button. */
[data-testid="stMainBlockContainer"]{{padding-top:5rem;padding-bottom:6rem}}
.st-key-fs_next{{position:fixed;right:2rem;bottom:1.75rem;z-index:1000;width:auto}}
.st-key-fs_next button{{box-shadow:0 24px 70px -32px rgba(16,30,22,.45);padding:.65rem 1.4rem}}
/* Small uppercase label above headings ("eyebrow"). */
.fs-eyebrow{{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:.75rem;font-weight:500;
  letter-spacing:.18em;text-transform:uppercase;color:{C['primary']};margin:0 0 .25rem}}
.fs-muted{{color:{C['muted_fg']}}}
/* Match card (Discover, and the example on the landing page). */
.fs-card{{border:1px solid {C['border']};background:{C['card']};border-radius:.45rem;overflow:hidden;
  box-shadow:0 24px 70px -32px rgba(16,30,22,.45)}}
.fs-card-head{{display:flex;justify-content:space-between;align-items:center;padding:1rem 1.5rem;
  border-bottom:1px solid {C['border']}}}
.fs-card-title{{font-family:Newsreader,Georgia,serif;font-size:1.5rem;font-weight:600;color:{C['fg']}}}
.fs-tag{{font-family:"IBM Plex Mono",monospace;font-size:.65rem;text-transform:uppercase;letter-spacing:.08em}}
.fs-split{{display:grid;grid-template-columns:1fr 1fr}}
.fs-them{{background:{C['peer']};padding:1.6rem 1.25rem;border-right:1px solid {C['border']}}}
.fs-you{{background:{C['self']};padding:1.6rem 1.25rem}}
.fs-them .fs-tag{{color:{C['peer_fg']}}} .fs-you .fs-tag{{color:{C['primary']}}}
.fs-split p{{margin:.9rem 0 0;font-size:.9rem;line-height:1.55;color:{C['fg']}}}
.fs-middle{{position:relative;text-align:center;padding:1.75rem 1.5rem;border-top:1px solid {C['border']}}}
.fs-badge{{position:absolute;left:50%;top:0;transform:translate(-50%,-50%);background:{C['complement']};
  color:{C['complement_fg']};padding:.25rem .75rem}}
.fs-badge.similar{{background:{C['peer']};color:{C['peer_fg']}}}
.fs-middle .fs-quote{{font-family:Newsreader,Georgia,serif;font-style:italic;font-size:1.5rem;margin:0;color:{C['fg']}}}
.fs-middle p{{margin:.5rem auto 0;max-width:34rem;font-size:.9rem;line-height:1.6;color:{C['muted_fg']}}}
.fs-card-foot{{display:flex;justify-content:space-between;align-items:center;padding:1rem 1.5rem;
  border-top:1px solid {C['border']}}}
.fs-avatars span{{display:inline-flex;width:2.5rem;height:2.5rem;align-items:center;justify-content:center;
  border:2px solid {C['card']};border-radius:999px;color:{C['primary_fg']};font-weight:700}}
.fs-avatars span+span{{margin-left:-.5rem}}
.fs-cta-link{{font-size:.9rem;font-weight:600;color:{C['primary']}}}
/* Landing page sections. */
.fs-hero h1{{font-family:Newsreader,Georgia,serif;font-weight:600;font-size:clamp(3rem,6vw,5.5rem);
  line-height:.96;margin:.5rem 0 0;color:{C['fg']};padding:0}}
.fs-hero .fs-lead{{margin-top:1.6rem;font-size:1.2rem;line-height:1.65;color:{C['muted_fg']};max-width:36rem}}
.fs-section h2{{font-family:Newsreader,Georgia,serif;font-weight:600;font-size:clamp(2.2rem,4vw,3.6rem);
  line-height:1.05;margin:.75rem 0 0;color:{C['fg']};padding:0}}
.fs-steps-list{{border-top:1px solid {C['border']};border-bottom:1px solid {C['border']}}}
.fs-steps-list article{{display:grid;grid-template-columns:3.5rem 1fr;gap:1rem;padding:1.75rem 0}}
.fs-steps-list article+article{{border-top:1px solid {C['border']}}}
.fs-steps-list .num{{font-family:"IBM Plex Mono",monospace;font-size:.75rem;color:{C['muted_fg']};padding-top:.4rem}}
.fs-steps-list h3,.fs-promises h3{{font-family:Newsreader,Georgia,serif;font-size:1.5rem;font-weight:600;margin:0;
  color:{C['fg']};padding:0}}
.fs-promises h3{{font-family:Manrope,sans-serif;font-size:1.1rem}}
.fs-steps-list p,.fs-promises p{{margin:.5rem 0 0;line-height:1.65;color:{C['muted_fg']}}}
.fs-promises article{{border-left:2px solid {C['primary']};padding:.75rem 0 .75rem 1.5rem;margin-bottom:1rem}}
.st-key-fs_cta{{background:{C['primary']};border-radius:.45rem;padding:3.5rem 1.5rem;text-align:center}}
.st-key-fs_cta .fs-eyebrow{{color:{C['primary_fg']};opacity:.7}}
.st-key-fs_cta h2{{color:{C['primary_fg']}!important}}
.st-key-fs_cta button{{background:{C['card']}!important;color:{C['primary']}!important;border:none!important}}
.fs-footer{{display:flex;justify-content:space-between;flex-wrap:wrap;gap:.75rem;padding:2rem 0 0;
  border-top:1px solid {C['border']};color:{C['muted_fg']};font-size:.9rem}}
.fs-footer b{{font-family:Newsreader,Georgia,serif;font-size:1.1rem;color:{C['fg']}}}
</style>
"""


def page_style(wide=False):
    """Shared styles; wide=True for the landing page (the Lovable site is wider than an app page)."""
    wide_css = ("<style>[data-testid='stMainBlockContainer']{max-width:1180px;"
                "padding-left:clamp(1.25rem,4vw,2.5rem);padding-right:clamp(1.25rem,4vw,2.5rem)}</style>")
    st.html(_CSS + (wide_css if wide else ""))


def scroll_to_top():
    """Start at the top of the page (e.g. right after signing in from far down the landing page).
    Retries for a moment, because the page is still being drawn when this runs."""
    import streamlit.components.v1 as components
    components.html(
        "<script>let n = 0; const t = setInterval(() => {"
        " const m = window.parent.document.querySelector('[data-testid=\"stMain\"]');"
        " if (m) m.scrollTo(0, 0); if (++n > 10) clearInterval(t); }, 100);</script>",
        height=0)


def eyebrow(text):
    st.html(f'<p class="fs-eyebrow">{html.escape(text)}</p>')


def step_eyebrow(current_title):
    """'STEP 2 OF 6 · PRIVACY CHECK' above each step page's title."""
    titles = [title for title, _ in STEPS]
    if current_title in titles:
        i = titles.index(current_title)
        eyebrow(f"Step {i + 1} of {len(STEPS)} · {STEPS[i][1]}")


def next_step_button(current_title, pages):
    """One green "Next: …" button on every step page except the last. It keeps you signed in
    (st.switch_page; a plain web link would reload the page and sign you out)."""
    titles = [title for title, _ in STEPS]
    if current_title not in titles or current_title == titles[-1]:
        return
    title, label = STEPS[titles.index(current_title) + 1]
    with st.container(key="fs_next"):
        if st.button(f"Next: {label}", icon=":material/arrow_forward:", icon_position="right", type="primary"):
            st.switch_page(pages[title])


# ---------- Match card (Lovable "A promising connection" panel) ----------

def match_card_html(title, them_name, them_idea, you_name, you_idea, kind, quote, text, foot=""):
    """kind: "complementary", "similar" or "both". All text is escaped (it can come from users or Claude)."""
    e = html.escape
    badge = {"both": "Similar and complementary", "similar": "Similar work"}.get(kind, "Complementary")
    initials = f'<span style="background:{C["peer_strong"]}">{e(them_name[:1].upper())}</span>' \
               f'<span style="background:{C["primary"]}">{e(you_name[:1].upper())}</span>'
    return f"""
<div class="fs-card">
  <div class="fs-card-head"><span class="fs-card-title">{e(title)}</span></div>
  <div class="fs-split">
    <div class="fs-them"><span class="fs-tag">Them · {e(them_name)}</span><p>{e(them_idea)}</p></div>
    <div class="fs-you"><span class="fs-tag">You · {e(you_name)}</span><p>{e(you_idea)}</p></div>
  </div>
  <div class="fs-middle"><span class="fs-badge fs-tag {'similar' if kind == 'similar' else ''}">{e(badge)}</span>
    <p class="fs-quote">{e(quote)}</p><p>{e(text)}</p></div>
  <div class="fs-card-foot"><div class="fs-avatars">{initials}</div><span class="fs-cta-link">{e(foot)}</span></div>
</div>"""


# ---------- Landing page sections (Lovable index.tsx) ----------

HERO_TITLE = "Meet people by what they're thinking about."
HERO_LEAD = ("Your best collaborator may already be exploring the same question, or holding the missing piece. "
             "The Fellowship finds that connection.")

HOW_IT_WORKS = [
    ("01", "Bring your conversations", "Upload a ChatGPT or Claude export, saved notes, or paste a chat. You choose "
                                       "what comes in; nothing is pulled without you."),
    ("02", "We find the signal", "Personal details are removed or held back. Only the ideas, questions and skills "
                                 "you approve are used for matching."),
    ("03", "Meet your intellectual neighbours", "Discover people exploring the same frontier, or bringing a "
                                                "capability that complements yours. You both decide whether to connect."),
]

PROMISES = [
    ("Opt-in by design", "You decide which chats to provide. There is no silent account connection or "
                         "background collection."),
    ("Personal details held back", "Personal information and low-signal chatter are removed before any idea is "
                                   "used for matching."),
    ("Mutual consent", "A connection opens only when both people choose it. Until then you are known only by "
                       "your username."),
]


def hero_html():
    return (f'<div class="fs-hero"><p class="fs-eyebrow">Ideas that connect</p><h1>{html.escape(HERO_TITLE)}</h1>'
            f'<p class="fs-lead">{html.escape(HERO_LEAD)}</p></div>')


def example_card_html():
    return match_card_html(
        "A promising connection", "binding_lab", "Diffusion models for protein-binding predictions",
        "assay_bench", "SPR binding assays on small-molecule libraries", "complementary",
        "Meet. Learn. Collaborate.", "Together, you could test which compounds are worth taking into the lab.",
        "A conversation worth starting →")


def how_it_works_html():
    rows = "".join(f'<article><span class="num">{n}</span><div><h3>{html.escape(t)}</h3>'
                   f'<p>{html.escape(c)}</p></div></article>' for n, t, c in HOW_IT_WORKS)
    return (f'<div class="fs-section"><p class="fs-eyebrow">How it works</p>'
            f'<h2>From chat history to human connection.</h2></div>', f'<div class="fs-steps-list">{rows}</div>')


def privacy_html():
    items = "".join(f'<article><h3>{html.escape(t)}</h3><p>{html.escape(c)}</p></article>' for t, c in PROMISES)
    return (f'<div class="fs-section"><p class="fs-eyebrow">Privacy</p><h2>Your chats remain yours.</h2>'
            f'<p class="fs-muted" style="font-size:1.1rem;line-height:1.65;margin-top:1.25rem">They are processed '
            f'to identify ideas, not to build a dossier. Raw conversation text is never shown to another member.</p>'
            f'</div>', f'<div class="fs-promises">{items}</div>')


def footer_html():
    return (f'<div class="fs-footer"><b>{NAME}</b>'
            f'<span>An AI-native discovery network for thoughtful people.</span></div>')
