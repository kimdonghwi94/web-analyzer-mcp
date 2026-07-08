[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/kimdonghwi94-web-analyzer-mcp-badge.png)](https://mseep.ai/app/kimdonghwi94-web-analyzer-mcp)

# 🔍 Web Analyzer MCP

<a href="https://glama.ai/mcp/servers/@kimdonghwi94/web-analyzer-mcp">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/@kimdonghwi94/web-analyzer-mcp/badge" alt="WebAnalyzer MCP server" />
</a>

A powerful MCP (Model Context Protocol) server for intelligent web content analysis and summarization. Built with FastMCP, this server provides smart web scraping, content extraction, and AI-powered question-answering capabilities.

## ✨ Features

### 🎯 Core Tools

1. **`url_to_markdown`** - Extract and summarize key web page content
   - Analyzes content importance using custom algorithms
   - Removes ads, navigation, and irrelevant content
   - Keeps only essential information (tables, images, key text)
   - Outputs structured markdown optimized for analysis

2. **`web_content_qna`** - AI-powered Q&A about web content
   - Extracts relevant content sections from web pages
   - Uses intelligent chunking and relevance matching
   - Answers questions using OpenAI GPT models

### 🚀 Key Features

- **Smart Content Ranking**: Algorithm-based content importance scoring
- **Essential Content Only**: Removes clutter, keeps what matters
- **Multi-IDE Support**: Works with Claude Desktop, Cursor, VS Code, PyCharm
- **Flexible Models**: Choose from GPT-3.5, GPT-4, GPT-4 Turbo, or GPT-5

## 📦 Installation

### Prerequisites
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (Python package manager)
- Chrome/Chromium browser (for Selenium)
- OpenAI API key (for Q&A functionality)

### 🚀 Quick Start with uv (Recommended)

```bash
# Clone the repository
git clone https://github.com/kimdonghwi94/web-analyzer-mcp.git
cd web-analyzer-mcp

# Run directly with uv (auto-installs dependencies)
uv run mcp-webanalyzer
```

### Installing via Smithery

To install web-analyzer-mcp for Claude Desktop automatically via [Smithery](https://smithery.ai/server/@kimdonghwi94/web-analyzer-mcp):

```bash
npx -y @smithery/cli install @kimdonghwi94/web-analyzer-mcp --client claude
```

# IDE/Editor Integration

<details>
<summary><b>Install Claude Desktop</b></summary>

Add to your Claude Desktop_config.json file. See [Claude Desktop MCP documentation](https://modelcontextprotocol.io/quickstart/user) for more details.

```json
{
  "mcpServers": {
    "web-analyzer": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/web-analyzer-mcp",
        "run", 
        "mcp-webanalyzer"
      ],
      "env": {
        "OPENAI_API_KEY": "your_openai_api_key_here",
        "OPENAI_MODEL": "gpt-4"
      }
    }
  }
}
```

</details>

<details>
<summary><b>Install Claude Code (VS Code Extension)</b></summary>

Add the server using Claude Code CLI:

```bash
claude mcp add web-analyzer -e OPENAI_API_KEY=your_api_key_here -e OPENAI_MODEL=gpt-4 -- uv --directory /path/to/web-analyzer-mcp run mcp-webanalyzer
```
</details>

<details>
<summary><b>Install Cursor IDE</b></summary>

Add to your Cursor settings (`File > Preferences > Settings > Extensions > MCP`):

```json
{
  "mcpServers": {
    "web-analyzer": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/web-analyzer-mcp",
        "run", 
        "mcp-webanalyzer"
      ],
      "env": {
        "OPENAI_API_KEY": "your_openai_api_key_here",
        "OPENAI_MODEL": "gpt-4"
      }
    }
  }
}
```
</details>

<details>
<summary><b>Install JetBrains AI Assistant</b></summary>

See [JetBrains AI Assistant Documentation](https://www.jetbrains.com/help/idea/ai-assistant.html) for more details.

1. In JetBrains IDEs go to **Settings** → **Tools** → **AI Assistant** → **Model Context Protocol (MCP)**
2. Click **+ Add**
3. Click on **Command** in the top-left corner of the dialog and select the **As JSON** option from the list
4. Add this configuration and click **OK**:

```json
{
  "mcpServers": {
    "web-analyzer": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/web-analyzer-mcp",
        "run", 
        "mcp-webanalyzer"
      ],
      "env": {
        "OPENAI_API_KEY": "your_openai_api_key_here",
        "OPENAI_MODEL": "gpt-4"
      }
    }
  }
}
```
</details>

## 🎛️ Tool Descriptions

### `url_to_markdown`
Converts web pages to clean markdown format with essential content extraction.

**Parameters:**
- `url` (string): The web page URL to analyze

**Returns:** Clean markdown content with structured data preservation

### `web_content_qna` 
Answers questions about web page content using intelligent content analysis.

**Parameters:**
- `url` (string): The web page URL to analyze
- `question` (string): Question about the page content

**Returns:** AI-generated answer based on page content

## 🏗️ Architecture

### Content Extraction Pipeline

1. **URL Validation** - Ensures proper URL format
2. **HTML Fetching** - Uses Selenium for dynamic content
3. **Content Parsing** - BeautifulSoup for HTML processing
4. **Element Scoring** - Custom algorithm ranks content importance
5. **Content Filtering** - Removes duplicates and low-value content
6. **Markdown Conversion** - Structured output generation

### Q&A Processing Pipeline

1. **Content Chunking** - Intelligent text segmentation
2. **Relevance Scoring** - Matches content to questions
3. **Context Selection** - Picks most relevant chunks
4. **Answer Generation** - OpenAI GPT integration

## 🏗️ Project Structure

```
web-analyzer-mcp/
├── web_analyzer_mcp/          # Main Python package
│   ├── __init__.py           # Package initialization
│   ├── server.py             # FastMCP server with tools
│   ├── web_extractor.py      # Web content extraction engine
│   └── rag_processor.py      # RAG-based Q&A processor
├── scripts/                   # Build and utility scripts
│   └── build.js              # Node.js build script
├── README.md                 # English documentation
├── README.ko.md              # Korean documentation
├── package.json              # npm configuration and scripts
├── pyproject.toml            # Python package configuration
├── .env.example              # Environment variables template
└── dist-info.json            # Build information (generated)
```

## 🛠️ Development

### Modern Development with uv

```bash
# Clone repository
git clone https://github.com/kimdonghwi94/web-analyzer-mcp.git
cd web-analyzer-mcp

# Development commands
uv run mcp-webanalyzer     # Start development server
uv run python -m pytest   # Run tests
uv run ruff check .        # Lint code
uv run ruff format .       # Format code
uv sync                    # Sync dependencies

# Install development dependencies
uv add --dev pytest ruff mypy

# Create production build
npm run build
```

### Alternative: Traditional Python Development

```bash
# Setup Python environment (if not using uv)
pip install -e .[dev]

# Development commands
python -m web_analyzer_mcp.server  # Start server
python -m pytest tests/            # Run tests
python -m ruff check .             # Lint code
python -m ruff format .            # Format code
python -m mypy web_analyzer_mcp/   # Type checking
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📋 Roadmap

- [ ] Support for more content types (PDFs, videos)
- [ ] Multi-language content extraction
- [ ] Custom extraction rules
- [ ] Caching for frequently accessed content
- [ ] Webhook support for real-time updates

## ⚠️ Limitations

- Requires Chrome/Chromium for JavaScript-heavy sites
- OpenAI API key needed for Q&A functionality
- Rate limited to prevent abuse
- Some sites may block automated access

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙋‍♂️ Support

- Create an issue for bug reports or feature requests
- Contribute to discussions in the GitHub repository
- Check the [documentation](https://github.com/kimdonghwi94/web-analyzer-mcp) for detailed guides

## 🌟 Acknowledgments

- Built with [FastMCP](https://github.com/jlowin/fastmcp) framework
- Inspired by [HTMLRAG](https://github.com/plageon/HtmlRAG) techniques for web content processing
- Thanks to the MCP community for feedback and contributions

---

**Made with ❤️ for the MCP community**