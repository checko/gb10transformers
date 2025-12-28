from codereview import CodeReviewer
from pathlib import Path

reviewer = CodeReviewer()
print(f"Suffix for bad_python.py: {Path('test_review/bad_python.py').suffix}")
print(f"Prefix for .py: '{reviewer.get_comment_style('.py')}'")
