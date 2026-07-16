#!/bin/bash
osascript -e 'tell app "Terminal" to do script "cd \"/Users/thanvireddy/MED AI/backend/express-backend\" && node server.js"'
osascript -e 'tell app "Terminal" to do script "cd \"/Users/thanvireddy/MED AI/backend/fastapi-backend\" && \"/Users/thanvireddy/MED AI/.venv/bin/uvicorn\" main:app --reload --port 9000"'
osascript -e 'tell app "Terminal" to do script "cd \"/Users/thanvireddy/MED AI/frontend\" && npm start"'
osascript -e 'tell app "Terminal" to do script "cd \"/Users/thanvireddy/MED AI/frontend/doctor-portal\" && npm start"'
