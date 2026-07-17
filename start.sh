#!/bin/bash
osascript -e 'tell app "Terminal" to do script "cd \"/Users/thanvireddy/MED AI/backend\" && \"/Users/thanvireddy/MED AI/.venv/bin/uvicorn\" main:app --reload --port 9000"'
osascript -e 'tell app "Terminal" to do script "cd \"/Users/thanvireddy/MED AI/frontend\" && npm start"'
osascript -e 'tell app "Terminal" to do script "cd \"/Users/thanvireddy/MED AI/frontend-doctor\" && npm start"'
