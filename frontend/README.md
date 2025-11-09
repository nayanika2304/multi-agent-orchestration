# Multi-Agent Orchestrator UI

A simple React UI for demonstrating the Multi-Agent Orchestrator system.

## Features

-  Submit queries to the orchestrator
-  See which agent was selected
-  View confidence scores and reasoning
-  Example query buttons for quick testing
-  Clean, modern UI

## Setup

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Make sure the orchestrator is running on `http://localhost:8000`

3. Start the development server:
```bash
npm run dev
```

4. Open your browser to `http://localhost:3000`

## Usage

1. Type a query in the text area (e.g., "Calculate 2 + 2")
2. Click "Submit Query" or press Enter
3. View the response, selected agent, and routing information

## Example Queries

- **Math**: "Calculate 2 + 2", "Solve the equation x^2 - 4 = 0"
- **Currency**: "Convert 100 USD to EUR", "What is the exchange rate for GBP to JPY?"
- **RAG**: "Search for documents about AI"

## API Endpoint

The UI communicates with the orchestrator via:
- **POST** `/management/api/v1/agents/query`
- Request body: `{ "query": "your question here" }`

## Build for Production

```bash
npm run build
```

The built files will be in the `dist` directory.

