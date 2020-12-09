# Strava athlete segment stats given segment end coordinates
This app tries to obtain all the segments the athlete has taken to reach the end of the segment to
come out with the athlete's segment count.

It takes as input the athlete's end latitude and longitude coordinates and tries to find
all the segments leading to it within a specified distance and a start range (both in kms).

**This is just work in progress and does not work as expected considering the strava
segment explorer api only returns the 10 most popular segments instead of returning all**

## Using the APP

First install the pre-requisites with:
```
pip3 install -r requirements.txt
```

Obtain your strava api access client secret and id by visiting `https://www.strava.com/settings/api`

Fill in the secret and id in strava_secret.py. To generate the client access token object file,
`client.pkl`, you start the app for the first time and follow the instructions to generate the access token
by visiting `http://localhost:8000`. Then restart to use the app.

Happy Hacking,
 --Karthick