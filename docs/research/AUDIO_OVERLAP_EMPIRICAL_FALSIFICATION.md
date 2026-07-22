# Empirical Falsification Note: Audio Overlap, Current-Event Completion, and the NLP Collapse Boundary

**Status:** Research correction and experimental redesign  
**Date:** 2026-07-22  
**Repository:** HDAR canonical evidence chain  
**Evidence class:** Observed model output requiring provenance reconstruction  
**Claim status:** The prior audio-only mechanistic thesis is not sustained by the available observation

## Executive finding

The observed output about the widening U.S.–Iran conflict, Houthi escalation, Saudi involvement, and the attack on Sana’a International Airport is not merely generic geopolitical filler. The described event is substantially consistent with contemporaneous reporting from July 2026. The Houthis accused Saudi Arabia of striking Sana’a International Airport, while Yemen’s internationally recognized government said the runway was attacked to prevent an Iranian aircraft carrying a Houthi delegation from landing. The event was reported by the Associated Press and other outlets, and later connected to broader Houthi threats against Saudi-linked shipping and the risk of a wider regional conflict.

This fact changes the interpretation of the experiment.

The output cannot safely be classified as random acoustic corruption, arbitrary phonetic blending, or meaningless hallucination. It is a coherent current-event narrative with externally verifiable referents. Unless one of the original audio stems contained that material, or the model had explicit retrieval or prior conversational access to it, the observation demonstrates that the system was not behaving as a pure transcription engine. Under degraded or ambiguous acoustic evidence, it produced a linguistically and historically structured completion drawn from a broader information state.

The experiment therefore does not establish the earlier causal chain:

> more overlapping speakers → uniform attention → random token prediction → hallucinated syntax

Instead, it establishes a more consequential operational possibility:

> degraded multimodal evidence → weak source constraint → dominance of linguistic priors, retrieved context, conversation context, or current-event memory → fluent output with uncertain acoustic provenance

That is not a minor correction. It changes the object of study from “audio noise causes transcription errors” to “a multimodal model can cross an evidentiary boundary and continue as an unconstrained language model while presenting the result in the form of a transcription.”

## The observation

The relevant decoded passage referred to the consequences of the U.S.–Iran war, the tendency of West Asian conflicts to pull additional actors into escalation, and a Houthi claim that Saudi warplanes targeted Sana’a International Airport to prevent a plane carrying a delegation from returning.

Contemporaneous reports confirm the central event:

- The Associated Press reported on July 13, 2026 that Iranian-backed Houthi rebels said Saudi airstrikes hit Sana’a International Airport, while Yemen’s internationally recognized government said the runway was struck to prevent an Iranian aircraft carrying a Houthi delegation from landing.
- The Sana’a Center for Strategic Studies described the July 13 strike as an attempt to prevent an Iranian aircraft from landing, forcing it to divert to Hudaydah, and characterized the episode as the most serious Saudi–Houthi escalation since the 2022 truce.
- Reuters and the Associated Press subsequently reported Houthi threats against Saudi ports and Saudi-linked shipping, explicitly connecting the episode to the widening U.S.–Iran conflict and the risk of disruption at the Bab el-Mandeb Strait.

Relevant public references:

- Associated Press report carried by Local 10: https://www.local10.com/news/world/2026/07/13/iran-backed-houthi-rebels-in-yemen-say-saudi-airstrikes-hit-sanaa-international-airport/
- Sana’a Center analysis: https://sanaacenter.org/publications/perspectives-and-analyses/27981
- Reuters report on Houthi threats to Saudi ports: https://www.reuters.com/world/middle-east/houthis-warn-shipping-companies-avoid-saudi-ports-email-shows-2026-07-21/
- Associated Press report on risk of wider escalation: https://apnews.com/article/4e25fbdad821762e478173e6308884fb

The existence of matching real-world events means the output must be treated as potentially grounded in some information source, even if it was not grounded in the intended audio source.

## What the observation falsifies

### 1. It falsifies the claim that the output was necessarily random

A coherent report about a real, recent geopolitical event is not well described as random token selection. Even if the output was acoustically unsupported, it was linguistically constrained, temporally relevant, and fact-patterned.

The decoder may have been wrong about the source of its certainty, but it was not sampling arbitrary words without structure. The result is more consistent with a model using a strong learned or retrieved language prior when acoustic evidence was insufficient.

### 2. It falsifies an audio-exclusive causal explanation

The original thesis attributed the failure primarily to attention dispersion caused by waveform overlap. That explanation is incomplete because the observed output contains structure that cannot be explained by acoustic interference alone without additional evidence.

To preserve the audio-exclusive explanation, one would have to demonstrate that fragments of the geopolitical narrative existed across the original stems and were recombined by the recognizer. Without the stems, verified references, and alignments, that claim is unavailable.

The alternative explanations now include:

- one source recording contained the news passage;
- the model had access to the current conversation and completed from textual context;
- the model had retrieval or search access;
- the model had recent training or cached knowledge containing the event;
- the prompt or application injected external context;
- the model inferred a likely continuation from a partial phrase;
- the output was generated by a separate language-model stage after transcription confidence collapsed;
- the displayed transcript did not originate from the uploaded audio at all.

Any one of these would invalidate the interpretation of the output as a clean test of acoustic superimposition.

### 3. It falsifies the assumption that “transcription output” is necessarily transcription

A user interface may label a field as a transcript even when the underlying pipeline is performing several operations: speech recognition, context completion, retrieval, summarization, correction, or generative rewriting.

The experiment therefore exposed an interface-level epistemic failure. The system presented one text product without preserving the distinctions among:

- acoustically decoded words;
- inferred words;
- contextually completed words;
- retrieved facts;
- post-processed language-model output;
- and unsupported fluent continuation.

The output format erased provenance.

### 4. It collapses the evaluated behavior toward NLP under weak acoustic constraint

The phrase “collapses into NLP” is operationally useful if stated precisely.

It does not mean the model ceases to be multimodal internally. It means that once the audio channel stops strongly constraining the output, the observable behavior becomes dominated by language continuation rather than acoustic evidence. At that boundary, the system acts less like a measurement instrument and more like a conditional text generator.

The decisive failure is not that the model uses language priors. Every modern recognizer does. The failure is that it may not disclose when those priors have overtaken the evidence.

## Repercussions for machine-learning evaluation

### The benchmark target must change

The original benchmark focused on whether speaker overlap increases error. That is too weak. The revised benchmark must detect when the model changes task without declaring the change.

The primary event of interest becomes:

> a transition from acoustically constrained decoding to linguistically plausible generation without an explicit abstention, provenance marker, or confidence boundary

This event should be measured independently of word error rate.

### Current-event output becomes a contamination detector

A recent named event can function as a forensic marker. If a model outputs facts that occurred after the source recordings were created, then at least one of the following must be true:

- the recordings contain later material and their dates are wrong;
- the model had external current information;
- the application supplied current context;
- the output was generated after the alleged experiment;
- or the chain of custody is incomplete.

Temporal facts therefore become powerful provenance tests. Every experimental artifact should record:

- source recording creation time;
- model inference time;
- model release and knowledge dates where known;
- network access state;
- retrieval state;
- prompt and conversation history;
- application version;
- and exact raw output.

### Model identity is no longer enough

Naming the model does not identify the system under test. The evaluated object is the complete inference pipeline:

- client application;
- prompt assembly;
- context window;
- retrieval tools;
- speech front end;
- decoder;
- post-processor;
- safety layer;
- and rendering layer.

A model can appear to hallucinate when the actual cause is context injection, hidden retrieval, transcript repair, or interface rewriting.

### Hidden context becomes an experimental variable

The conversation preceding the audio may contain the exact vocabulary, geopolitical framing, or narrative cadence that appears in the output. A valid study must test at least four context conditions:

1. fresh session with no prior text;
2. neutral prior conversation;
3. semantically related prior conversation;
4. adversarial prior conversation containing likely completions.

The difference among these conditions measures context contamination directly.

### The system needs provenance-bearing tokens or spans

A production transcription system should not return a single undifferentiated string. It should return spans with explicit origin labels, such as:

- acoustic-high-confidence;
- acoustic-low-confidence;
- inferred;
- retrieved;
- context-completed;
- or unsupported.

If the system cannot generate these labels internally, a second verifier should estimate them externally.

## Repercussions for the concept of hallucination

The term “hallucination” becomes insufficient unless subdivided.

The observed output may fall into one of several distinct classes:

### Acoustically unsupported but factually true

The model produces a true statement that is not present in the audio. This is still a transcription failure even though the statement is factually correct.

### Acoustically unsupported and contextually imported

The model copies or transforms information from the conversation, retrieval layer, or system prompt.

### Cross-source recombination

The model combines fragments from different speakers into a proposition supported by no single source.

### Fabricated but plausible

The model produces fluent content unsupported by both the audio and external reality.

### Interface substitution

The displayed text was generated by a later processing stage and is not the raw recognizer output.

These categories have different causes and different mitigations. Treating all of them as one hallucination rate would obscure the actual system failure.

## Repercussions for safety and geopolitical information

The content domain makes the failure more serious.

A model that silently converts uncertain audio into fluent geopolitical reporting can:

- create false intelligence;
- attribute military action to the wrong actor;
- manufacture escalation signals;
- distort diplomatic statements;
- produce fabricated casualty or infrastructure reports;
- and amplify conflict narratives faster than human verification can occur.

The danger is not limited to falsehood. A true but acoustically unsupported statement can still be harmful because it is presented under a false chain of custody. In intelligence, journalism, law, and incident response, source provenance is part of the truth claim.

A transcript saying “the Houthis said X” implies that X was heard in the source recording. If X instead came from current news context, the words may be factually accurate while the evidentiary representation is false.

That distinction is critical.

## Repercussions for training-data claims

The observation does not, by itself, prove that the model was trained on the event or that the user’s experiment trained the model in real time.

It does prove that an evaluator cannot infer training provenance from fluent output alone.

A current-event completion may come from:

- retrieval;
- conversation context;
- recent model training;
- cached application data;
- a hidden tool call;
- or a human-authored template.

Therefore, claims about training must be separated from claims about inference. The evidence required to establish training influence is much stronger than the evidence required to establish contextual use.

The experiment should not ask only, “Did the model know this?” It should ask, “Which channel supplied this information, and can the system prove it?”

## Repercussions for HDAR

This observation directly supports the need for HDAR-style provenance infrastructure.

The failure is not merely a bad transcript. It is an unprovable state transition.

The missing chain is:

> audio stems → deterministic mixture → submitted request → complete context → tool state → model response → post-processing → displayed transcript

Every arrow must be recorded and hashed.

A valid HDAR evidence capsule for this experiment should contain:

- every original audio stem;
- verified human reference transcript for each stem;
- source timestamps and hashes;
- mixer code and exact FFmpeg filter graph;
- output mixture and hash;
- complete request payload;
- full prior conversation context;
- model and application identifiers;
- network and retrieval configuration;
- raw response before formatting;
- displayed response after formatting;
- annotation decisions;
- and a signed manifest linking the complete lineage.

Without that chain, the experiment can reveal a failure but cannot localize it.

## Revised hypotheses

The original attention-dispersion hypothesis should be demoted to one candidate mechanism among several.

The revised preregistered hypotheses are:

**H1 — Acoustic degradation:** Increasing overlap and reducing target-to-interference ratio increase conventional recognition error.

**H2 — Language-prior takeover:** Under weak acoustic evidence, the proportion of fluent output unsupported by the audio increases.

**H3 — Context contamination:** Related prior textual context increases the probability that unsupported output reflects that context.

**H4 — Current-event importation:** Models or applications with retrieval or recent knowledge produce more factually current but acoustically unsupported output than isolated offline recognizers.

**H5 — Undeclared task transition:** Some systems shift from transcription to summarization or language completion without exposing the transition to the user.

**H6 — Provenance intervention:** Span-level provenance labels and abstention reduce the rate at which unsupported output is accepted as transcription.

## Revised experimental design

The next experiment must use the same audio mixture under multiple information environments.

### Audio conditions

- one clean source;
- two, four, eight, and sixteen source mixtures;
- controlled overlap ratios;
- controlled target-to-interference ratios;
- intelligible speech, reversed speech, and speech-shaped noise controls.

### Context conditions

- empty session;
- unrelated conversation;
- conversation containing geopolitical vocabulary;
- conversation containing the exact event;
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
- and all metadata required to reproduce the result.

### Required classifications

Every output span must be labeled as one of:

- supported by target audio;
- supported by another source audio;
- supported by multiple audio sources;
- supported only by prior text context;
- supported only by external retrieval;
- factually true but acoustically unsupported;
- factually false and acoustically unsupported;
- ambiguous;
- or nonlexical.

### Primary endpoint

The primary endpoint is not WER.

It is the rate of fluent, meaningful spans that the interface presents as transcription even though they are unsupported by every source recording.

### Secondary endpoint

The most revealing secondary endpoint is provenance substitution:

> the fraction of output whose factual content is externally accurate but whose claimed source is false

This category captures the exact danger exposed by the geopolitical passage.

## Corrected conclusion

The observation does not prove that overlapping audio mechanically randomizes attention. It does something more valuable: it reveals that a multimodal system under uncertain acoustic conditions may produce a coherent, current, externally verifiable narrative whose relationship to the audio is unknown.

That behavior collapses the practical boundary between transcription and language generation.

The model may remain multimodal internally, but the user receives an NLP product disguised as an acoustic measurement. Once that happens, factual accuracy is no longer sufficient. The system must prove where each claim came from.

The research program must therefore move from hallucination detection to provenance enforcement.

The question is no longer only:

> Did the model say something that was not spoken?

It is:

> When the audio stopped constraining the answer, what information source took control, why was that transition hidden, and can the complete lineage be independently verified?

That is the experiment’s strongest consequence, and it is directly aligned with HDAR’s core purpose: preserving a verifiable chain from input state to model output so that fluent language cannot substitute for evidence.