Google Antigravity IDE Workspace Rules: Graphify Comprehension Workflow

This workspace integrates Graphify (https://graphify.net/) to assist the AI agent with directory mapping, dependency tracing, and context optimization.

Before executing any terminal tool calls, editing files, or generating plans, you must consume this rule block to minimize token footprint and navigate imports without reading raw files in bulk.

1. Core Graphify Outputs & Workspace Context

Graphify constructs a queryable knowledge graph of this workspace, saving its artifacts inside the graphify-out/ directory.

graphify-out/graph.json: The complete, persistent serialized knowledge graph.

graphify-out/GRAPH_REPORT.md: A plain-text summary of high-degree "god" nodes, unexpected file couplings, and structural clusters.

graphify-out/graph.html: An interactive, visual model of the files, classes, methods, and relationships.

2. Dynamic Command Toolbox

If Graphify is installed on the host system, you can execute terminal commands to pull highly targeted contexts instead of reading raw code files. You must use these tools during your research and execution planning phases:

Query the Graph:

graphify query "How does the AI Gateway resolve fallback providers?"


Always use this to isolate relevant subgraphs before requesting code details.

Calculate Connection Paths (Trace Calls / Data Flow):

graphify path "AIGateway" "OllamaProvider"


Use this to find exactly how components interact, which files are imported, and where exceptions might propagate.

Explain Structural Entities:

graphify explain "ResponseValidator"


Fetches the AST-extracted classes, methods, docstrings, and rationale comments for a specific component without opening the source file.

Strict Token Budgeting:
When extracting subgraphs to pass to your internal reasoning loop, use the --budget flag to limit the token footprint of the payload:

graphify query "Identify JSON repair rules" --budget 1000


3. Operational Workflow Rules for Code Comprehension

When tasked with implementing features, fixing bugs, or analyzing logic, you must follow this sequence to minimize token usage:

                  [ Task Received by Agent ]
                              │
                              ▼
            [ Read graphify-out/GRAPH_REPORT.md ]
               (Identify key nodes & structures)
                              │
                              ▼
                [ Query Specific Subgraphs ]
            Using `graphify query` or `graphify path`
                              │
                              ▼
             [ Read ONLY Targeted Code Files ]
             (Pinpointed precisely by the graph)
                              │
                              ▼
            [ Code, Test, and Refresh the Graph ]
                 (Run `graphify --update`)


Never Blindly Grep or Read All Files: If you are introduced to a new feature or debugging task, read graphify-out/GRAPH_REPORT.md first to understand the system architecture.

Trace Paths First: Before modifying an interface, run graphify path between the target component and its dependents. This tells you the exact "blast radius" of your changes so you don't break downstream systems.

Open Files as a Last Resort: Only read a file's raw content once you have used graphify explain or graphify query to confirm it contains the exact code block you need to edit.

Keep the Graph Fresh: After implementing changes or writing new modules, run the graph update command in your terminal to ensure the index matches the code:

graphify --update
