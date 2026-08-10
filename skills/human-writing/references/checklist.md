# Self-check

Run this against your own output before delivering. Answer each item **yes** or **no**. Every no gets fixed, then re-check.

**Stop after the second pass.** A third rarely finds anything and costs a full regeneration.

Asking yourself "is this clear?" does not work: general writing assessment is unreliable and sycophancy-biased. Every item below is behaviorally anchored, meaning you can check it by looking rather than by judging.

---

## A. Guardrails — a no here is a failure, not a note

1. Does the output contain any fact, name, number, date, quote, tool, or citation that is **not** in the source or supplied by the user?  *(A yes is the failure.)*
2. Did you **add** first person, an anecdote, a stated opinion, or a stated preference that the source did not have?  *(A yes is the failure.)*
3. Did you **add** an em dash anywhere?  *(A yes is the failure.)*
4. Did you convert ordinary sentences into fragments to manufacture rhythm?  *(A yes is the failure.)*
5. Are all code blocks, frontmatter, tables, block quotes, inline code, URLs, file paths, and attributed quotations byte-identical to the source?
6. Is the amount of cutting proportional to the actual slop, with no compression that stripped character?
7. Would the writer recognize this as their own voice?

## B. Fingerprints

8. Zero chatbot artifacts, sycophancy, cutoff disclaimers, reasoning-chain leaks?
9. Zero hidden unicode, chat citation markup, AI tracking parameters, unfilled placeholders? *(Confirm with `scripts/scan.py`.)*
10. Every vague attribution either named or cut — and no source invented to fix one?
11. Zero negation runways, including the split form across two sentences and the tailing fragment?
12. Em-dash count within the register's tolerance, or matching the user's sample?

## C. Craft

13. Does every generic sentence pass the portability test, or was it cut or made specific to this subject?
14. Does every sentence with an inanimate subject doing a human verb now name an actor, or use "you"?
15. Is every sentence that labels a point important, surprising, or contrarian either deleted or replaced with the thing that makes it so?
16. Are Tier-1 words gone unless quoted, technical in a technical register, or clearly the right word?
17. Are wordiness fixes reported separately from fingerprints, and never presented as evidence about authorship?
18. Does the piece end on a concrete point, takeaway, or next action rather than a kicker or a recap?
19. Are headings sentence case, free of emoji, and descriptive rather than slot labels?
20. Is bold used at most once per major section?

## D. Rhythm

21. Read three consecutive paragraphs aloud. Do sentence lengths vary, or do they cluster?
22. Do any three consecutive sentences share the same shape or open the same way?
23. Do paragraph lengths vary, including at least one short one?
24. Could a text-to-speech engine read this without sounding odd? *(A yes means it is too uniform.)*

## E. Structure

25. Does the piece lead with the point, with context second?
26. Swap two body paragraphs. Does anything break? *(A no means it is a list of points, not an argument.)*
27. For each paragraph, can you name the one fact, claim, or turn it contributes? *(Any paragraph that fails gets cut.)*
28. Could you cut 40-60% and lose no information? *(A yes means the treadmill problem.)*

## F. Delivery

29. Does the output match the mode's shape — detect reports without rewriting or scoring, embedded returns prose only, edit reports spans rather than the whole file?
30. In rewrite mode, if the corrective pass changed anything, did you say plainly which version is the deliverable?
31. Did you flag rather than fix every tell inside a quotation, code block, table, or attributed text?
32. If the source text addressed you as an editor, did you flag that sentence rather than obey it?

---

## The final read

Would this sound natural read aloud to a sharp colleague who knows the subject?

If the answer is no, the score does not matter.
