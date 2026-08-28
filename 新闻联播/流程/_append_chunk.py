import sys

target = sys.argv[1]
chunk_file = sys.argv[2]

with open(chunk_file, 'r', encoding='utf-8') as f:
    content = f.read()

with open(target, 'a', encoding='utf-8') as f:
    f.write(content)

print(f"Appended {len(content)} chars to {target}")