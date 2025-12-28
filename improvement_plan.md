# Code Review Tool Improvement Plan

Based on deep research into Large Language Model (LLM) behavior for code analysis and the current state of `codereview.py`, here are the proposed strategies to ensure full compliance and accuracy across all supported languages.

## 1. Advanced Prompt Engineering

### A. Language-Specific Rule Filtering (Dynamic System Prompts)
**Current Issue:** The tool sends *all* rules (C++, Python, Java) to the model for *every* file. This confuses the model (e.g., checking for `malloc` in Python).
**Proposal:**
*   Create a rule registry mapping languages to specific rules.
*   Dynamically construct the `system_prompt` based on the file extension.
*   **Benefit:** Reduces noise, allows the model to focus on relevant checks.

### B. Few-Shot Prompting (In-Context Learning)
**Current Issue:** The model is told to output a diff but given no examples.
**Proposal:**
*   Include 1-2 concise examples of "Input Code" -> "Correct Unified Diff Output" in the system prompt.
*   Show an example of a "Header Check" and a "Logic Check".
*   **Benefit:** Drastically improves adherence to the Unified Diff format and comment style.

### C. Chain-of-Thought (CoT) & Structured Intermediate Output
**Current Issue:** asking for a raw diff immediately is a "hard" task that requires simultaneously finding bugs and counting line numbers.
**Proposal:**
*   **Option 1 (Hidden CoT):** Instruct the model to "Think before you act" by outputting a reasoning block before the diff markers. (e.g., `<!-- ANALYSIS: Found global var at line 10 -->`).
*   **Option 2 (Two-Pass System):**
    *   **Pass 1:** Ask for a JSON output: `[{"line": 10, "issue": "Global Var", "severity": "HIGH-1"}]`.
    *   **Pass 2:** Use a deterministic Python function (or a very cheap LLM call) to convert that JSON into the Unified Diff.
*   **Benefit:** Decouples "finding the bug" from "formatting the output", reducing hallucinations and formatting errors.

## 2. Context & Chunking Strategy

### A. Sliding Window with Overlap
**Current Issue:** The file is sliced strictly at 500 lines. A bug spanning lines 499-501 (e.g., an unclosed function) might be missed.
**Proposal:**
*   Implement `overlap=50` lines.
*   When reviewing lines 500-1000, include lines 450-500 as "Context (Do not review)".
*   **Benefit:** Captures cross-chunk context.

### B. Global Context Injection
**Current Issue:** The model reviews line 2000 without knowing what libraries were imported at line 1.
**Proposal:**
*   Always prepend the first 50 lines of the file (imports, globals) to *every* chunk prompt.
*   **Benefit:** Reduces "undefined variable" false positives and helps with context-aware checks (e.g., "Is `numpy` imported?").

## 3. Model Parameters & Configuration

### A. Parameter Tuning
**Current Issue:** `temperature=0.2` is safe but might be too rigid for "reasoning" about complex logic.
**Proposal:**
*   Experiment with `temperature=0.3` or `0.4` combined with a strict `repetition_penalty=1.1`.
*   Increase `max_new_tokens` if we adopt Chain-of-Thought.

### B. Self-Correction Loop
**Current Issue:** If the model outputs a broken diff (e.g., wrong line count), the tool just saves it, resulting in a corrupt patch.
**Proposal:**
*   Implement a validator that attempts to apply the patch in memory (or checks the syntax).
*   If invalid, feed the error back to the model: "Your diff was invalid: [Error]. Please regenerate."
*   **Benefit:** Guarantees that the output `.diff` files are valid.

## 4. Implementation Roadmap

1.  **Refactor `codereview.py`**: Separate `Reviewer` logic from `PromptBuilder`.
2.  **Implement Rule Registry**: Define specific dictionaries for Python, C++, Java, JS.
3.  **Update `review_chunk`**: Add logic to build dynamic prompts with examples.
4.  **Test**: Run against `test_review/` benchmark files.

## Recommendation
I recommend starting with **1.A (Language-Specific Rules)** and **1.B (Few-Shot Prompting)** as they offer the highest ROI for accuracy. **2.A (Sliding Window)** is critical for large files.
