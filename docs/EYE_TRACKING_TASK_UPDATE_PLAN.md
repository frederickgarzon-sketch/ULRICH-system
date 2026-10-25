# Eye-Tracking Task and User-Friendly Dashboard Update Plan

**Status:** Protocol foundation and research-based full reporting implemented; gaze validation and Everyday Planning task remain pending  
**Prepared:** 2026-09-18  
**System:** Behavioral Monitoring System  

> This system is a research-support and screening-assistance platform. It is not a standalone ADHD diagnostic instrument.

## 1. Research basis

Primary reference:

- Chen X, Wang S, Yang X, et al. *Utilizing artificial intelligence-based eye tracking technology for screening ADHD symptoms in children.* Frontiers in Psychiatry. 2023;14:1260031.
- DOI: `10.3389/fpsyt.2023.1260031`
- PubMed: <https://pubmed.ncbi.nlm.nih.gov/38034916/>
- Full text: <https://pmc.ncbi.nlm.nih.gov/articles/PMC10682190/>

Secondary naturalistic-task reference:

- Merzon L, Pettersson K, Aronen ET, et al. *Eye movement behavior in a real-world virtual reality task reveals ADHD in children.* Scientific Reports. 2022;12:20308.
- DOI: `10.1038/s41598-022-24552-4`
- PubMed: <https://pubmed.ncbi.nlm.nih.gov/36434040/>
- Full text: <https://pmc.ncbi.nlm.nih.gov/articles/PMC9700686/>

Supporting literature-review source:

- Perkins LE. *Role of Eye-Tracking Technology and Software Algorithms in Enhancing ADHD Detection and Diagnosis: A Systematic Literature Review.* Georgia Southern University Honors College Thesis 1042. 2025.
- Record: <https://digitalcommons.georgiasouthern.edu/honors-theses/1042/>

The Perkins review summarizes clinical, observational, and machine-learning literature involving saccades, fixations, and blink rate. Its conclusion supports eye tracking and software analysis as potential supplements to traditional assessment while emphasizing variation across age groups and study designs and the need for further validation and standardization. Because this is an undergraduate honors thesis/literature review rather than a peer-reviewed primary validation study, it is used here to locate and organize candidate measures—not to establish diagnostic accuracy or implementation parameters.

The study involved children aged 6–12 years and used a consumer 13-inch tablet with a 30 Hz front-facing camera. Its approximately six-minute eye-tracking protocol contained a simple fixation task, 14 prosaccade trials, and 14 antisaccade trials.

The paper supports using fixation and saccadic-task measurements as objective research indicators associated with attention and inhibitory control. It does not establish eye tracking as an independent clinical diagnosis of ADHD.

The secondary study used EPELI (Executive Performance in Everyday LIving), an immersive virtual-reality task. It involved 37 children with ADHD and 36 typically developing controls aged 9–13 years. Participants completed 13 everyday-life scenarios containing 70 subtasks over approximately 25–35 minutes while using a head-mounted display with an integrated 90 Hz eye tracker. A support vector machine using fixation duration, saccade duration, and saccade amplitude achieved a cross-validated AUC of 0.92 in that study. This is a study-specific result—not an expected accuracy for this project.

The secondary paper supports adding ecologically oriented, multi-step tasks and whole-session behavioral features. It cannot be directly reproduced by the current webcam/tablet setup because the present system has neither an immersive VR environment nor a validated 90 Hz gaze tracker.

The supporting review reinforces an important separation in the data model:

- **Blink family:** blink count, rate, duration, and eye-closure quality.
- **Fixation family:** fixation location, duration, dispersion, and interruptions.
- **Saccade family:** onset, direction, latency, amplitude, duration, velocity, and correction.
- **Task family:** accuracy, omission/commission errors, reaction time, and completion efficiency.
- **Movement family:** calibrated head and regional body movement.

These families must not be collapsed into one “attention” or “ADHD” score without a prespecified, independently validated model.

### 1.1 Complementary role of the two papers

| Evidence source | Strongest contribution to this project | Directly implementable now? |
|---|---|---|
| Chen et al. tablet study | Short fixation, prosaccade, and antisaccade protocol using consumer-grade imagery | Task presentation and event logging: yes; paper-equivalent gaze metrics: not until validated |
| Merzon et al. EPELI study | Naturalistic multi-step behavior, executive performance, task efficiency, action count, movement, and distractors | Simplified non-VR task design and metrics: yes; VR gaze replication/classifier: no |
| Perkins systematic review | Candidate feature families, software/ML directions, and cross-study limitations | Supports architecture and literature tracing; does not prescribe a validated local protocol |

The first release should use the short standardized eye-control battery as the core experimental task and add a separate, clearly labelled **Everyday Planning Pilot** inspired by EPELI. It must not be called EPELI unless the licensed/authorized implementation and validated protocol are actually used.

### 1.2 EPELI-derived measures worth adapting

The EPELI study reported five established task-performance measures:

- **Total score:** percentage of assigned subtasks completed successfully.
- **Task efficacy:** relevant actions as a proportion of actions taken.
- **Navigation efficacy:** completion relative to movement/navigation cost.
- **Controller motion:** cumulative controller angular movement.
- **Total actions:** total interaction count during instructions and execution.

For this non-VR system, safe analogues are:

- completed steps / assigned steps;
- correct or relevant actions / total actions;
- completion time and unnecessary navigation between on-screen areas;
- mouse/touch travel or interaction movement, kept separate from body-camera movement;
- total clicks/taps, repeated actions, corrections, and instruction revisits;
- body/head movement summarized across the entire scenario;
- performance with and without controlled distractors.

These are locally defined analogues, not validated EPELI scores. Their names, formulas, and limitations must be shown in the protocol and report.

## 2. Paper protocol to be represented in the system

### 2.1 Simple fixation task

- Recorded duration: 30 seconds.
- Participant maintains gaze on a central target.
- Intended measurements:
  - central-area fixation duration;
  - number of gaze interruptions or fixation intervals;
  - proportion of valid tracked time;
  - tracking loss and invalid frames.

### 2.2 Prosaccade task

- Four practice trials are recommended locally before recording.
- Fourteen recorded trials: seven left and seven right.
- Participant looks toward the lateral target.
- Intended measurements:
  - correct initial direction;
  - response latency;
  - amplitude;
  - peak and mean velocity;
  - error-correction latency;
  - valid/invalid trial count.

### 2.3 Antisaccade task

- Four practice trials are recommended locally before recording.
- Fourteen recorded trials: seven left and seven right.
- Participant looks away from the lateral target.
- Intended measurements:
  - correct initial direction;
  - direction error rate;
  - adjusted accuracy after self-correction;
  - correction latency;
  - response latency, amplitude, and velocity;
  - valid/invalid trial count.

### 2.4 Trial behavior

- Trials must be randomized while remaining balanced by task type and direction.
- A center fixation gate of at least 500 ms is required before a recorded trial begins.
- The paper used a green center cue for prosaccade and red for antisaccade. The participant instructions must also use shape/text cues so color is not the only instruction channel.
- Trial timestamps must use a monotonic server/client clock suitable for reaction-time measurement.
- A trial must be marked invalid rather than silently scored when the face or required eye features are lost.

## 3. Phenotypic-behavior mapping

| Research construct | Task or observation | Candidate measurements | Interpretation boundary |
|---|---|---|---|
| Inattention / visual persistence | Simple fixation | central fixation duration, gaze interruptions, valid fixation time | Research indicator only |
| Reflexive orienting | Prosaccade | direction accuracy, latency, amplitude, velocity | Age and task conditions affect performance |
| Inhibitory control | Antisaccade | direction errors, adjusted accuracy, correction latency | Must not be treated as a diagnosis |
| Impulsive response tendency | Antisaccade and existing response task | premature/incorrect direction and commission errors | Combine with task context, not camera data alone |
| Hyperactivity / restlessness | Existing body camera during all modules | regional movement, posture changes, movement frequency | The cited eye-tracking paper did not validate body metrics |
| Performance consistency | All recorded trials | within-session variability and time-on-task trend | Fatigue, hunger, medication, age, and test time are confounders |

The final research report must keep task performance, eye behavior, head movement, blink measurements, and body movement as separate measurement families. A combined score may only be introduced after a documented validation study.

## 4. Honest capability boundary

### Available in the current system

- Face detection and face landmarks.
- Eye aspect ratio, eye open/closed state, and blink measurements.
- Calibrated relative head pose and head movement.
- Body pose, regional movement, and posture changes.
- Visual attention-task presentation, response accuracy, and reaction time.
- Session, participant, calibration, and database records.

### Not yet validated or complete

- Screen-coordinate gaze estimation.
- Saccade onset, amplitude, gain, and velocity.
- Fixation classification and intrusive-saccade counting.
- Paper-equivalent prosaccade/antisaccade scoring.
- A trained and locally validated AI gaze model comparable to the study model.
- Diagnostic classification of ADHD or ADHD presentation/subtype.

Eye landmarks or iris overlays must never be labelled as gaze tracking. Until the gaze module passes validation, the new task may record target events, button responses, head pose, blink, and body behavior, but gaze-dependent outputs must display **Not available — gaze model not validated**.

## 5. Physical setup profiles

The system requires two explicit profiles rather than one universal distance:

### Face and blink monitoring

- Target face-camera distance: 40 cm.
- Approved guidance band: 35–45 cm.
- Purpose: detailed face landmarks, blink, and relative head-pose monitoring.

### Paper-aligned eye-task research

- Target viewing distance: 60–80 cm for the paper's 13-inch setup.
- Both eyebrows, eyes, and chin must remain visible.
- The paper used a well-lit room and reported 800–1200 lux.
- Screen size, target geometry, camera field of view, and viewing distance must be recorded in the session metadata.

The 60–80 cm protocol cannot automatically be transferred to a different display size. Before formal data collection, target visual angles and gaze accuracy must be recalculated and pilot-tested for the actual tablet or monitor.

## 6. User-friendly dashboard specification

### 6.1 Two interface levels

**Operator mode** is the default and presents only the guided workflow, actionable status, and essential controls.

**Research/Admin mode** contains task parameters, thresholds, diagnostics, exports, landmark configuration, validation information, and audit history. Access remains protected by the researcher login.

### 6.2 Operator workflow

1. Select or create a coded participant.
2. Confirm consent and session metadata.
3. Run camera, lighting, distance, and tracking checks.
4. Select an accepted calibration profile.
5. Select the standardized task battery.
6. Read the participant instruction script.
7. Complete practice trials.
8. Run the recorded task with pause and abort controls.
9. Review data quality and invalid trials.
10. Save/finalize the session and generate a research report.

### 6.3 Main dashboard content

- Participant code and session ID.
- Face and body camera traffic-light status.
- Calibration status and age of calibration.
- Current task, trial number, elapsed time, and estimated time remaining.
- Data-quality status with a plain-language reason.
- Primary actions: Start, Pause, Resume, Abort, and Finish.
- A collapsed **Technical details** group for EAR, yaw/pitch/roll, FPS, latency, dropped frames, and inference timing.

### 6.4 Participant task screen

- Full-screen, distraction-minimized layout.
- One instruction at a time with a short demonstration.
- Practice completion gate before recorded trials.
- Large target and unambiguous direction cue.
- Progress shown without exposing scores during testing.
- Operator-controlled pause/abort behavior.
- No dashboard navigation, technical indicators, or researcher controls visible to the participant.

## 7. Task duration and difficulty policy

### Standard research battery

- Setup and instruction: 2–4 minutes.
- Practice: 1–2 minutes.
- Paper-aligned eye-control battery: approximately 6 minutes.
- Optional seated body baseline: 2–3 minutes.
- Expected total visit segment: approximately 10–15 minutes, excluding consent and troubleshooting.

The exact duration, number of trials, inter-stimulus interval, and target timing must be versioned and locked once formal data collection starts.

### Difficulty

- **Standardized Research** is the default and uses identical parameters for comparable participants.
- **Easy**, **Moderate**, and **Hard** presets may be provided for piloting or training but must never change automatically during a fixed research protocol.
- **Adaptive** mode is future work and must be recorded as a distinct protocol; adaptive and fixed-session results must not be pooled without an analysis plan.

Possible preset differences include target size, presentation time, response window, distractor count, and working-memory load. Every report must store the exact protocol version and parameters—not only the difficulty label.

## 8. User manual additions

The user manual must document:

1. Research purpose and non-diagnostic limitation.
2. Participant eligibility and the approved age range for the local study.
3. Consent/assent and coded participant identification.
4. Medication, vision correction, color-vision, sleep, fatigue, hunger, and test-time metadata required by the approved protocol.
5. Device startup, network, SSH, server, and camera-node checks.
6. Screen, chair, face camera, and body camera placement.
7. Lighting and measured distance requirements.
8. Calibration and data-quality gates.
9. Exact operator script for every task.
10. Practice and recorded-trial rules.
11. Pause, abort, reconnection, and invalid-trial handling.
12. Task-specific captured variables and calculations.
13. Session review, finalization, deletion authorization, and export.
14. Troubleshooting and escalation.
15. Privacy, retention, backup, and access controls.
16. References, software version, model version, and protocol version.

## 9. Planned implementation phases

### Implementation record — 2026-09-18

Completed foundation:

- Added versioned `research_task_runs` and `research_task_trials` database tables without changing or deleting existing records.
- Added immutable protocol/version/configuration snapshots, random seed, gaze-provider identity, and validation status.
- Added reproducible balanced Eye Control plans: four practice trials, one recorded fixation block, 14 prosaccade trials, and 14 antisaccade trials.
- Added explicit practice/recorded phases, trial status, tracking validity, invalid reason, expected/observed direction, response latency, and client monotonic timestamps.
- Added API endpoints for protocol catalog, run start/status/abort, next trial, and trial completion.
- Enforced the validated-gaze gate. Eye landmarks cannot unlock gaze-dependent recording.
- Added research-task content to session reports and safe deletion order for associated records.
- Added an operator-facing protocol catalog showing `Validation required`, `Planned`, duration, capability, and non-diagnostic status.
- Added automated protocol and API tests. Full suite result at this checkpoint: **62 passed**.

Completed reporting update — 2026-09-18:

- Full reports now include participant profile, consent/context fields, operator/session metadata, and notes.
- Objective Blink, Head, Body, Response Task, and Eye-Control families remain visibly separate.
- Reports calculate response-time variability and task-type validity/accuracy only from locally recorded data.
- Automatic quality warnings expose missing samples, missing completed trials, low valid-trial coverage, and unvalidated gaze.
- A descriptive research-context section maps each measurement family to a construct without producing an ADHD score or classification.
- All three supplied research sources appear in the report with the exact role and limitation of each source.
- JSON and ZIP exports contain the same expanded report data.

Still pending:

- Participant-facing Eye Control task presentation and operator-run controls.
- Everyday Planning Pilot task content and scoring formulas.
- A real gaze-provider implementation and validation dataset/harness.
- Task-specific report visualizations and final screenshot-based manual update.
- Pilot validation and protocol freeze.

### Phase A — Protocol and data contracts

- Define task/trial/event database schemas.
- Define protocol versions, randomized trial generation, invalid-trial reasons, and immutable session snapshots.
- Add research metadata and non-diagnostic language.

### Phase B — Professional guided UI

- Separate Operator and Research/Admin experiences.
- Implement the compact session wizard and participant-only task screen.
- Add practice, countdown, progress, pause, abort, reconnect, and completion states.

### Phase C — Fixation/prosaccade/antisaccade task engine

- Implement central fixation, balanced randomized trials, cues, monotonic timestamps, and task-event recording.
- Initially label gaze-dependent outputs unavailable unless a validated gaze provider is active.

### Phase C2 — Everyday Planning Pilot

- Add short, age-appropriate multi-step scenarios using ordinary on-screen interaction rather than claiming VR equivalence.
- Record assigned/completed steps, relevant and irrelevant actions, action sequence, instruction revisits, corrections, completion time, and input-device travel.
- Synchronize task events with head, blink, and body telemetry.
- Provide controlled distractor-free and distractor-present protocol variants only when approved in the study design.
- Keep all locally adapted measures separate from published EPELI scores.

### Phase D — Gaze provider and validation harness

- Introduce a replaceable gaze-provider interface rather than coupling the task to one model.
- Build calibration-point collection, accuracy/error measurement, screen-coordinate normalization, and per-trial quality checks.
- Evaluate model error across participants, lighting, viewing distance, glasses, screen size, and head movement.
- Define fixation and saccade event algorithms independently from the blink algorithm; document sampling-rate requirements and confidence thresholds for each.
- Stratify validation results by age and other approved demographic/technical factors rather than assuming one threshold works for every participant.
- Compare any machine-learning model against transparent task-only and eye-feature-only baselines.
- Reserve a participant-independent holdout set; frames or trials from one participant must not appear across training and test partitions.

### Phase E — Reporting and manual

- Add task-specific session results, invalid-trial counts, protocol metadata, and separate behavioral measurement families.
- Update the complete user manual and operator scripts with screenshots.

### Phase F — Pilot validation

- Run engineering timing and repeatability tests.
- Conduct an ethics-approved pilot with an a priori analysis plan.
- Freeze the protocol before collecting the formal dataset.
- Do not release a combined screening/classification score until sensitivity, specificity, calibration, bias, and external validation are documented.

## 10. Acceptance criteria before formal use

- Every session stores the exact task and model version.
- Trial order is randomized, balanced, reproducible from a stored seed, and auditable.
- Reaction timestamps are monotonic and timing error is measured.
- Lost tracking creates an explicit invalid trial.
- Practice data never enters recorded outcome calculations.
- Operator and participant screens are visually and functionally separated.
- All task instructions are understandable without developer assistance.
- Distance, lighting, framing, and camera-status guidance are visible before Start.
- Reports distinguish observed data, derived measurements, missing values, and quality warnings.
- Reports clearly distinguish the standardized eye-control battery, locally adapted everyday-task measures, and any future VR-derived measures.
- No screen or report states that the system diagnoses ADHD.
- Gaze metrics remain disabled until the gaze validation gate passes.
- Any reported classifier performance identifies the dataset, participant-level split, sample size, confidence interval, and external-validation status.

## 11. Decisions required before coding is finalized

- Approved participant age range.
- Actual task display device and physical screen size.
- Whether the 40 cm face camera and 60–80 cm task-viewing setup use the same or separate camera.
- Exact ethics/consent requirements and permitted metadata.
- Whether the first release is a task-and-event implementation only or includes development of a new gaze-estimation model.
- Fixed standardized timing values for the local pilot.

These decisions change protocol validity and must be recorded rather than silently assumed in code.
