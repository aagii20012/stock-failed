- **When prose paraphrases a sealed `measurement`, name the denominator the seal names.** Generation 2
  Attempt 3's report says the concentration condition measures a share of "**gross profit**". The sealed
  text — byte-identical in `config/generation_2/g2_gate_criteria_ra1.json` and `..._ra3.json`, and
  implemented as `total = sum(contributions.values())` at `g2_gate_ra1.py:697` — divides by the **net**
  sum over all closed episodes. The two are not close: the same run measures `0.7505` of net and
  `0.2413` of gross, so the misreading is the difference between the recorded `FAIL` and a `PASS`. The
  gate followed the seal, so the verdict is right and only two sentences are wrong — but they were
  already hashed into the manifest, so the repair was disclosure in the session report, not an edit.
  Extract the `measurement` string and quote it, or restate it and diff your restatement against it.
