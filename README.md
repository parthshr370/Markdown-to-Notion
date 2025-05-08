# Markdown-to-Notion (and JSON) Converter

This project provides tools to convert content from various sources (including XLSX files, URLs, and local files) into Markdown. It also features specialized functionality to parse structured data, particularly company information from table-like Markdown (often derived from Excel/XLSX files), into JSON objects.

The project offers two main interfaces:
1.  A **Command-Line Interface (CLI)** (`camel_markitdown_client.py`): Uses an AI agent (Google Gemini) to process URIs, convert them to Markdown, and then attempt to parse specific table structures into JSON.
2.  A **Streamlit Web Application** (`streamlit_markitdown_app.py`): Provides a user-friendly web UI for converting content from URLs or uploaded files into Markdown and then parsing it into JSON if applicable.

## Core Functionality

*   **Content to Markdown:** Converts content accessible via URIs (schemes: `http://`, `https://`, `file://`, `data:`) into Markdown format. This allows processing web pages, local files (including XLSX, PDF, DOCX if underlying `markitdown` library supports them), and other data sources.
*   **Markdown Table to JSON:** Parses Markdown tables that follow a specific header format (e.g., starting with `| Company | ...`) into a list of structured JSON objects. This is particularly useful for extracting data from tabular sources like Excel spreadsheets that have been converted to Markdown. The expected data fields are defined by a Pydantic model (e.g., `Company`, `Company_Website`, `YC_Link`, `Short_Description`, `Tags`, `Location`, `Founder_Link_1`, etc.).

## How to Run

### I. Prerequisites

1.  **Conda Environment:** It's highly recommended to use a dedicated Conda environment.
    ```bash
    # Example: conda activate your_env_name
    conda activate kratos
    ```

2.  **Installing Dependencies:**

    This project relies on the `markitdown` library and a custom `markitdown-mcp` package.

    *   **Primary Method (using local packages within this project):**
        The project includes `markitdown` and `markitdown-mcp` under the `packages/` directory. To install them in editable mode (recommended for this project's specific setup):
        ```bash
        # Navigate to the project root directory.
        # Install the core markitdown library from the local packages directory
        pip install -e './packages/markitdown[all]'

        # Install the MCP server package from the local packages directory (needed for this project's scripts)
        pip install -e './packages/markitdown-mcp'

        # Install Pydantic for data validation and parsing
        pip install pydantic
        ```
        *(Note: The paths `./packages/markitdown` and `./packages/markitdown-mcp` suggest these are local packages within this project structure. Ensure they exist or adjust paths accordingly if they are external/installed differently.)*

    *   **Alternative: Installing the `markitdown` library (from Microsoft/PyPI):**
        The `markitdown` library is developed by Microsoft. If you prefer to install it from the official PyPI repository or build from their source (this might be useful for system-wide installation or if not using this project's specific bundled version):
        *   Via pip (from PyPI):
            ```bash
            pip install 'markitdown[all]'
            ```
        *   From source (GitHub):
            ```bash
            git clone git@github.com:microsoft/markitdown.git
            cd markitdown
            # This command assumes the microsoft/markitdown repository contains a 'packages/markitdown' subdirectory for installation
            pip install -e 'packages/markitdown[all]'
            ```
        **Important:** If you install `markitdown` this way, you will still need the `markitdown-mcp` package and `Pydantic` for this project's `camel_markitdown_client.py` and `streamlit_markitdown_app.py` to function correctly. Install them from this project's root directory:
        ```bash
        pip install -e './packages/markitdown-mcp'
        pip install pydantic
        ```

3.  **API Keys (for CLI):**
    *   The Camel AI client (CLI) is configured to use Google Gemini. Set your API key as an environment variable:
        ```bash
        export GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY_HERE"
        ```

### II. Running the Camel AI Client (CLI Mode)

This mode uses an LLM agent to interact with the `markitdown` tool.

1.  **Install Camel AI Dependency:**
    ```bash
    pip install "camel-ai[google]"
    ```

2.  **Ensure Prerequisites:** Your Conda environment should be active and `GOOGLE_API_KEY` exported.

3.  **Run the Client Script:** From the project root:
    ```bash
    python camel_markitdown_client.py
    ```
    *   The script will prompt you to enter a URI.
    *   If company data is successfully parsed from the Markdown, it will be saved to `companies_output.json` in the current directory.

### III. Running the Streamlit Frontend (Web UI Mode)

This mode provides a web interface for direct conversion and parsing.

1.  **Install Streamlit Dependency:**
    ```bash
    pip install streamlit
    ```

2.  **Ensure Prerequisites:** Your Conda environment should be active.

3.  **Run the Streamlit App:** From the project root:
    ```bash
    streamlit run streamlit_markitdown_app.py
    ```
    *   Streamlit will provide a local URL (e.g., `http://localhost:8501`) to open in your browser.
    *   You can input a URL or upload a file.
    *   The app will display the generated Markdown and any parsed JSON data, with options to download both.

## Using the `markitdown` library directly (CLI)

The core `markitdown` library (developed by Microsoft) also provides its own command-line interface for direct file conversions. This is separate from the `camel_markitdown_client.py` and `streamlit_markitdown_app.py` scripts packaged with this project.

If you have installed `markitdown` (either through this project's local `packages/` directory or from the official Microsoft sources as described in the "Installing Dependencies" section), you can use its CLI as follows:

*   **Convert a file and print to stdout:**
    ```bash
    markitdown path-to-file.pdf > document.md
    ```

*   **Specify an output file:**
    ```bash
    markitdown path-to-file.pdf -o document.md
    ```

*   **Pipe content from stdin:**
    ```bash
    cat path-to-file.pdf | markitdown
    ```

## Project Structure Snippet (from how_to_run.md)

```
markitdown/
├── packages/
│   ├── markitdown/          # Core library source
│   │   └── src/
│   ├── markitdown-mcp/      # MCP Server source
│   │   └── src/
├── camel_markitdown_client.py # Camel AI client script (CLI mode)
├── streamlit_markitdown_app.py # Streamlit frontend script
├── README.md                  # This file
├── how_to_run.md              # Detailed run guide
└── ...
```
