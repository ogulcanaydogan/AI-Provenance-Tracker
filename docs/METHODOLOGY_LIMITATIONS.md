# Methodology Limitations

## Scope
AI Provenance Tracker provides probabilistic AI-likelihood scoring and provenance signals. It does not provide certainty or legal-grade proof.

## Core constraints
1. False positives and false negatives are expected in every modality.
2. Confidence scores are model outputs, not calibrated guarantees for all domains.
3. Source attribution is currently heuristic and can fail under style transfer or prompt obfuscation.
4. C2PA verification depends on manifest availability and valid signatures.
5. External provider adapters can fail due to timeout, schema drift, or service outages.

## Dataset and evaluation constraints
1. Public benchmark sampling is limited and not globally representative.
2. Domain/language distribution is incomplete and can bias aggregate metrics.
3. Tamper tests cover a bounded set of transforms and do not exhaust adversarial attacks.
4. Audio/video benchmarks are experimental and lower-confidence by design.

## Operational guidance
1. Use this system as decision support, not as a single-source adjudication tool.
2. Combine detector output with human review and independent evidence.
3. For high-stakes workflows, require multi-signal corroboration and documented escalation paths.

## Reporting guidance
When publishing or presenting results, include:
- benchmark version and dataset hash
- run command and commit SHA
- provider availability matrix
- explicit limitation statement that confidence does not imply certainty
