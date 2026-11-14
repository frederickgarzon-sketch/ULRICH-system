# Research screening summary

> Update 2026-10-11: participant-facing reports and exports now return descriptive behavioral records/features only (`research_screening.status = descriptive_only`, `score = null`). The optional reference/composite code below remains an offline research tool, not an automatic participant result. See `CLIENT_FIX_CHECKLIST_2026-10-11.md`.

The session report includes descriptive behavioral features and an optional
experimental composite. It does **not** diagnose ADHD and must not be used as a
replacement for clinical history, multi-setting observations, standardized
rating scales, or qualified professional assessment.

## Features

- omission rate;
- commission rate;
- reaction-time coefficient of variation;
- longest error-free attention span;
- task-minus-baseline blink-rate change;
- mean body movement during the task; and
- mean angular head speed during the task.

Task measurements use the first recorded trial through the last trial plus one
trial interval. Baseline blink rate uses the period before the first trial.

## Reference guard

The application looks for `data/research_reference_features.csv`. The composite
is withheld unless at least 30 rows match the participant's age group and enough
non-constant values exist to calculate at least three signal indicators. The
example file documents the required columns but is intentionally too small to
unlock scoring.

Reference rows must come from an approved research protocol. Do not duplicate,
fabricate, or label ordinary participant sessions as a typically developing
reference cohort merely to unlock the score.

Even when calculated, the output is labelled **Experimental Behavioral
Indicator**, version `research-0.1`, and **not clinically validated**.

