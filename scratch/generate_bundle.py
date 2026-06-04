import os

FILES = [
    "config.py",
    "operators.py",
    "local_search.py",
    "pool.py",
    "rl.py",
    "heuristics.py",
    "solvers.py"
]

src_dir = "src/vrptw"
output_file = "/Users/thundercock2/.gemini/antigravity/brain/a2f667cd-3d6f-4d5b-87ad-a5f864490fc1/source_bundle.md"

with open(output_file, "w") as out:
    out.write("# Source Code Bundle\n\n")
    out.write("This bundle contains the following files concatenated for review:\n")
    for f in FILES:
        out.write(f"- `{f}`\n")
    out.write("\n---\n\n")
    
    for f in FILES:
        path = os.path.join(src_dir, f)
        out.write(f"## FILE: {f}\n\n")
        out.write("```python\n")
        with open(path, "r") as inf:
            out.write(inf.read())
        out.write("\n```\n\n---\n\n")

print("Generated source bundle successfully!")
