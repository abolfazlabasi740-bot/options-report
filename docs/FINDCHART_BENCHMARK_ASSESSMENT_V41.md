# FindChart Benchmark Assessment — V4.1.1

## Purpose

This document defines the boundary for any reference to FindChart in the OptimusAI project. FindChart may be used as a UX/distribution benchmark only. Its binary screening logic, qualitative price-action interpretation and text-based symbol matching are not active analytical dependencies.

## Problem

Unqualified use of FindChart terminology in technical documents can mix two different paradigms:

1. Binary/technical screening for underlying equities.
2. Continuous, evidence-gated derivatives ranking for OptimusAI.

These paradigms must remain technically separated.

## Compliant / usable reference

### Distribution UX

Compact information cards (Micro-Cards), staged message delivery and low-cognitive-load presentation may be used as UX references for the Distribution Layer, including Bale formatting.

### Underlying context

Underlying-equity context may be displayed beside an option contract as reference information when directly evidenced by the TSETMC source boundary. Such context is informational only and is not automatically converted into a scoring variable.

## Non-compliant / excluded logic

### Binary filtering

FindChart-style true/false filters must not replace, gate, weight or modify the Six-Block continuous scoring distribution.

### Qualitative signaling

Buy/Sell labels, discretionary price-action conclusions and unsupported support/resistance levels are outside the analytical core.

### Identity inference

Textual symbol matching is not an accepted identity mechanism. Option/underlying linkage must use explicit, verified instrument identifiers supplied by the TSETMC source boundary.

## System boundary statement

> The structure and message-card presentation of FindChart are accepted solely as a UX/distribution-layer reference; its binary filtering, direct signaling and technical inference logic are completely out of scope for the analytical core because they are not compatible with the project's continuous, evidence-gated derivatives architecture and data-governance rules.

## Governance

FindChart must not be added as:
- an active data source;
- a reconciliation source;
- a fallback source for missing TSETMC fields;
- a scoring input;
- an identity resolver;
- a signal generator.

Any future benchmark use must be documented as UX/reference evidence and must not alter the TSETMC-only source-of-truth boundary.

## Current status

- Active source of truth: TSETMC.
- External comparison source: none.
- FindChart runtime dependency: none.
- Six-Block scoring: OFF until the TSETMC evidence gate closes.
- Buy/Sell signaling: OFF.
