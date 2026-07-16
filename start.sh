#!/bin/bash
osascript -e 'tell app "Terminal" to do script "cd \"/Users/thanvireddy/MED AI/express-backend\" && node server.js"'
osascript -e 'tell app "Terminal" to do script "cd \"/Users/thanvireddy/MED AI/fastapi-backend\" && uvicorn main:app --reload --port 9000"'
osascript -e 'tell app "Terminal" to do script "cd \"/Users/thanvireddy/MED AI/frontend\" && npm start"'
osascript -e 'tell app "Terminal" to do script "cd \"/Users/thanvireddy/MED AI/doctor-portal\" && npm start"'
