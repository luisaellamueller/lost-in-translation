# Screening of the machine translations (French-authored sample)

Completed outputs: 259; failed (output limit): 1.

## Automatic checks

- Stopped normally: 259 of 259; end with sentence punctuation: 259 of 259.
- Length ratio machine/French words: 0.73-1.03 (median 0.86); official/French median 0.91.
- French function-word share > 5%: 1 (20153944).
- Repeated 6-grams (> 3 repeats): 7 (20154097, 20164070, 20203335, 20013164, 20023261, 20083550, 20163049).

Inspection of flagged texts (annotations):

- 20013164 (repetition_flag): mirrors_source. États du sud et de l'est de la Méditerranée appears twice in the French
- 20023261 (repetition_flag): mirrors_source. mesures ... pour permettre aux détenus repeated as in the French
- 20083550 (repetition_flag): mirrors_source. list of colourings repeated as in the French
- 20154097 (repetition_flag): mirrors_source. the French names "Message 2015 sur les constructions" four times (slightly varied wording); the output repeats one rendering
- 20163049 (repetition_flag): mirrors_source. liste des mandats de gestion passage repeated as in the French
- 20164070 (repetition_flag): mirrors_source. mercury thresholds and cadastre phrase repeated as in the French
- 20203335 (repetition_flag): mirrors_source. the French states the 1% tax on fortunes above 2 million twice (different wording); the output repeats one rendering
- 20153944 (french_flag): not_untranslated. flag caused by an invented expansion of LIFD/LHID into French law names; no French passage

## Reading sample (random.Random(2026), 20 texts, opening ~100 words)

- ok: 10; minor: 5; content-changing: 5

- 20244110: minor. broken relative clause in second sentence; meaning recoverable
- 20133348: ok
- 20254642: minor. concessive "Si" rendered as conditional "Wenn"
- 20223284: ok
- 20073201: content. postulat -> "Petition"; "LPP" -> "Rentenversicherungssystem"
- 20203069: minor. French abbreviations OFEV/CCE kept
- 20253316: minor. first sentence ungrammatical; "à l'horizon 2030" -> "im Jahr 2030"
- 20213158: ok
- 20083138: content. Valais -> "Waals" (Wallis); sentence structure garbled
- 20003094: minor. pour seulement cinq jours d'exposition omitted
- 20174092: content. poursuites -> "Klagen" (Swiss term: Betreibungen); "émoluments" -> "Honorare"
- 20233852: ok
- 20113806: ok
- 20214097: ok
- 20223224: ok
- 20003435: content. 145 milliards -> "14
- 20133239: ok
- 20063383: content. parenthesis turned into a contradictory time clause ("als die Post ... 2006 bekannt gab")
- 20183432: ok
- 20083928: ok
