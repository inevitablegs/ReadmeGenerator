import os
import re
import google.generativeai as genai
from github import Github
from dotenv import load_dotenv
from django.core.cache import cache
from django.core.exceptions import ValidationError
from markdown import markdown
from html.parser import HTMLParser
from groq import Groq
load_dotenv()

genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-1.5-flash')

# --- Helper class to validate markdown content ---
class HTMLFilter(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []

    def handle_data(self, d):
        self.text.append(d)

    def get_data(self):
        return ''.join(self.text)

def validate_markdown(content):
    try:
        html = markdown(content)
        f = HTMLFilter()
        f.feed(html)
        clean_text = f.get_data().strip()
        if not clean_text or len(clean_text) < 50:
            raise ValueError("Generated content is too short or invalid")
        return content
    except Exception as e:
        raise ValidationError(f"Markdown validation failed: {str(e)}")

def extract_repo_info(url):
    parts = url.strip('/').split('/')
    if len(parts) < 2:
        raise ValueError("Invalid GitHub URL")
    return parts[-2], parts[-1]

def log_repo_meta(repo_data):
    print("\n🧾 Repo Metadata Debug:")
    for k, v in repo_data.items():
        if isinstance(v, (dict, list)):
            print(f"{k}: {len(v)} items")
        else:
            print(f"{k}: {v}")

def get_repo_data(owner, repo_name):
    g = Github(os.getenv('GITHUB_TOKEN'))
    repo = g.get_repo(f"{owner}/{repo_name}")

    data = {
        'description': repo.description or 'No description provided.',
        'languages': repo.get_languages(),
        'topics': repo.get_topics(),
        'license': None,
        'stars': repo.stargazers_count,
        'forks': repo.forks_count,
        'watchers': repo.watchers_count,
        'default_branch': repo.default_branch,
    }

    try:
        license_info = repo.get_license()
        if license_info:
            data['license'] = license_info.license.key if license_info.license else None
    except Exception:
        pass

    try:
        readme = repo.get_readme()
        data['existing_readme'] = readme.decoded_content.decode('utf-8')
    except:
        data['existing_readme'] = ""

    data['ingestion_summary'] = get_repo_ingestion_summary(repo)
    return data

def get_repo_ingestion_summary(repo, max_files=50):
    """Smart ingestion of all project types: Python, JS, Node, Web, Docker, etc."""
    important_files = []
    seen_paths = set()

    try:
        contents = repo.get_contents("")
        while contents:
            item = contents.pop(0)

            if item.path in seen_paths:
                continue
            seen_paths.add(item.path)

            if item.type == "dir":
                try:
                    contents.extend(repo.get_contents(item.path))
                except Exception:
                    continue
            elif item.type == "file":
                ext = os.path.splitext(item.name)[-1].lower()
                important_names = [
                    "README.md", "requirements.txt", "setup.py", "Dockerfile", "Makefile",
                    "package.json", "pyproject.toml", ".env.example", "config.json",
                    "docker-compose.yml", "Procfile"
                ]
                important_exts = [
                    ".py", ".js", ".ts", ".html", ".yml", ".yaml", ".json", ".sh", ".cpp", ".java"
                ]

                if item.name in important_names or ext in important_exts:
                    try:
                        content = item.decoded_content.decode("utf-8", errors="ignore")
                        important_files.append({
                            "path": item.path,
                            "language": ext or "text",
                            "content": content[:1500]
                        })
                    except Exception:
                        continue

            if len(important_files) >= max_files:
                break

    except Exception as e:
        important_files.append({"error": f"Ingestion error: {str(e)}"})

    return important_files



def generate_with_groq(prompt, model_name="llama-3.3-70b-versatile"):
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    response = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        temperature=1,
        max_tokens=4096 
    )

    return response.choices[0].message.content.strip()




def generate_readme_content(repo_data, user_prompt="", repo_url="", backend="gemini"):
    file_summary = ""
    for file in repo_data.get('ingestion_summary', []):
        if "path" in file and "content" in file:
            file_summary += f"\n📄 **{file['path']}**:\n```\n{file['content']}\n```\n"

    prompt = f"""
You are a professional technical writer specializing in GitHub documentation.

Generate a clean, well-formatted `README.md` file for the following repository:

---

📁 **Repository Metadata**:
- **Name**: {repo_data.get('name')}
- **Description**: {repo_data.get('description') or 'No description provided'}
- **Languages**: {', '.join(repo_data.get('languages', {}).keys())}
- **Stars**: ⭐ {repo_data.get('stars', 0)}
- **Forks**: 🍴 {repo_data.get('forks', 0)}
- **License**: {repo_data.get('license', 'Not specified')}
- **GitHub URL**: {repo_url}

---

🧠 **Project Ingestion Snapshot**:
{file_summary or 'No files available'}

---

📝 **User’s Custom Prompt**:
{user_prompt if user_prompt else 'N/A'}

---

📌 **README Must Include**:
1. Project title with emoji
2. Description: 2-4 paragraphs
3. Features (bullet points)
4. Installation instructions (include real repo URL: `git clone {repo_url}`)
5. Usage with code examples
6. Configuration if needed
7. Technologies table
8. Explain technologies used (e.g., Python, Django, React)
9. Screenshots (placeholder)
10. Contributing guidelines
11. Do **not** include folder structure

---

🧾 **Formatting Rules**:
- Use GitHub-flavored Markdown
- Emojis in headings
- Code blocks with language syntax like ```python``` or ```bash``
- Limit lines to 100 chars
- Use tables for technologies
- Clear, professional tone
"""

    if backend == "groq":
        raw_md = generate_with_groq(prompt)
    else:
        # Default: Gemini
        response = model.generate_content(
            prompt,
            safety_settings={
                'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
                'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
                'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
                'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE',
            },
            generation_config={
                'temperature': 0.7,
                'top_p': 0.9,
                'max_output_tokens': 2048,
            }
        )
        raw_md = response.text

    if not raw_md:
        raise ValueError(f"{backend.upper()} did not return any content")

    return validate_markdown(raw_md)

def generate_readme(repo_url, user_prompt="", backend="gemini"):
    # Include backend in cache key to separate results
    cache_key = f"readme_{backend}_{repo_url}_{user_prompt}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        owner, repo_name = extract_repo_info(repo_url)
        repo_data = get_repo_data(owner, repo_name)
        repo_data['name'] = repo_name

        log_repo_meta(repo_data)  # Optional logging, keep if useful

        readme_content = generate_readme_content(
            repo_data,
            user_prompt=user_prompt,
            repo_url=repo_url,
            backend=backend
        )

        cache.set(cache_key, readme_content, timeout=86400)
        return readme_content

    except Exception as e:
        raise Exception(f"Failed to generate README: {str(e)}")


# Validate GitHub token on startup
try:
    github_token = os.getenv('GITHUB_TOKEN')
    if github_token:
        g = Github(github_token)
        user = g.get_user()
        print(f"✅ GitHub token validated: {user.login}")
    else:
        print("⚠️ GITHUB_TOKEN not set")
except Exception as e:
    print(f"⚠️ GitHub token validation failed: {str(e)}")
