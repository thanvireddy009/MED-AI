#!/bin/bash
osascript -e 'tell app "Terminal" to do script "cd \"/Users/thanvireddy/MED AI/human-review-app/backend\" && node server.js"'
osascript -e 'tell app "Terminal" to do script "cd \"/Users/thanvireddy/MED AI/human-review-app/frontend\" && npm start"'
osascript -e 'tell app "Terminal" to do script "cd \"/Users/thanvireddy/MED AI/human-review-app/doctor-portal\" && npm start"'
