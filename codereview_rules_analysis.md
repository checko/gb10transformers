# Code Review Rules Analysis

This document analyzes the existing code review rules extracted from `ai_review.py`. The goal is to evaluate their relevance for a modern, general-purpose AI code review tool (`codereview.py`) and identify which ones should be kept, updated, or removed.

## Scoring Legend
- **✅ GOOD**: Essential, universal rule. Keep as is.
- **⚠️ UPDATE**: Valid concept but needs modification (e.g., remove specific company names).
- **🚫 REMOVE**: Irrelevant, too specific (e.g., legacy hardware), or obsolete.
- **🤔 OPTIONAL**: Good for specific domains (e.g., Android, Embedded) but shouldn't be global defaults.

---

## PART 1: Header Rules (Strict Mode)

These rules currently enforce specific corporate policies.

| Rule ID | Name | Score | Analysis / Recommendation |
| :--- | :--- | :--- | :--- |
| **[HEADER-1]** | **SPDX-License-Identifier** | **✅ GOOD** | Standard practice for open source and proprietary compliance. **Keep.** |
| **[HEADER-2]** | **Copyright** | **⚠️ UPDATE** | Currently hardcodes "RoyalTek Co., Ltd.". **Action**: Make the company name configurable or generic. Keep the date logic. |
| **[HEADER-3]** | **Author** | **⚠️ UPDATE** | Enforces `@royaltek.com` email domain. **Action**: Remove domain restriction or make it configurable. |

---

## PART 2: Risk Analysis Rules

### 🔴 CRITICAL (Security & Stability)

| Rule ID | Name | Score | Analysis / Recommendation |
| :--- | :--- | :--- | :--- |
| **[CRITICAL-1]** | Memory Management | **✅ GOOD** | Vital for C/C++. Less relevant for Python but good to have for extensions. |
| **[CRITICAL-2]** | File Operations | **✅ GOOD** | Universal best practice. |
| **[CRITICAL-3]** | Race Conditions | **✅ GOOD** | Critical for all multi-threaded code. |
| **[CRITICAL-4]** | Deadlocks | **✅ GOOD** | Critical for concurrency. |
| **[CRITICAL-5]** | Thread Safety | **✅ GOOD** | Critical. |
| **[CRITICAL-6]** | Loops (Infinite) | **✅ GOOD** | Universal coding standard. |
| **[CRITICAL-7]** | Unsafe Functions | **✅ GOOD** | `strcpy` and SQL injection are classic vulnerabilities. |
| **[CRITICAL-8]** | Encryption | **✅ GOOD** | Security best practice. |
| **[CRITICAL-9]** | Hard-coding | **✅ GOOD** | No secrets in code. Essential. |
| **[CRITICAL-10]** | Input Validation | **✅ GOOD** | Security baseline. |
| **[CRITICAL-11]** | Security Measures | **✅ GOOD** | Vague but acceptable as a catch-all. |
| **[CRITICAL-12]** | Stability | **✅ GOOD** | "Software must not crash" is a bit obvious, but fine. |
| **[CRITICAL-13]** | Android/UI Thread | **🤔 OPTIONAL** | Specific to Android/GUI dev. Mark as "UI-Only" or remove for backend projects. |

### 🟠 HIGH (Performance & Error Handling)

| Rule ID | Name | Score | Analysis / Recommendation |
| :--- | :--- | :--- | :--- |
| **[HIGH-1]** | Global Variables | **✅ GOOD** | Standard best practice. |
| **[HIGH-2]** | Comms Timeout | **✅ GOOD** | Good distributed systems practice. |
| **[HIGH-3]** | Exceptions | **✅ GOOD** | Resource cleanup is vital. |
| **[HIGH-4]** | Initialization | **✅ GOOD** | Basic hygiene. |
| **[HIGH-5]** | Resource Mgmt | **✅ GOOD** | Closing files/sockets is essential. |
| **[HIGH-6]** | Input Checks | **✅ GOOD** | Defensive programming. |
| **[HIGH-7]** | Security Logging | **✅ GOOD** | Audit trails are important. |
| **[HIGH-8]** | Performance UI | **🤔 OPTIONAL** | UI specific. |
| **[HIGH-9]** | Resource GUI | **🤔 OPTIONAL** | UI specific. |
| **[HIGH-10]** | Recursion | **🤔 OPTIONAL** | "Disallow recursion" is a strict embedded/safety-critical rule. Overkill for general software. **Update**: Warn on deep recursion instead of ban. |
| **[HIGH-11]** | UART Protocol | **🚫 REMOVE** | Too specific (Embedded/Hardware). |
| **[HIGH-12]** | eMMC Storage | **🚫 REMOVE** | Too specific (Embedded/Hardware). |
| **[HIGH-13]** | Static Analysis | **✅ GOOD** | General quality rule. |

### 🟡 MEDIUM (Maintainability)

| Rule ID | Name | Score | Analysis / Recommendation |
| :--- | :--- | :--- | :--- |
| **[MEDIUM-1]** | Comments | **✅ GOOD** | Standard. |
| **[MEDIUM-2]** | Magic Numbers | **✅ GOOD** | Standard. |
| **[MEDIUM-3]** | Complexity | **✅ GOOD** | Cyclomatic complexity check. |
| **[MEDIUM-4]** | Control Flow | **✅ GOOD** | Switch defaults/else cases. |
| **[MEDIUM-5]** | Android Activity | **🚫 REMOVE** | Too specific (Legacy Android). |
| **[MEDIUM-6]** | Audio Quality | **🚫 REMOVE** | Too specific (Audio processing). |
| **[MEDIUM-7]** | Testing | **✅ GOOD** | Encourages test coverage. |
| **[MEDIUM-8]** | Process | **🚫 REMOVE** | "Code review ensures quality" is a meta-statement, not a checkable code rule. |

### 🟢 LOW (Style)

| Rule ID | Name | Score | Analysis / Recommendation |
| :--- | :--- | :--- | :--- |
| **[LOW-1]** | Naming (CamelCase) | **⚠️ UPDATE** | Python uses `snake_case`. C#/Java use `CamelCase`. Rule should be language-aware or generic "Standard Naming Conventions". |
| **[LOW-2]** | Constants | **✅ GOOD** | `UPPER_CASE` is standard across most languages. |
| **[LOW-3]** | File Structure | **✅ GOOD** | One class per file is good practice. |
| **[LOW-4]** | UI Layout | **🤔 OPTIONAL** | UI specific. |
| **[LOW-5]** | UI Layout | **🤔 OPTIONAL** | UI specific. |

---

## Summary of Proposed Changes for `codereview.py`

1.  **Remove Company Specifics**: Strip "RoyalTek" and specific email domains. Replace with placeholders or generic checks.
2.  **Remove Legacy/Embedded Rules**: Drop UART, eMMC, Audio, and specific Android legacy rules to make the tool general-purpose.
3.  **Language Awareness**: Adjust naming convention rules to respect the target language (e.g., Python vs Java).
4.  **UI Separation**: Group UI rules into a separate optional category or prompt injection.
