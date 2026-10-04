# Showcase data for the hosted demo

Loaded by `pipeline/showcase.py` when the app starts with an empty `data/` folder (the hosted demo,
after every restart). Never loaded over existing data. Rebuild with `.venv/bin/python -m pipeline.build_showcase`.

**This folder is public.** It holds only:
- the two **synthetic** demo researchers (researcher_014, cellbio_027): made-up chats, their privacy-check
  results, and Step 4's sample ideas approved (labelled as sample data on the Review page). Their own Step 3
  result has only two short ideas each, which Step 5 doesn't shortlist (below its 0.20 pre-score), so the
  sample ideas are used to show a real match. "Find my ideas" still works and is instant (cached);
- for our team's accounts: **username and approved ideas** (amanjalan1997, ecology_expert, szoliwer, researcher_1, robo67, researcher_cancer),
  the ideas each person chose to share with matches. No chats, emails, names or passwords;
- the matches between everyone, one connected demo pair and a short synthetic conversation.

Matches in this bundle (3):
- researcher_014 ↔ cellbio_027 (both)
- ecology_expert ↔ researcher_cancer (both)
- amanjalan1997 ↔ szoliwer (similar)
