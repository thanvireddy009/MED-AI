#!/bin/bash
# Clear port 9000 in case a previous backend is still running
lsof -ti :9000 | xargs kill -9 2>/dev/null

osascript -e 'tell app "Terminal" to do script "cd \"/Users/thanvireddy/MED AI/backend\" && \"/Users/thanvireddy/MED AI/.venv/bin/uvicorn\" main:app --reload --port 9000"'
osascript -e 'tell app "Terminal" to do script "cd \"/Users/thanvireddy/MED AI/frontend/reviewer\" && npm start"'
osascript -e 'tell app "Terminal" to do script "cd \"/Users/thanvireddy/MED AI/frontend/doctor\" && PORT=3001 npm start"'
