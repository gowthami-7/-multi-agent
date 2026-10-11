## 🚀 Live Demo

**Try the deployed application:** [Open Multi-Agent AI System](YOUR_STREAMLIT_APP_URL)

The application is deployed using Streamlit Community Cloud.

## ✨ Features

- **Planner Agent:** Breaks user requests into manageable tasks.
- **Researcher Agent:** Retrieves relevant information and sources.
- **Executor Agent:** Performs supported tasks, including safe calculations.
- **Verifier Agent:** Checks task results and verification evidence.
- **Interactive Dashboard:** Displays workflow progress, task status, results, and a downloadable report.

## 🛠️ Tech Stack

- Python
- Streamlit
- OpenRouter API
- Wikipedia-based information retrieval
- Pytest for calculator testing

## 💻 Run Locally

1. Clone the repository:

   ```bash
   git clone https://github.com/gowthami-7/-multi-agent.git
   cd -multi-agent
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv venv
   ```

   Windows:

   ```bat
   venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root and configure your OpenRouter API key:

   ```text
   OPENROUTER_API_KEY=your_api_key_here
   ```

5. Start the application:

   ```bash
   python -m streamlit run app/main.py
   ```

**Security:** Never commit your `.env` file or publish your API key.

## 🧪 Tests

Run the calculator tests using:

```bash
python -m pytest tests/test_calculator.py -v
```




\# Autonomous Multi-Agent AI Workflow \& Task Automation System



\## Abstract



This project implements a multi-agent AI workflow system that decomposes user requests into tasks, executes those tasks through specialized agents and tools, and evaluates the resulting outputs using a verification agent. It aims to improve task organization, execution monitoring, and result consistency.



\## Objectives



\- Decompose user requests into manageable tasks.

\- Coordinate specialized AI agents through a central orchestrator.

\- Support arithmetic calculations using a controlled calculator.

\- Retrieve source material for research-oriented tasks.

\- Maintain workflow state, logs, and execution results.

\- Verify outputs and report incomplete tasks or errors.



\## Architecture



1\. \*\*Planning Agent:\*\* Converts a user request into a structured task plan.

2\. \*\*Research Agent:\*\* Retrieves relevant source material for research tasks.

3\. \*\*Execution Agent:\*\* Performs planned tasks using available tools and AI assistance.

4\. \*\*Verification Agent:\*\* Checks task completion, evidence, and result consistency.

5\. \*\*Orchestrator:\*\* Coordinates the workflow and manages task execution.

6\. \*\*Tools:\*\* Provide controlled arithmetic calculation and information retrieval.

7\. \*\*Streamlit Dashboard:\*\* Presents workflow status, tasks, results, verification, and logs.



\## Technology Stack



\- Python

\- Streamlit

\- OpenAI-compatible client

\- OpenRouter API

\- Wikipedia-based information retrieval

\- Python `unittest` framework



\## Project Structure



```text

project2-multi-agent/

├── app/

│   ├── agents/

│   │   ├── planner.py

│   │   ├── researcher.py

│   │   ├── executor.py

│   │   └── verifier.py

│   ├── core/

│   │   ├── orchestrator.py

│   │   └── state.py

│   ├── services/

│   │   └── ai\_service.py

│   ├── tools/

│   │   ├── calculator.py

│   │   └── retrieval.py

│   └── main.py

├── tests/

│   └── test\_calculator.py

├── .env.example

├── .gitignore

├── requirements.txt

└── README.md

```



\## Setup Instructions



\### 1. Install Python



Install a compatible Python version and open a terminal in the project directory.



\### 2. Create and activate a virtual environment



Windows:



```cmd

python -m venv venv

venv\\Scripts\\activate

```



\### 3. Install dependencies



```cmd

python -m pip install -r requirements.txt

```



\### 4. Configure the API key



Create a `.env` file based on `.env.example` and add your own OpenRouter API key:



```text

OPENROUTER\_API\_KEY=your\_openrouter\_api\_key\_here

```



Never commit the `.env` file or publish API credentials.



\### 5. Run the application



From the project root:



```cmd

python -m streamlit run app\\main.py

```



\### 6. Run automated tests



```cmd

python -m unittest discover -s tests -v

```



\## Example Workflow



Example request:



> Calculate 300 times 12 and verify the result.



The Planning Agent creates calculation and verification tasks. The Execution Agent performs the tasks, and the Verification Agent reviews the available evidence.



A successful test run returned a completed workflow, a verification score of 85/100, and no workflow errors. The expected arithmetic result was 3,600.



\## Limitations



\- AI-generated plans and reviews depend on the configured model and its availability.

\- Research quality depends on retrieved source material.

\- The verification agent supports quality checks but does not guarantee factual correctness.

\- API access may require connectivity and may be subject to provider limits.

\- Results should be reviewed before use in high-stakes decisions.



\## Conclusion



The project demonstrates an orchestrated multi-agent workflow combining task planning, research, execution, verification, and status reporting. It provides a foundation for extending AI-assisted automation with additional tools, stronger evaluation, and more robust error handling.



