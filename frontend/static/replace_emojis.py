import os

# Directory containing the files
static_dir = "/Users/vansh/Desktop/mobile phone preduction /KarmayogAI/frontend/static"

# Emoji to text mapping
emoji_map = {
    "📊": "[Chart]",
    "🎯": "[Target]",
    "📚": "[Courses]",
    "🤖": "[AI]",
    "🔗": "[Link]",
    "📈": "[Trend]",
    "✅": "[✓]",
    "❌": "[✗]",
    "⚠️": "[!]",
    "🏅": "[Medal]",
    "🗺️": "[Map]",
    "⭐": "[*]",
    "💡": "[Hint]",
    "📄": "[Doc]",
    "🔍": "[Search]",
    "🧠": "[AI]",
    "❓": "[?]",
    "🌐": "[Web]",
    "🛡️": "[Admin]",
    "👥": "[Users]",
    "⚡": "[Active]",
    "📝": "[Notes]",
    "🎓": "[Cert]",
    "🏆": "[Trophy]",
    "🌟": "[Star]",
    "🚀": "[Next]",
    "🔷": "[>]",
    "▶": "[>]",
    "▶️": "[>]",
    "↩": "[<-]",
    "↗": "[^]",
    "←": "[<]",
    "→": "[>]",
    "✓": "[✓]",
    "✕": "[x]",
    "☁️": "[Upload]",
    "👤": "[User]",
    "📋": "[List]",
    "📘": "[Book]",
    "🏛️": "[Gov]",
    "💰": "[Budget]",
    "🔑": "[Key]",
    "📧": "[Email]",
    "🌱": "[New]",
    "⏱": "[Time]",
    "⏱️": "[Time]",
    "🎉": "[!]",
    "📂": "[Folder]",
    "🗑": "[Del]",
    "🗓": "[Date]",
    "🏠": "[Home]",
}

# Files to process
files_to_process = [
    "login.html",
    "register.html",
    "dashboard.html",
    "assessment.html",
    "recommendations.html",
    "quiz-generator.html",
    "quiz-take.html",
    "learning-paths.html",
    "progress.html",
    "igot.html",
    "admin.html",
    "shell.html",
    "app.js",
]

total_replacements = 0

for filename in files_to_process:
    filepath = os.path.join(static_dir, filename)
    if not os.path.exists(filepath):
        print(f"  SKIP (not found): {filename}")
        continue

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    original = content
    file_replacements = 0

    for emoji, replacement in emoji_map.items():
        count = content.count(emoji)
        if count > 0:
            content = content.replace(emoji, replacement)
            file_replacements += count

    if file_replacements > 0:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  OK: {filename} — {file_replacements} replacement(s)")
    else:
        print(f"  OK: {filename} — no emojis found")

    total_replacements += file_replacements

print(f"\nDone. Total replacements across all files: {total_replacements}")
