# A2A Hospitality Concierge (Simple)

[![GitHub license](https://img.shields.io/github/license/andrechen1985/a2a-hospitality-simple)](https://github.com/andrechen1985/a2a-hospitality-simple/blob/main/LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/andrechen1985/a2a-hospitality-simple?style=social)](https://github.com/andrechen1985/a2a-hospitality-simple/stargazers)

[![GitHub issues](https://img.shields.io/github/issues/andrechen1985/a2a-hospitality-simple)](https://github.com/andrechen1985/a2a-hospitality-simple/issues)
[![GitHub forks](https://img.shields.io/github/forks/andrechen1985/a2a-hospitality-simple)](https://github.com/andrechen1985/a2a-hospitality-simple/network)
[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue?logo=docker)](https://www.docker.com/)

> 100% Open Source - Rule-Based - No LLM/Vector DB - Portfolio Demo

## Demo Screenshot
![Demo Screenshot](docs/demo-screenshot.png)

## Quick Start
1. docker compose up --build -d
2. open http://localhost:8501

## Architecture
Streamlit UI -> Agent A (Intent Parser) -> A2A JSON -> Agent B (Rule Engine + Policy Dict) -> Response

## Test Cases
| Member | Prompt | Result |
|--------|--------|--------|
| GOLD_001 | Can I check out at 2pm? | Approved |
| SILVER_002 | Can I check out at 2pm? | Needs approval |
| NEW_GUEST | Can I check out at 2pm? | Denied |

## Tech Stack
- Backend: FastAPI + Pydantic
- Frontend: Streamlit
- Infra: Docker Compose
- Logic: File-based Policy RAG Simulation
- License: MIT
