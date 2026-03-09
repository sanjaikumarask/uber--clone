import os

def fix_coverage_paths():
    filepath = "backend/coverage.xml"
    if not os.path.exists(filepath):
        print(f"Error: {filepath} not found.")
        return

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Reads backend/coverage.xml
    # 2. Replaces <source>/app</source> with <source>.</source>
    content = content.replace('<source>/app</source>', '<source>.</source>')

    # Keep track of filename occurrences for validation
    fixed_count = content.count('filename="/app/')
    
    # Optional logic if coverage files just have 'apps/' instead of '/app/apps/'
    if fixed_count == 0 and content.count('filename="apps/') > 0:
        fixed_count = content.count('filename="apps/') + content.count('filename="consumers/')
        content = content.replace('filename="apps/', 'filename="backend/apps/')
        content = content.replace('filename="consumers/', 'filename="backend/consumers/')
    else:
        # 3. Replaces filename="/app/ with filename="backend/
        content = content.replace('filename="/app/', 'filename="backend/')

    # 4. Replaces all other /app/ occurrences with backend/
    content = content.replace('/app/', 'backend/')

    # 5. Validates that at least 150 filename entries were fixed
    if fixed_count >= 150:
        print(f"Validation passed: At least 150 paths were fixed ({fixed_count} actual).")
    else:
        print(f"Warning: Only {fixed_count} occurrences of filename were fixed. Expected >= 150.")

    # 6. Saves the fixed file back
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    # 7. Prints a summary
    print(f"Fixed {fixed_count} paths successfully")

if __name__ == "__main__":
    fix_coverage_paths()
