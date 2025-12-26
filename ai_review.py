#!/usr/bin/env python3

import os
import subprocess
import requests
import re
from datetime import datetime

BACKEND = os.getenv("BACKEND", "ollama")
STRICT_AI_REVIEW = os.getenv("STRICT_AI_REVIEW", "false").lower() == "true"
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://192.168.145.70:11434")
OLLAMA_MODE = os.getenv("OLLAMA_MODE", "generate").lower()  # chat or generate
HF_API_URL = os.getenv("HF_API_URL", "http://192.168.145.70:8000/generate")
TARGET_EXTENSIONS = [".py", ".c", ".cpp", ".h", ".hpp", ".cc", ".hh", ".kt", ".java"]
CURRENT_YEAR = datetime.now().year

if BACKEND == "hf":
    MODEL = os.getenv("HF_MODEL", "mistralai/Mistral-7B-Instruct-v0.1")
else:
    MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:120b")

def get_changed_files():
    """
    Compare the current HEAD with the target branch of the MR and retrieve the list of changed files
    """
    import json

    mr_iid = os.getenv("CI_MERGE_REQUEST_IID")
    project_id = os.getenv("CI_PROJECT_ID")
    api_base = os.getenv("CI_API_V4_URL", "https://gitlab.com/api/v4")
    token = os.getenv("GITLAB_TOKEN")

    if not mr_iid or not project_id or not token:
        print("⚠️ Unable to retrieve the MR target branch: missing CI_MERGE_REQUEST_IID / CI_PROJECT_ID / GITLAB_TOKEN")
        return []

    try:
        # Fetch Merge Request information
        url = f"{api_base}/projects/{project_id}/merge_requests/{mr_iid}"
        headers = {"PRIVATE-TOKEN": token}
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()

        mr_data = resp.json()
        target_branch = mr_data.get("target_branch", "main")

        print(f"🔍  MR #{mr_iid} target branch: {target_branch}")

        # Ensure the latest target branch data has been retrieved
        subprocess.run(["git", "fetch", "origin", target_branch], check=True)

        #  Compare differences
        result = subprocess.run(
            ["git", "diff", "--name-only", f"origin/{target_branch}...HEAD"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True
        )

        changed_files = result.stdout.strip().splitlines()

        if changed_files:
            print(f"✅ Changed files detected vs origin/{target_branch}：{changed_files}")
        else:
            print(f"⚠️ No changed files detected vs origin/{target_branch}")

        return [
            f for f in changed_files
            if os.path.isfile(f)
            and f.endswith(tuple(TARGET_EXTENSIONS))
            and not f.startswith(".gitlab/")
        ]

    except Exception as e:
        print(f"❌ Error during dynamic diff vs target branch: {e}")
        return []


def extract_code_from_file(file_path):
    """
    Extract code from file
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = []
            for line in f:
                lines.append(line)
            return ''.join(lines)
    except Exception as e:
        return f"[❌ Unable to read file {file_path}: {e}]"

def generate_code_review_prompt(file_code, filename, current_year):
    """
    生成同時包含 Header 檢查與程式碼品質審查的 Prompt (Sandwich Structure)
    """

    top_instructions = f"""
# Role
你是一位**資深軟體架構師**與**嚴格的合規稽核員**。
你的目標是審查檔案：「{filename}」。

# ⛔ 核心格式限制 (CRITICAL OUTPUT RULES)
1. **禁止使用 Markdown 表格**：絕對不要輸出 `| 欄位 | 欄位 |` 這種格式。
2. **純文字排版**：請使用縮排、列表與 ASCII 分隔線 (例如 `===`, `---`) 來呈現報告。
3. **嚴格引用**：Header 檢查必須逐字引用，若程式碼中沒有，就寫「未出現在程式碼中」。
4. **只能引用實際出現在下方程式碼中的內容** - 必須逐字逐句複製程式碼中的實際文字。
5. **嚴禁腦補、推測、幻想或假設任何內容** - 即使你認為「應該」有某個內容，如果程式碼中沒有，就必須回報「未出現在程式碼中」。
6. **嚴禁使用模板或經驗值** - 不要根據你的訓練資料或過往經驗來「猜測」應該有什麼內容。
7. **必須逐字檢查** - 在引用程式碼時，必須完全照抄，包括大小寫、標點符號、空格 (但請依照指示去除行號前綴)。
8. **Risk ID 必須對應檢查表** - Risk ID 必須包含方括號 (例如 `[MEDIUM-2]`)，並完全對應下方檢查表中的標籤。
9. **Location 格式與單一性** - Location 欄位必須填寫 **Input Code 左側的 4 碼行號** (例如 `0015`)，禁止自行簡化為 `15`。若同一個風險出現在多行，**禁止合併行號** (例如禁止寫 `0010, 0025`)，必須分開列出不同區塊。
10. **嚴禁輸出空內容區塊** - 如果某個風險等級沒有發現問題，**絕對不要**輸出包含 `None`、`N/A` 或空值的區塊。只有在確實發現問題且能填寫具體 Location/Problem/Fix 時，才能生成區塊。

---

# PART 1: Header 格式規範 (Strict Mode)

請檢查程式碼開頭的註解區塊，必須**完全符合**以下規定：

**⚠️ 忽略註解符號與空格規則**：
1. 檢查時請**忽略**行首的常見註解符號（如 `//`, `/*`, `*`, `#`）。
2. 請**忽略**符號與文字之間的多餘空格 (例如 `//Copyright` 與 `//   Copyright` 視為相同)。
3. **重點**：我們只檢查「有效的文字內容」。

## 1. SPDX-License-Identifier
- 標準格式：`SPDX-License-Identifier: <授權名稱>`
- 判定規則：
  - ❌ **FAIL (缺行)**：程式碼中完全找不到此行，回報「未出現在程式碼中」。
  - ❌ **FAIL (內容為空)**：該行存在，但冒號 `:` 後面沒有內容 (例如僅寫了 `SPDX-License-Identifier:` )。
  - ✅ **PASS**：該行存在，且冒號後有具體的授權名稱 (例如 `Apache-2.0` 或 `GPL-3.0`)。

## 2. Copyright
- 標準格式：`Copyright (c) <年份資訊>, RoyalTek Co., Ltd.`
- 判定規則：
  - ❌ **FAIL (缺行)**：程式碼中完全找不到此行，回報「未出現在程式碼中」。
  - ❌ **FAIL (公司名稱錯誤)**：必須逐字精確匹配 `RoyalTek Co., Ltd.`。
    - 注意大小寫：`RoyalTek` (T 必須大寫)。
    - 注意標點：`Co., Ltd.` (必須有逗號與句點)。
  - ❌ **FAIL (年份邏輯錯誤)**：
    - 若為單一年份 (e.g., `2025`)：必須 <= {current_year}。
    - 若為年份範圍 (e.g., `2020-2025`)：**結束年份** 必須 <= {current_year}。
    - 若年份大於 {current_year} (未來時間)，視為 FAIL。
  - ✅ **PASS**：該行存在，且公司名稱 (RoyalTek Co., Ltd.) 完全正確，年份亦符合邏輯。

## 3. Author
- 標準格式：`Author: Name <Email>`
- 判定規則：
  - ❌ **FAIL (缺行)**：程式碼中完全找不到此行，回報「未出現在程式碼中」。
  - ❌ **FAIL (格式錯誤)**：Email **必須**被角括號 `< >` 包圍，但 Name (姓名) **不可**包圍。
    - 錯誤範例：`Author: KJ Chang (KJ.Chang@royaltek.com)` (Email 用了圓括號)。
    - 錯誤範例：`Author: <KJ Chang> <KJ.Chang@royaltek.com>` (Name 不該有角括號)。
    - 錯誤範例：`Author: KJ Chang KJ.Chang@royaltek.com` (Email 漏了角括號)。
  - ❌ **FAIL (網域錯誤)**：Email 必須以 `@royaltek.com` 結尾。
  - ✅ **PASS**：該行存在，格式符合 `Name <Email>` (Name 為純文字，Email 含角括號)，且 Email 以 `@royaltek.com` 結尾。

---

# PART 2: 風險與品質規範 (Risk List)

**⚠️ ID 引用規則 (IMPORTANT)**：
- **Risk ID 來源**：請**直接複製**規則列表開頭的**方括號標籤** (例如 `[CRITICAL-1]` 或 `[LOW-2]`)。
- **絕對禁止重新編號**：不管這是你發現的第幾個問題，ID 必須完全依照該規則在列表中的標籤。
- **允許並要求重複引用**：如果同一種風險在不同行數出現多次（例如多個地方都有 Magic Number），**必須分開列出**。
    - ✅ **正確**：列出兩個獨立的區塊，都使用 `Risk ID: [MEDIUM-2]`，但 `Location` 不同 (例如一個是 `0010`，另一個是 `0055`)。
    - ❌ **錯誤**：將所有行號合併在同一個區塊中（例如 `Location: 0010, 0055, 0092`）。
- **範例**：
    - 若規則寫著 `[LOW-2] Naming...`，你的報告中必須寫 `Risk ID: [LOW-2]`。
    - **錯誤範例**：`Risk ID: 2` (未包含完整標籤) 或 `Risk ID: LOW-02` (自作聰明補零)。

請根據以下列表掃描程式碼問題 (若無問題則不需列出)：

**⚠️ 重要指令 (IMPORTANT)**：
- **必須檢查完整程式碼**：無論程式碼多長，請務必從第一行檢查到最後一行。
- **不可省略**：不要因為程式碼過長而停止檢查或只檢查部分片段。
- **不可摘要**：請列出所有發現的問題，不要只列出前幾個。
- **Location 格式**：請務必使用 Input Code 左側顯示的 **4 碼數字** (例如 `0005`, `0120`)，不要自行簡化為 `5` 或 `120`。

## 🔴 [CRITICAL] (Must be fixed immediately. Causes crashes, security vulnerabilities, or hardware damage.)
[CRITICAL-1]  Memory Management: Check return values of `malloc` or `new`. Log errors and handle failures.
[CRITICAL-2]  File Operations: Check return values for file open/read/write. Log errors and notify upper layers.
[CRITICAL-3]  Concurrency - Race Conditions: Use locks or mutexes to protect shared resources.
[CRITICAL-4]  Concurrency - Deadlocks: Ensure consistent lock acquisition order and set maximum wait times.
[CRITICAL-5]  Concurrency - Thread Safety: Only use thread-safe APIs in multi-threaded environments.
[CRITICAL-6]  Loops: All loops (`while`, `for`, `goto`) must have clear entry and exit conditions to avoid infinite loops.
[CRITICAL-7]  Security - Unsafe Functions: Avoid unsafe functions like `strcpy` (C++) or SQL injection vulnerabilities (Java).
[CRITICAL-8]  Security - Encryption: Passwords and keys must be stored and transmitted encrypted.
[CRITICAL-9]  Security - Hard-coding: Do not hard-code sensitive data in source code or config files.
[CRITICAL-10] Security - Input Validation: Verify and filter all user input data.
[CRITICAL-11] Security - Measures: Ensure necessary measures to prevent data theft or tampering.
[CRITICAL-12] Stability: Software must not crash.
[CRITICAL-13] Android/UI: Ensure UI updates are ONLY performed in the UI thread.

## 🟠 [HIGH] (Potential errors, performance bottlenecks, or system instability. Strongly recommended to fix.)
[HIGH-1]  Global Variables: Avoid them. Use local variables with read/write methods.
[HIGH-2]  Error Handling - Communication: Handle timeouts/disconnections with a retry mechanism (e.g., 3 retries).
[HIGH-3]  Error Handling - Exceptions: Use `try-catch` appropriately (Java/C++) and ensure resource release.
[HIGH-4]  Initialization: Initialize all variables. Check array/memory ranges before use.
[HIGH-5]  Resource Management: Ensure files, network connections, etc., are closed after use.
[HIGH-6]  Input Checks: All functions must perform type and value checks on input data.
[HIGH-7]  Security - Logging: Log security events (errors, exceptions) with context, excluding sensitive info.
[HIGH-8]  Performance - UI: Move time-consuming tasks to background threads.
[HIGH-9]  Performance - Resources: Release GUI resources in a timely manner.
[HIGH-10] Embedded - Recursion: Disallow recursive functions (stack overflow risk).
[HIGH-11] Protocol - UART: Use checksums to ensure data completeness.
[HIGH-12] Storage - eMMC: Avoid continuous writing; write to RAM and flush on shutdown.
[HIGH-13] Quality: Fix major bugs found by static analysis tools.

## 🟡 [MEDIUM] (Improves maintainability, readability, or best practices.)
[MEDIUM-1]  Comments: Comment output, input, and key logic (`//` or `/**/`).
[MEDIUM-2]  Magic Numbers: Use meaningful variables/constants instead of hard-coded numbers.
[MEDIUM-3]  Complexity: Keep nested control structures within 3 layers. Refactor if deeper.
[MEDIUM-4]  Control Flow: `if` and `switch` statements must consider `default` or exceptions.
[MEDIUM-5]  Android: Selectively disable Activity rebuild or use ViewModel.
[MEDIUM-6]  Audio: Check quality (echo cancellation, noise reduction).
[MEDIUM-7]  Testing: Unit and integration tests to ensure correctness.
[MEDIUM-8]  Process: Code review ensures quality.

## 🟢 [LOW] (Style, formatting, and minor details.)
[LOW-1]  Naming: Class/Variables (Nouns), Functions (Verbs), CamelCase.
[LOW-2]  Naming: Constants in UPPERCASE_WITH_UNDERSCORES.
[LOW-3]  Structure: Separate `*.h`, `*.cpp`, `*.java` files per class.
[LOW-4]  UI Layout: Use appropriate layout managers, test multiple screen sizes.
[LOW-5]  UI Layout: Manage vertical and horizontal layouts.

---

# 輸出範本 (Output Template)

請**嚴格遵守**以下純文字格式回覆，不要更動結構：

==================================================
CODE REVIEW REPORT: {filename}
==================================================

>>> PART 1: HEADER CHECK RESULTS

[1] SPDX-License-Identifier
    Status: [ ✅ PASS / ❌ FAIL ]
    Found : (請複製程式碼中的實際文字，記得去除行號前綴，若無則寫 "None")
    Reason: (請說明理由)

[2] Copyright
    Status: [ ✅ PASS / ❌ FAIL ]
    Found : (請複製程式碼中的實際文字，記得去除行號前綴)
    Reason: (檢查年份是否 <= {current_year} 且拼字完全正確)

[3] Author
    Status: [ ✅ PASS / ❌ FAIL ]
    Found : (請複製程式碼中的實際文字，記得去除行號前綴)
    Reason: (檢查是否為 @royaltek.com)

--------------------------------------------------

>>> PART 2: RISK ANALYSIS

(若未發現任何問題，請輸出： "✅ No risks found.")

(針對每個發現的問題，請重複以下區塊)
**⚠️ 警告：若無發現具體問題，絕對不要輸出此區塊 (不要填寫 None)**
[SEVERITY: (請填寫等級，例如 🔴 CRITICAL)]
    Risk ID : (請填寫規則方括號中的完整標籤，例如 [LOW-2])
    Location: (請填寫 Input Code 左側的 4 碼行號，例如 0102)
    Problem : (問題描述)
    Fix     : (具體修正建議)
    -------------------------------------------

==================================================
END OF REPORT
==================================================
"""

    # Add line numbers to the code
    lines = file_code.splitlines()
    numbered_code = '\n'.join([f"{i+1:04d} | {line}" for i, line in enumerate(lines)])

    code_section = f"""
# Input Code
(The code content begins below)
↓↓↓↓↓↓↓↓↓↓
{numbered_code}
↑↑↑↑↑↑↑↑↑↑
(End of code content)
"""

    bottom_instructions = f"""
# Final Execution Instructions

你已經閱讀完檔案 "{filename}" 的所有程式碼。現在請開始執行審查：

1.  **回頭檢查 Header**：請重新檢視程式碼最上方的註解，比對 PART 1 規則。
    -   **🎯 去除行號規則**：當你引用程式碼到「Found」欄位時，必須切除行首的「數字 + 分隔線」，保留原始註解內容。
        -   Input in code:  `0002 | // Copyright (c) 2025, RoyalTek Co., Ltd.`
        -   Output in report: `// Copyright (c) 2025, RoyalTek Co., Ltd.`

2.  **掃描邏輯風險**：請重新檢視程式碼邏輯，比對 PART 2 風險列表。
    -   **Risk ID**：請直接複製規則文字開頭的方括號標籤 (例如 `[MEDIUM-2]`)。
        -   ✅ 正確範例：`Risk ID : [HIGH-5]`
        -   ❌ 錯誤範例：`Risk ID : 5` (遺漏前綴) 或 `Risk ID : [HIGH-05]` (自作聰明補零)
    -   **Location**：請務必填寫 **Input Code 左側顯示的 4 碼行號** (例如 `0444`)，**絕對不要**自己發明行號。
        -   ✅ 正確範例：`Location : 0444`
        -   ❌ 錯誤範例：`Location : 444` (遺漏前綴)

3.  **再次確認完整性**：
    -   請確認您已經檢查了**每一行程式碼**，沒有遺漏任何部分。
    -   如果程式碼很長，請確保您沒有因為長度而忽略了後面的部分。

4.  **產生報告**：
-   **禁止空區塊**：在輸出每一個 Risk 區塊前，請先確認 `Problem` 和 `Fix` 是否有實質內容。如果只是想填 `None`，請直接跳過該區塊，**絕對不要輸出**。
    -   **禁止 Markdown 表格** (不要用 `|`)。
    -   **使用純文字格式** (依照上方的 "Output Template")。
    -   **語言**：請使用繁體中文 (Traditional Chinese) 撰寫報告內容。

**Action**: 請依照範本輸出 "CODE REVIEW REPORT"：
"""

    prompt = f"{top_instructions}\n{code_section}\n{bottom_instructions}"
    return prompt.strip()

def call_ollama_api(prompt):
    try:
        if OLLAMA_MODE == "chat":
            url = f"{OLLAMA_HOST}/api/chat"
            payload = {
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False
            }
        elif OLLAMA_MODE == "generate":
            url = f"{OLLAMA_HOST}/api/generate"
            payload = {
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_ctx": 65536,  # 程式碼行數要更多要再增加，目前大約可以到6500行
                    "num_predict": -1, 
                    "temperature": 0,
                    "top_k": 20, 
                    "top_p": 0.9, 
                    "repeat_penalty": 1.05, 
                    "seed": 42
                }
            }
        else:
            return f"[❌ Invalid OLLAMA_MODE: {OLLAMA_MODE} (should be 'chat' or 'generate')]"

        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=600
        )
        response.raise_for_status()

        if OLLAMA_MODE == "chat":
            return response.json().get("message", {}).get("content", "[⚠️ No chat response from Ollama]")
        else:
            return response.json().get("response", "[⚠️ No generate response from Ollama]")

    except Exception as e:
        return f"[❌ Unable to connect to Ollama ({OLLAMA_MODE}): {e}]"

def call_hf_api(prompt):
    try:
        response = requests.post(
            HF_API_URL,
            headers={"Content-Type": "application/json"},
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=120
        )
        response.raise_for_status()
        return response.json().get("response", "[⚠️ No response content from HF API]")
    except Exception as e:
        return f"[❌ Unable to connect to HF API: {e}]"

def call_model_api(prompt):
    if BACKEND == "ollama":
        return call_ollama_api(prompt)
    elif BACKEND == "hf":
        return call_hf_api(prompt)
    else:
        return "[❌ Invalid backend specified. Use 'ollama' or 'hf']"


def parse_review_result(ai_response):
    """
    解析 AI 回覆，檢查是否有 Header 違規或風險。
    回傳一個字典，包含檢查結果。
    """
    result = {
        "header_fail": False,
        "risks": []
    }

    # 1. 檢查 Header (Part 1)
    # 同時支援有圖示或無圖示的寫法
    if re.search(r"Status:.*(FAIL|❌)", ai_response, re.IGNORECASE):
        result["header_fail"] = True

    # 2. 檢查 Risks (Part 2)
    # 忽略前面的圖示，只抓取文字等級
    risk_pattern = re.compile(r"\[SEVERITY:.*(CRITICAL|HIGH)\]")
    result["risks"] = risk_pattern.findall(ai_response)

    return result


def post_comment_to_merge_request(message):
    mr_id = os.getenv("CI_MERGE_REQUEST_IID")
    project_id = os.getenv("CI_PROJECT_ID")
    api_base = os.getenv("CI_API_V4_URL", "https://gitlab.com/api/v4")
    token = os.getenv("GITLAB_TOKEN")

    print("🔍 [DEBUG] MR ID:", mr_id)
    print("🔍 [DEBUG] Project ID:", project_id)
    print("🔍 [DEBUG] API URL:", api_base)
    print("🔍 [DEBUG] Token Present:", "Yes" if token else "No")

    if not mr_id or not project_id or not token:
        print("⚠️ Unable to comment: Missing CI_MERGE_REQUEST_IID, CI_PROJECT_ID, or GITLAB_TOKEN")
        return

    url = f"{api_base}/projects/{project_id}/merge_requests/{mr_id}/notes"
    headers = {"PRIVATE-TOKEN": token}
    data = {"body": message}

    try:
        resp = requests.post(url, headers=headers, data=data)
        if resp.status_code == 201:
            print("✅ Comment posted to Merge Request")
        else:
            print(f"❌ Failed to post comment：{resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"❌ Unable to submit comment：{e}")


def main():
    print("🔍  Starting AI code review...")
    changed_files = get_changed_files()
    
    if not changed_files:
        print("ℹ️  No changed files detected. Skipping analysis.")    
        post_comment_to_merge_request(
        "🤖 AI Code Review：No changed files detected. Skipping analysis."
        )
        return

    has_violation = False

    for filepath in changed_files:
        print(f"\n📂 Analyzing：{filepath}")
        file_code = extract_code_from_file(filepath)
        prompt = generate_code_review_prompt(file_code, filepath, CURRENT_YEAR)
        ai_response = call_model_api(prompt)

        print("🤖 AI Suggestions：")
        print(ai_response)
        print("\n" + "=" * 80)

        comment_header = f"### 🤖 AI Code Review Report：`{filepath}`"
        comment_body = f"{comment_header}\n\n```\n{ai_response}\n```"
        post_comment_to_merge_request(comment_body)

        # 解析結果
        analysis_result = parse_review_result(ai_response)

        # 如果 Header 失敗 或 Risks 列表有內容，就標記為違規
        if analysis_result["header_fail"] or analysis_result["risks"]:
            has_violation = True

    if has_violation:
        print("❌ Found violations")
        if STRICT_AI_REVIEW:
            print("🚫 Strict mode enabled. CI task marked as failed.")
            exit(1)
        else:
            print("⚠️ Non-strict mode. Suggestions provided but CI will not be blocked.")
    else:
        print("✅ All changed files comply with company policies.")


if __name__ == "__main__":
    main()
