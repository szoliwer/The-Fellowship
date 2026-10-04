"""Glue that joins the steps into one app (owned by the integration lead).

Each step keeps its own logic and screens in its own folder. This package only holds what
sits *between* steps, plus clearly labelled placeholders for parts not built yet:

  ranking.py        Step 3 → Step 4 bridge: a placeholder ranking (Step 4's ranking isn't built)
  ideas_page.py     page 3: runs Step 3 (idea_generation.py) for the logged-in user
  matching_page.py  page 5: runs Step 5 (match_generation.py) for everyone who approved ideas
  matches.py        match view + Accept/Pass status, used by the Step 6 placeholder
  discover_page.py  page 6: PLACEHOLDER until Step 6's own page exists
"""
