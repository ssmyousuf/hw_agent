# Credit Card Analysis Agent 💳🤖

A **privacy-first**, **local AI-powered** credit card statement analyzer built with Llama 3.2, FastAPI, and MCP (Model Context Protocol).

## ✨ Features

- 🔒 **100% Local Processing** - All data stays on your machine
- 📊 **Smart Analysis** - Automatic categorization and spending insights
- 📈 **Visual Charts** - Bar and pie charts for spending breakdown
- 🐞 **Visual Debugger** - Inspect the agent's reasoning in real-time
- 🔍 **Keyword Search** - Find transactions by merchant or category
- 📄 **Multi-Format Support** - CSV and PDF (including password-protected)
- 💬 **Natural Language** - Ask questions in plain English
- ⚡ **Optimized Performance** - Smart memory management for long conversations

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- 4GB+ RAM (for running the LLM)

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd Agents
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Download the AI model**
   ```bash
   python scripts/download_model.py
   ```

4. **Run the application**
   ```bash
   run_app.bat  # Windows
   # or
   ./run_app.sh  # Linux/Mac
   ```

5. **Open your browser**
   Navigate to `http://localhost:8000`

## 📖 Usage

### Upload Statement
1. Drag & drop your CSV or PDF statement into the upload zone
2. For password-protected PDFs, enter the password when prompted
3. Wait for the parser to extract transactions

### Ask Questions
- "What was my total spending last month?"
- "Show me all Food expenses"
- "How much did I spend at Amazon?"
- "Generate a pie chart of my spending"
- "What are my top 5 expenses?"

### Debug Mode
Click the **🐞 Debug Mode** button to see:
- Agent's thought process
- Tool calls with parameters
- Raw data returned
- Execution flow

## 🏗️ Architecture

```
┌─────────────┐
│  Frontend   │  Vanilla JS + Glassmorphism UI
│  (Browser)  │
└──────┬──────┘
       │ HTTP
┌──────▼──────┐
│   FastAPI   │  REST API + Static File Server
│   Backend   │
└──────┬──────┘
       │
┌──────▼──────┐
│  AI Agent   │  Llama 3.2 3B (llama-cpp-python)
│   (Local)   │  Recursive Tool Calling
└──────┬──────┘
       │
┌──────▼──────┐
│ MCP Server  │  Transaction Tools
│   (Tools)   │  - read_transactions
└─────────────┘  - summarize_spending
                 - generate_spending_chart
```

## 🛠️ Key Components

### Backend (`backend/`)
- **`agent.py`** - Core AI agent with tool-calling loop
- **`main.py`** - FastAPI server and endpoints
- **`mcp_server.py`** - MCP tool definitions
- **`data_ingestion.py`** - PDF/CSV parsing and categorization

### Frontend (`frontend/`)
- **`index.html`** - Main UI structure
- **`app.js`** - Chat logic, file upload, debugger
- **`style.css`** - Glassmorphism design
- **`docs.html`** - Technical documentation

## 🔧 Configuration

### Model Settings
Edit `backend/agent.py`:
```python
self.llm = Llama(
    model_path=self.model_path,
    n_gpu_layers=0,      # Increase for GPU acceleration
    n_ctx=4096,          # Context window size
    verbose=False
)
```

### Categories
Customize merchant categories in `backend/data_ingestion.py`:
```python
categories = {
    "Food & Dining": ["SWIGGY", "ZOMATO", ...],
    "Shopping": ["AMAZON", "FLIPKART", ...],
    # Add your own categories
}
```

## 🎯 Performance Tips

1. **GPU Acceleration**: Set `n_gpu_layers=35` if you have a compatible GPU
2. **Context Management**: The agent auto-truncates old messages to prevent memory issues
3. **Large Files**: For PDFs with 100+ pages, consider splitting them
4. **Query Specificity**: More specific queries = faster, more accurate results

## 🐛 Troubleshooting

### "Could not parse any statements"
- **PDF**: Check if it's password-protected or has an unusual layout
- **CSV**: Ensure it has `date`, `description`, `amount` columns
- Check `debug_pdf_log.txt` for detailed parsing logs

### "Context window exceeded"
- Restart the app to clear conversation history
- The agent now auto-manages memory, but very long sessions may need a refresh

### File upload fails
- Ensure file extension is `.csv` or `.pdf` (case-insensitive)
- Hard refresh browser (`Ctrl+F5`) to clear cache

## 📚 Documentation

Full technical documentation is available at `http://localhost:8000/docs.html` when the app is running.

## 🤝 Contributing

This is a personal project, but suggestions are welcome! Open an issue or submit a pull request.

## 📄 License

MIT License - Feel free to use and modify for your own purposes.

## 🙏 Acknowledgments

- **Llama 3.2** by Meta AI
- **llama-cpp-python** by abetlen
- **FastAPI** by Sebastián Ramírez
- **MCP** by Anthropic

---

**Built with ❤️ for privacy-conscious financial analysis**
