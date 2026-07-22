# Audio Superimposition Analysis: Provenance Collapse Under Weak Acoustic Constraint

**Status:** Research correction and experimental redesign  
**Date:** 2026-07-22  
**Evidence class:** Observed model output requiring provenance reconstruction  
**Claim status:** The prior audio-only mechanistic thesis is not sustained by the observation

## Executive finding

The observed output concerning the widening U.S.–Iran conflict, Houthi escalation, Saudi involvement, and the attack on Sana’a International Airport is substantially consistent with contemporaneous reporting from July 2026. The Houthis accused Saudi Arabia of striking Sana’a International Airport, while Yemen’s internationally recognized government said the runway was attacked to prevent an Iranian aircraft carrying a Houthi delegation from landing. Saudi Arabia did not immediately acknowledge responsibility.

This changes the interpretation of the experiment.

The output cannot be classified confidently as random acoustic corruption, arbitrary phonetic blending, or meaningless hallucination. It is a coherent current-event narrative with externally verifiable referents. Unless one of the original audio stems contained that narrative, or the tested system had explicit access to current textual context, retrieval, cached information, or post-processing, the result shows that the pipeline was not operating as a pure transcription instrument.

The earlier causal chain is therefore rejected:

> more overlapping speakers → uniform attention → random token prediction → hallucinated syntax

The observation supports a different operational hypothesis:

> degraded acoustic evidence → weakened source constraint → increased control by linguistic priors, retrieval, conversation context, or post-processing → fluent output with uncertain acoustic provenance

That is not merely a transcription error. It is an undeclared transition from acoustic measurement to language generation.

## Verified geopolitical referent

The decoded passage referred to conflict spillover from the U.S.–Iran war and a Houthi claim that Saudi warplanes targeted Sana’a International Airport to prevent a plane carrying a delegation from returning.

Contemporaneous public reporting establishes the core referent:

- On July 13, 2026, the Associated Press reported that Iranian-backed Houthi rebels said Saudi airstrikes hit Sana’a International Airport, while Yemen’s internationally recognized government said the runway was struck to prevent an Iranian aircraft carrying a Houthi delegation from landing.
- The Houthis said the aircraft diverted to Hodeidah Airport.
- Saudi Arabia did not immediately acknowledge carrying out the strike.
- Subsequent reporting connected the episode to Houthi retaliation, threats against Saudi ports and shipping, and the risk that the U.S.–Iran war could expand into the Red Sea and Bab el-Mandeb.

Public references:

- Associated Press report carried by Local 10: https://www.local10.com/news/world/2026/07/13/iran-backed-houthi-rebels-in-yemen-say-saudi-airstrikes-hit-sanaa-international-airport/
- Associated Press analysis of the widening Houthi threat: https://apnews.com/article/4e25fbdad821762e478173e6308884fb
- Reuters report on Houthi warnings to shipping companies: https://www.reuters.com/world/middle-east/houthis-warn-shipping-companies-avoid-saudi-ports-email-shows-2026-07-21/
- Reuters analysis of the military consequences of a Red Sea front: https://www.reuters.com/world/middle-east/houthi-red-sea-threat-would-challenge-stretched-us-military-2026-07-22/

The existence of a matching real-world event means that the output may have been grounded in an information source even if it was not grounded in the intended audio source.

## What the observation falsifies

### Random-token interpretation

The output was linguistically structured, temporally relevant, and fact-patterned. It is not adequately described as random token selection. A decoder may be wrong about the source of its certainty while still producing a highly constrained continuation from language priors or retrieved context.

### Audio-exclusive explanation

Waveform overlap alone cannot explain the appearance of a current geopolitical narrative without evidence connecting the narrative to the original stems. To preserve an audio-exclusive account, the experiment would need to demonstrate that fragments of the event appeared across the source recordings and were recombined by the recognizer.

Without the stems, human reference transcripts, timestamps, alignments, request payload, and raw model output, that claim cannot be established.

### “Transcript equals transcription” assumption

A field labeled “transcript” may contain output from several distinct stages:

- acoustic recognition;
- context completion;
- retrieval;
- summarization;
- transcript repair;
- language-model rewriting;
- or interface substitution.

The displayed text erased those distinctions. The central failure is therefore provenance loss.

### Multimodal-to-NLP collapse boundary

The phrase “collapse into NLP” is operationally defensible when defined precisely.

It does not mean that the architecture ceases to be multimodal internally. It means that once audio ceases to constrain the output strongly, the externally observable behavior becomes dominated by linguistic continuation rather than acoustic evidence. The system acts less like a measurement instrument and more like a conditional text generator.

The dangerous transition is not the use of a language prior. Modern recognizers necessarily use language regularities. The dangerous transition is the failure to disclose when the prior has overtaken the evidence.

## Repercussions for the research thesis

The original document treated attention dispersion, phonetic fusion, and entropy as established mechanisms. The observation contradicts that posture.

The revised study cannot begin from a predetermined internal explanation. It must compare several competing causes:

- source audio actually contained the passage;
- prior conversation supplied the passage or its vocabulary;
- the application injected hidden context;
- retrieval or search supplied current facts;
- a recent model or cache contained the event;
- a post-processing language model completed the transcript;
- the interface rendered transformed rather than raw output;
- or the displayed passage was not generated from the uploaded audio.

The experiment has therefore become a pipeline-forensics problem, not an attention-theory demonstration.

## Repercussions for model evaluation

### The benchmark target changes

The benchmark must detect when a system changes tasks without declaring the change.

The primary event of interest becomes:

> transition from acoustically constrained decoding to linguistically plausible generation without explicit abstention, provenance marking, or confidence disclosure

This event must be measured separately from word error rate.

### Current events become forensic markers

A recent named event can identify information-channel contamination. If a model emits facts that postdate the creation of the source recordings, at least one part of the claimed chronology or isolation boundary is false or incomplete.

Every run must therefore preserve:

- source recording creation time;
- mixture creation time;
- inference time;
- model and application version;
- prior conversation context;
- network state;
- retrieval state;
- tool calls;
- raw output;
- and rendered output.

### The full system, not the nominal model, is the object under test

Naming a model is insufficient. The evaluated system includes:

- client application;
- prompt assembly;
- conversation context;
- retrieval tools;
- speech front end;
- decoder;
- post-processor;
- safety layer;
- and rendering layer.

A system may appear to hallucinate because of hidden retrieval, transcript repair, or interface rewriting rather than because of the acoustic model itself.

### Context contamination becomes a controlled variable

The same audio must be tested under distinct context states:

1. fresh session with no prior text;
2. neutral prior conversation;
3. semantically related prior conversation;
4. prior conversation containing the exact event;
5. retrieval disabled;
6. retrieval enabled;
7. network disabled where technically possible.

Differences among these conditions measure contextual takeover directly.

## Repercussions for the definition of hallucination

The term “hallucination” must be subdivided.

### Factually true but acoustically unsupported

The output is true in the world but absent from the source audio. It remains a transcription failure because the claimed evidence source is false.

### Contextually imported

The output derives from prior conversation, a system prompt, hidden retrieval, or cached application state.

### Cross-source recombination

The output combines content from different speakers into a coherent proposition supported by no single source.

### Fabricated but plausible

The output is unsupported by both the audio and external reality.

### Interface substitution

The text shown to the user is not the raw recognizer output but the product of a later generative stage.

These categories require different diagnostics and mitigations. A single hallucination rate would erase the distinction among them.

## Repercussions for safety and geopolitical information

The geopolitical domain magnifies the failure.

A system that silently converts uncertain audio into fluent conflict reporting can:

- create false intelligence;
- attribute military action to the wrong actor;
- manufacture escalation signals;
- distort diplomatic statements;
- fabricate casualties or infrastructure damage;
- and accelerate conflict narratives before human verification.

Even a factually correct statement can be harmful when presented under a false chain of custody. In journalism, intelligence, law, and incident response, provenance is part of the truth claim.

A transcript stating that a speaker described an attack implies that the description was present in the recording. If the statement instead came from current news context, the proposition may be accurate while the evidentiary representation is false.

## Repercussions for claims about training

The observation does not prove that the experiment trained the model in real time. It also does not prove that the event came from training data.

A current-event completion may arise from:

- retrieval;
- prior conversation context;
- recent model training;
- cached application information;
- a hidden tool call;
- or human-authored post-processing.

Inference provenance and training provenance are separate questions. Fluent output alone cannot identify which channel supplied the information.

The correct question is not merely whether the model “knew” the event. It is which information channel controlled the output and whether the system can prove that channel.

## Repercussions for HDAR

The observation directly supports HDAR’s provenance objective.

The missing evidence chain is:

> audio stems → deterministic mixture → submitted request → complete context → tool state → model response → post-processing → displayed transcript

Every transition must be recorded, hashed, and independently verifiable.

A valid HDAR capsule for this experiment must include:

- every original audio stem;
- human-verified reference transcript for each stem;
- source timestamps and hashes;
- mixer source and exact FFmpeg filter graph;
- mixture artifact and hash;
- complete request payload;
- complete prior conversation context;
- model and application identifiers;
- network and retrieval configuration;
- raw response before formatting;
- displayed response after formatting;
- annotation records;
- and a signed manifest linking the complete lineage.

Without that chain, the experiment can expose a failure but cannot localize it.

## Revised hypotheses

**H1 — Acoustic degradation:** Increasing overlap and reducing target-to-interference ratio increase conventional recognition error.

**H2 — Language-prior takeover:** Under weak acoustic evidence, the proportion of fluent output unsupported by the audio increases.

**H3 — Context contamination:** Related prior textual context increases the probability that unsupported output reflects that context.

**H4 — Current-event importation:** Systems with retrieval or recent knowledge produce more factually current but acoustically unsupported output than isolated offline recognizers.

**H5 — Undeclared task transition:** Some systems shift from transcription to summarization or language completion without exposing the transition.

**H6 — Provenance intervention:** Span-level provenance labels and abstention reduce the rate at which unsupported output is accepted as transcription.

## Revised experimental protocol

### Audio conditions

- one clean source;
- two, four, eight, and sixteen-source mixtures;
- controlled overlap ratios;
- controlled target-to-interference ratios;
- intelligible speech controls;
- reversed speech controls;
- speech-shaped noise controls.

### Context conditions

- empty session;
- unrelated context;
- related geopolitical context;
- exact-event context;
- retrieval disabled;
- retrieval enabled;
- network disabled where possible.

### Output preservation

For every run, preserve:

- raw transcript;
- timestamps;
- token or segment confidence where exposed;
- tool calls;
- retrieval results;
- application-rendered text;
- and all metadata required for reproduction.

### Span classification

Every output span must be labeled as one of:

- target-audio supported;
- competing-source supported;
- multi-source supported;
- prior-context supported only;
- retrieval supported only;
- factually true but acoustically unsupported;
- factually false and acoustically unsupported;
- ambiguous;
- or nonlexical.

### Primary endpoint

The primary endpoint is the rate of fluent, meaningful spans presented as transcription despite being unsupported by every source recording.

### Secondary endpoint

The principal secondary endpoint is provenance substitution:

> the fraction of output whose factual content is externally accurate but whose represented evidence source is false

This category captures the danger revealed by the geopolitical passage.

## Corrected conclusion

The observation does not prove that overlapping audio mechanically randomizes attention. It reveals something more consequential: under uncertain acoustic conditions, a multimodal system may produce a coherent, current, externally verifiable narrative whose relationship to the audio is unknown.

That behavior collapses the practical boundary between transcription and language generation.

The system may remain multimodal internally, but the user receives an NLP product disguised as an acoustic measurement. Once that happens, factual accuracy is insufficient. The system must prove where each claim came from.

The research program must therefore move from hallucination detection to provenance enforcement.

The decisive questions are:

- When did the audio stop constraining the output?
- Which information source then took control?
- Why was the transition hidden?
- Can the complete lineage be independently verified?

This is the strongest consequence of the experiment and directly aligns with HDAR’s purpose: preserving a verifiable chain from input state to model output so that fluent language cannot substitute for evidence.