import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import json # Added for JSON output
from typing import Optional, List, Any # Added for Pydantic and type hinting

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import MCPToolkit # camels implementation of the mcp protocol
from camel.types import ModelPlatformType
from camel.toolkits.mcp_toolkit import MCPClient
from pydantic import BaseModel, HttpUrl, field_validator, ValidationError # Added for Pydantic

# --- Pydantic Model for Company Data ---
class CompanyData(BaseModel):
    Company: str
    Company_Website: Optional[HttpUrl] = None
    YC_Link: Optional[HttpUrl] = None
    Short_Description: str
    Tags: Optional[List[str]] = None
    Location: Optional[str] = None
    Founder_Link_1: Optional[HttpUrl] = None # Made optional to handle potential missing values gracefully during parsing
    Founder_Link_2: Optional[HttpUrl] = None
    Founder_Link_3: Optional[HttpUrl] = None

    @field_validator('Tags', mode='before')
    @classmethod
    def split_tags(cls, v: Any) -> Optional[List[str]]:
        if isinstance(v, str):
            if v.lower() == 'nan':
                return None
            return [tag.strip() for tag in v.split(',') if tag.strip()]
        if isinstance(v, list): # If it's already a list (e.g. from JSON)
            return [str(item).strip() for item in v if str(item).strip()]
        return None

    @field_validator(
        'Company_Website', 'YC_Link', 
        'Founder_Link_1', 'Founder_Link_2', 'Founder_Link_3', 
        mode='before'
    )
    @classmethod
    def clean_url(cls, v: Any) -> Optional[Any]:
        if isinstance(v, str):
            v_stripped = v.strip()
            if v_stripped.lower() == 'nan' or not v_stripped:
                return None
        return v

# Ensure your Anthropic API key is set in your environment variables
# os.environ["ANTHROPIC_API_KEY"] = "YOUR_ANTHROPIC_API_KEY"
# you can also use your gemini api key here

# --- Markdown Table Parsing Function ---
def parse_markdown_table_to_objects(markdown_content: str) -> List[CompanyData]:
    lines = markdown_content.strip().split('\n')
    companies: List[CompanyData] = []
    header_line_index = -1

    # Find the header line, skipping potential titles like '## W24'
    for i, line in enumerate(lines):
        if line.strip().startswith('| Company |'):
            header_line_index = i
            break

    if header_line_index == -1:
        print("Error: Markdown table header starting with '| Company |' not found.")
        return companies

    header = [h.strip().replace(' ', '_') for h in lines[header_line_index].split('|')[1:-1]]
    
    # Check for separator line
    if header_line_index + 1 >= len(lines) or not lines[header_line_index + 1].strip().startswith('| ---'):
        print("Error: Markdown table separator line not found or invalid.")
        return companies

    for line_number, line_content in enumerate(lines[header_line_index + 2:]):
        line_stripped = line_content.strip()
        if not line_stripped.startswith('|') or not line_stripped.endswith('|'):
            # Skip lines that are not part of the table structure (e.g. blank lines, or other text)
            continue

        values = [v.strip() for v in line_stripped.split('|')[1:-1]]
        
        if len(values) != len(header):
            print(f"Warning: Skipping row (line {header_line_index + 2 + line_number + 1}) due to column count mismatch. Expected {len(header)}, got {len(values)}. Row: '{line_stripped}'")
            continue

        row_data = {}
        valid_entry = True
        for h, v in zip(header, values):
            # Pydantic model expects field names like Company_Website, Founder_Link_1 etc.
            # The header from markdown might be "Company Website", "Founder Link 1"
            # The .replace(' ', '_') above should handle this.
            row_data[h] = v if v.lower() != 'nan' else None
        
        # Ensure Founder_Link_1 is present, as per original request (even if empty string initially)
        # The Pydantic model now makes it Optional[HttpUrl], so None is fine if missing/NaN.
        # If it MUST be a valid URL and not just an empty string, the model should be HttpUrl (not Optional[HttpUrl])
        # and validation error will occur if it's missing or invalid.
        # For now, we rely on Pydantic validation.

        try:
            company = CompanyData(**row_data)
            companies.append(company)
        except ValidationError as e:
            print(f"Error validating data for row (line {header_line_index + 2 + line_number + 1}): '{line_stripped}'. Error: {e}")
            # print(f"Row data attempted: {row_data}") # For debugging
        except Exception as ex:
            print(f"An unexpected error occurred while processing row (line {header_line_index + 2 + line_number + 1}): '{line_stripped}'. Error: {ex}")

    return companies

# Starting the interactive input loop for the camel ai client 
async def interactive_input_loop(agent: ChatAgent):
    loop = asyncio.get_event_loop()
    print("\nEntering interactive mode. Type 'exit' at any prompt to quit.")
# exit conditions 
    while True:
        uri = await loop.run_in_executor(
            None,
            input,
            "\nEnter the URI (http:, https:, file:, data:) to convert to Markdown (or type 'exit'): "
        )
        uri = uri.strip()
        if uri.lower() == "exit":
            print("Exiting interactive mode.")
            break

        if not uri:
            print("URI cannot be empty.")
            continue

        # Prepend file:// scheme if it looks like a local absolute path
        if uri.startswith('/') and not uri.startswith('file://'):
            print(f"Detected local path, prepending 'file://' to URI: {uri}")
            formatted_uri = f"file://{uri}"
        else:
            formatted_uri = uri

        # The prompt clearly tells the agent which tool to use and what the parameter is.
        query = f"Use the convert_to_markdown tool to convert the content at the URI '{formatted_uri}' to Markdown. Do not generate an answer from your internal knowledge, just show the Markdown output from the tool."

        print(f"\nSending query to agent: {query}")
        response = await agent.astep(query)

        print("\nFull Agent Response Info:")
        print(response.info) # Shows tool calls and parameters

        markdown_content_to_parse = None
        if response.msgs and response.msgs[0].content:
            markdown_content_to_parse = response.msgs[0].content
        elif 'tool_calls' in response.info and response.info['tool_calls']:
            # Try to find markdown in tool call results
            for tool_call in response.info['tool_calls']:
                if hasattr(tool_call, 'result') and isinstance(tool_call.result, str):
                    # Assuming the direct result of the tool is the markdown string
                    markdown_content_to_parse = tool_call.result
                    break # Take the first string result found
        
        if markdown_content_to_parse:
            print("\nAttempting to parse Markdown table to JSON objects...")
            parsed_companies = parse_markdown_table_to_objects(markdown_content_to_parse)

            if parsed_companies:
                output_filename = "companies_output.json"
                # Convert Pydantic models to a list of dicts for JSON serialization
                companies_dict_list = [company.model_dump(mode='json') for company in parsed_companies]
                try:
                    with open(output_filename, 'w') as f:
                        json.dump(companies_dict_list, f, indent=2)
                    print(f"\nSuccessfully converted and saved data to {output_filename}")
                    print(f"Number of companies processed: {len(parsed_companies)}")
                except IOError as e:
                    print(f"\nError saving JSON to file: {e}")
                except Exception as e:
                    print(f"\nAn unexpected error occurred during JSON serialization: {e}")
            else:
                print("\nCould not parse any company data from the Markdown output.")
                print("\nRaw Markdown Output from Agent:")
                print("-" * 20)
                print(markdown_content_to_parse.rstrip())
                print("-" * 20)
        else:
            print("No Markdown content received from the agent to parse.")


# main funct
async def main(server_transport: str = 'stdio'):
    if server_transport != 'stdio':
        print("Error: This client currently only supports 'stdio' transport.")
        return

    print("Starting MarkItDown MCP server in stdio mode...")
    server_command = sys.executable
    server_args = ["-m", "markitdown_mcp"]

    # Get the root directory of the script (assuming it's in the project root)
    project_root = Path(__file__).resolve().parent

    # Create an MCPClient instance, adding the cwd
    server = MCPClient(
        command_or_url=server_command,
        args=server_args,
        # Set the working directory for the server process
        env={"PYTHONPATH": str(project_root / "packages" / "markitdown-mcp" / "src") + os.pathsep + str(project_root / "packages" / "markitdown" / "src") + os.pathsep + os.environ.get("PYTHONPATH", ""), "CWD": str(project_root)},
        # Optional: timeout=None
    )

    # Pass the MCPClient object in a list
    mcp_toolkit = MCPToolkit(servers=[server])

    print("Connecting to MCP server...")
    async with mcp_toolkit.connection() as toolkit:
        print("Connection successful. Retrieving tools...")
        tools = toolkit.get_tools()
        if not tools:
            print("Error: No tools retrieved from the server. Make sure the server started correctly and defined tools.")
            return
        print(f"Tools retrieved: {[tool.func.__name__ for tool in tools]}")

        # Check if the required tool is available using func.__name__
        if not any(tool.func.__name__ == "convert_to_markdown" for tool in tools):
             print("Error: 'convert_to_markdown' tool not found on the server.")
             return

        sys_msg = (
            "You are a helpful assistant. You have access to an external tool called 'convert_to_markdown' which takes a single argument, 'uri'. "
            "When asked to convert a URI to Markdown, you MUST use this tool by providing the URI to the 'uri' parameter. "
            "Provide ONLY the Markdown output received from the tool, without any additional explanation or introductory text."
        )

        # Ensure GOOGLE_API_KEY is set in environment variables
        # print(f"DEBUG: Value of GOOGLE_API_KEY from os.getenv: {os.getenv('GOOGLE_API_KEY')}")
        api_key = os.getenv("GOOGLE_API_KEY") # Check for GOOGLE_API_KEY
        if not api_key:
            print("Error: GOOGLE_API_KEY environment variable not set.") # Update error message
            print("Please set it before running the client.")
            return

        # Configure the model for Google Gemini
        # You might need to install the camel-google extra: pip install camel-ai[google]
        try:
            model = ModelFactory.create(
                model_platform=ModelPlatformType.GEMINI, # Change platform
                # Set the desired Gemini model
                model_type="gemini-2.5-pro-preview-03-25", # Using 1.5 Pro as 2.5 is not yet a valid identifier in CAMEL AI
                api_key=api_key,
                model_config_dict={"temperature": 0.0, "max_tokens": 8192}, # Adjust config if needed
            )
        except Exception as e:
             print(f"Error creating model: {e}")
             print("Ensure you have the necessary dependencies installed (e.g., `pip install camel-ai[google]`)")
             return

        camel_agent = ChatAgent(
            system_message=sys_msg,
            model=model,
            tools=tools,
        )
        camel_agent.reset()
        camel_agent.memory.clear()

        await interactive_input_loop(camel_agent)

if __name__ == "__main__":
    # This client only supports stdio for now
    asyncio.run(main(server_transport='stdio')) 