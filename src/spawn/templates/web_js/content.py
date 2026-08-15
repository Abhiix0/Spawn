# ---------------------------------------------------------------------------
# Vanilla JS
# ---------------------------------------------------------------------------

VANILLA_INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{project_name}</title>
  <link rel="stylesheet" href="style.css" />
</head>
<body>
  <main>
    <h1>{project_name}</h1>
    <p>Edit <code>script.js</code> to get started.</p>
  </main>
  <script src="script.js"></script>
</body>
</html>
"""

VANILLA_STYLE_CSS = """:root {{
  color-scheme: light dark;
  font-family: system-ui, sans-serif;
}}

body {{
  display: flex;
  min-height: 100vh;
  align-items: center;
  justify-content: center;
  margin: 0;
  text-align: center;
}}
"""

VANILLA_SCRIPT_JS = """console.log("{project_name} is running.");
"""

VANILLA_PACKAGE_JSON = """{{
  "name": "{project_name}",
  "version": "0.1.0",
  "private": true,
  "description": "",
  "scripts": {{
    "start": "npx serve ."
  }},
  "devDependencies": {{
    "serve": "^14.2.1"
  }}
}}
"""

VANILLA_README_CONTENT = """# {project_name}

A vanilla HTML/CSS/JS project scaffolded by Spawn.

## Getting started

```bash
npm install
npm start
```

Then open the URL that `serve` prints (defaults to http://localhost:3000).
"""

# ---------------------------------------------------------------------------
# Node.js / Express
# ---------------------------------------------------------------------------

EXPRESS_SERVER_JS = """const express = require("express");
const healthRouter = require("./routes/health");

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());
app.use("/health", healthRouter);

app.get("/", (req, res) => {{
  res.json({{ message: "{project_name} is running." }});
}});

app.listen(PORT, () => {{
  console.log(`{project_name} listening on http://localhost:${{PORT}}`);
}});
"""

EXPRESS_HEALTH_ROUTE_JS = """const express = require("express");
const router = express.Router();

router.get("/", (req, res) => {{
  res.json({{ status: "ok" }});
}});

module.exports = router;
"""

EXPRESS_PACKAGE_JSON = """{{
  "name": "{project_name}",
  "version": "0.1.0",
  "private": true,
  "description": "",
  "main": "server.js",
  "scripts": {{
    "start": "node server.js",
    "dev": "node --watch server.js"
  }},
  "dependencies": {{
    "express": "^4.19.2"
  }}
}}
"""

EXPRESS_ENV_EXAMPLE = """PORT=3000
"""

EXPRESS_README_CONTENT = """# {project_name}

An Express API scaffolded by Spawn.

## Getting started

```bash
npm install
cp .env.example .env
npm run dev
```

`GET /` returns a hello-world payload. `GET /health` returns `{{"status": "ok"}}`.
"""

# ---------------------------------------------------------------------------
# React (Vite)
# ---------------------------------------------------------------------------

REACT_INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{project_name}</title>
</head>
<body>
  <div id="root"></div>
  <script type="module" src="/src/main.jsx"></script>
</body>
</html>
"""

REACT_MAIN_JSX = """import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import "./App.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
"""

REACT_APP_JSX = """import {{ useState }} from "react";

function App() {{
  const [count, setCount] = useState(0);

  return (
    <main className="app">
      <h1>{project_name}</h1>
      <button onClick={{() => setCount((c) => c + 1)}}>
        Count is {{count}}
      </button>
    </main>
  );
}}

export default App;
"""

REACT_APP_CSS = """.app {{
  display: flex;
  min-height: 100vh;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  font-family: system-ui, sans-serif;
}}
"""

REACT_VITE_CONFIG = """import {{ defineConfig }} from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({{
  plugins: [react()],
}});
"""

REACT_PACKAGE_JSON = """{{
  "name": "{project_name}",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {{
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  }},
  "dependencies": {{
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  }},
  "devDependencies": {{
    "@vitejs/plugin-react": "^4.3.1",
    "vite": "^5.4.0"
  }}
}}
"""

REACT_README_CONTENT = """# {project_name}

A React + Vite project scaffolded by Spawn.

## Getting started

```bash
npm install
npm run dev
```
"""

# ---------------------------------------------------------------------------
# Next.js (App Router)
# ---------------------------------------------------------------------------

NEXTJS_LAYOUT_JS = """import "./globals.css";

export const metadata = {{
  title: "{project_name}",
}};

export default function RootLayout({{ children }}) {{
  return (
    <html lang="en">
      <body>{{children}}</body>
    </html>
  );
}}
"""

NEXTJS_PAGE_JS = """export default function Home() {{
  return (
    <main>
      <h1>{project_name}</h1>
      <p>Edit <code>app/page.js</code> to get started.</p>
    </main>
  );
}}
"""

NEXTJS_GLOBALS_CSS = """body {{
  display: flex;
  min-height: 100vh;
  align-items: center;
  justify-content: center;
  margin: 0;
  font-family: system-ui, sans-serif;
  text-align: center;
}}
"""

NEXTJS_CONFIG_JS = """/** @type {{import('next').NextConfig}} */
const nextConfig = {{}};

module.exports = nextConfig;
"""

NEXTJS_PACKAGE_JSON = """{{
  "name": "{project_name}",
  "version": "0.1.0",
  "private": true,
  "scripts": {{
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  }},
  "dependencies": {{
    "next": "^14.2.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  }}
}}
"""

NEXTJS_README_CONTENT = """# {project_name}

A Next.js (App Router) project scaffolded by Spawn.

## Getting started

```bash
npm install
npm run dev
```
"""

# ---------------------------------------------------------------------------
# Optional extras (written directly, NOT passed through .format_map --
# these are not in any starter_files list, see post_install() in __init__.py)
# ---------------------------------------------------------------------------

ESLINTRC_CONTENT = """{
  "env": { "browser": true, "es2021": true, "node": true },
  "extends": "eslint:recommended",
  "parserOptions": { "ecmaVersion": "latest", "sourceType": "module" },
  "rules": {}
}
"""

PRETTIERRC_CONTENT = """{
  "semi": true,
  "singleQuote": false,
  "printWidth": 88
}
"""

GITHUB_ACTIONS_CI_NODE = """name: CI

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - run: npm install
      - run: npm run build --if-present
"""
