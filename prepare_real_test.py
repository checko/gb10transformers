
import os

def prepare_real_test():
    files = ['codereview.py', 'ai_review.py', 'llmchat.py', 'check_gpu.py', 'envcheck.py']
    combined_content = []
    
    # Header Injection (Missing headers for test)
    # We purposefully do NOT add SPDX/Copyright here to trigger [HEADER-X] warnings.
    
    # 1. Add Global Variable / Race Condition at top
    combined_content.append("# --- INJECTED BUG: GLOBAL VARIABLE ---")
    combined_content.append("GLOBAL_REQUEST_COUNTER = 0")
    combined_content.append("def unsafe_increment():")
    combined_content.append("    global GLOBAL_REQUEST_COUNTER")
    combined_content.append("    # Race condition here")
    combined_content.append("    temp = GLOBAL_REQUEST_COUNTER")
    combined_content.append("    GLOBAL_REQUEST_COUNTER = temp + 1")
    combined_content.append("")

    for fname in files:
        if os.path.exists(fname):
            with open(fname, 'r') as f:
                content = f.read()
                # Strip existing shebangs and headers to make it one file
                lines = content.splitlines()
                for line in lines:
                    if line.startswith("#!") or "Copyright" in line or "SPDX" in line:
                        continue
                    combined_content.append(line)
                combined_content.append("")
                combined_content.append(f"# --- END OF {fname} ---")
                combined_content.append("")

    # 2. Inject Hard-coded Secret in the middle
    secret_injection_index = len(combined_content) // 3
    combined_content.insert(secret_injection_index, "    # --- INJECTED BUG: SECRET ---")
    combined_content.insert(secret_injection_index + 1, "    AWS_SECRET_KEY = 'AKIAIMNOVALIDKEY12345'")
    
    # 3. Inject SQL Injection near the end
    combined_content.append("")
    combined_content.append("# --- INJECTED BUG: SQL INJECTION ---")
    combined_content.append("def get_user_logs(username):")
    combined_content.append("    import sqlite3")
    combined_content.append("    conn = sqlite3.connect('logs.db')")
    combined_content.append("    cursor = conn.cursor()")
    combined_content.append("    # Unsafe query construction")
    combined_content.append('    query = "SELECT * FROM access_logs WHERE user = \'" + username + "\'"')
    combined_content.append("    cursor.execute(query)")
    combined_content.append("    return cursor.fetchall()")

    # 4. Inject Resource Leak
    combined_content.append("")
    combined_content.append("# --- INJECTED BUG: RESOURCE LEAK ---")
    combined_content.append("def load_config_unsafe(path):")
    combined_content.append("    f = open(path, 'r')")
    combined_content.append("    return f.read()")
    combined_content.append("    # File not closed")

    # Duplicate content if needed to reach > 1000 lines
    final_lines = []
    while len(final_lines) < 1200:
        final_lines.extend(combined_content)
        final_lines.append("# --- REPEATED CONTENT FOR VOLUME ---")
    
    out_path = "test_review/large_real_python.py"
    with open(out_path, 'w') as f:
        f.write("\n".join(final_lines))
        
    print(f"Generated {out_path} with {len(final_lines)} lines.")

if __name__ == "__main__":
    prepare_real_test()
