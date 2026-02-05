import re
import os

files = [
    r"C:\Users\posne\.gemini\extensions\gemini-flow\GEMINI.md",
    r"C:\Users\posne\.gemini\extensions\gemini-flow\gemini-flow.md"
]

for file_path in files:
    print(f"--- Scanning {os.path.basename(file_path)} ---")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines):
            # Look for @ that is NOT preceded by a quote " or '
            # This is a heuristic.
            # We specifically care about package names starting with @
            
            # Find all @package/name patterns
            matches = re.finditer(r'(@[\w\-]+/[\w\-]+)', line)
            for m in matches:
                # Check if it's quoted
                start = m.start()
                end = m.end()
                # Check char before
                char_before = line[start-1] if start > 0 else ''
                # Check char after
                char_after = line[end] if end < len(line) else ''
                
                is_quoted = (char_before == '"' and char_after == '"') or (char_before == "'" and char_after == "'")
                
                if not is_quoted:
                    print(f"Line {i+1}: {line.strip()}")
                    # print(f"  Match: {m.group(0)} | Quoted: {is_quoted}")
                    
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
