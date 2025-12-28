import re

def analyze_large_test():
    with open('test_review/large_real_python.py', 'r') as f:
        original = f.read()
    
    with open('test_review/large_real_python.py.diff', 'r') as f:
        diff_lines = f.readlines()
    
    bug_pattern = re.compile(r'# --- INJECTED BUG: (.*?) ---')
    bugs_in_original = bug_pattern.findall(original)
    print(f"Bugs injected in original: {len(bugs_in_original)}")
    
    # Track which bugs are covered
    # A bug is covered if a line containing "INJECTED BUG" is followed within a few lines by a line starting with "+" and containing "REVIEW"
    
    bugs_found_in_diff = 0
    bugs_covered_in_diff = 0
    
    for i, line in enumerate(diff_lines):
        if "# --- INJECTED BUG:" in line:
            bugs_found_in_diff += 1
            # Search forward for a review
            covered = False
            for j in range(i + 1, min(i + 10, len(diff_lines))):
                if diff_lines[j].startswith("+") and "REVIEW:" in diff_lines[j]:
                    covered = True
                    break
            if covered:
                bugs_covered_in_diff += 1
            else:
                # Check backward too, just in case
                for j in range(max(0, i - 5), i):
                    if diff_lines[j].startswith("+") and "REVIEW:" in diff_lines[j]:
                        covered = True
                        break
                if covered:
                    bugs_covered_in_diff += 1

    print(f"Bugs found in diff context: {bugs_found_in_diff}")
    print(f"Bugs covered by REVIEW in diff: {bugs_covered_in_diff}")

if __name__ == "__main__":
    analyze_large_test()
