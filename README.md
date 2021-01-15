## Youtube transcript scraper
A little hack together to get data. Given a channel channel page - it will iterate throughout all their videos (unless specified on when to end) and grab each video's metadata and transcript into a json file.

e.g.<br>
python YTAutoWebScrape.py https://www.youtube.com/user/PewDiePie/videos
<br>
Notes: 
- requires youtube-dl 
- Currently set up for chrome web browser
- change the executable path in __enter__ for chosen webdriver 
'''