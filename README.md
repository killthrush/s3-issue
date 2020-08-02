# Overview

This repository reproduces an odd issue with S3 and presigned URLs.  With modest byte transfer load of 5 simultaneous 40MB uploads (and also on slower connection speeds of < 10Mbps with single 50MB files) we'd consistently see connections be terminated in the middle of transfers with "broken pipe" errors and/or HTTP status code 0.  

I had ruled out causes like network saturation (the stack on my OSX laptop is nowhere near capacity) and out-of-memory conditions. On a hunch I tried modifying the link timeout value, and to my surprise the broken pipe errors ceased.  So that led me to ask myself - does S3 actively terminate connections for presigned transfers in which the expiration date has passed?  Even if the connection has been established and transfers are active?  It sure looks like that's the case, but I've not seen this behavior mentioned anywhere in the docs or forums.

Some other notes - we've tried uploading a single large (1GB) file and single smaller files with a 10-second timeout value; the single files don't fail.  It's only when we try multiple files at once do we start to see broken connections - and the severity increases with the number of files. We have also ruled out that connections are being made with expired links; transfers are definitely in progress when the connection breaks.  However, if we increase the timeout from a value of 10 to something higher like 1000 we stop seeing the failures.  This is the weirdest part of the whole issue - why would changing the URL and nothing else affect whether or not an active transfer is successful?  


# Setup

To run this, you'll need python 3.8 and the ability to create virtualenvs.  You will also need an active AWS session and an S3 bucket with object read/write access.

1. Clone the repo and create a virtualenv for the project
1. `cd` into the project directory
1. Activate your virtualenv and run `pip install -r requirements-dev.txt`
1. Active a set of AWS session environment variables using any technique at your disposal (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN)

# Running the Code

For the sake of simplicity, the parameters of the test are just controlled by the constants at the top of `s3_connection_issue.py`.  Thease values can easily be modified to test different cases:
```python
BUCKET_NAME = "my-bucket"
CONCURRENT_USERS = 5
LINK_TIMEOUT_VALUE = 10
WORKING_DIRECTORY = "/tmp"
SOURCE_FILE = f"{WORKING_DIRECTORY}/40MBfile"
```

`BUCKET_NAME` and `WORKING_DIRECTORY` should be self explanatory.  The `SOURCE_FILE` value must point to a file on disk; the underlying type isn't important (I used randomly generated binary files).  `CONCURRENT_USERS` is a setting that controls how the tool I'm using (`locust`) manages simultaneous connections through the `gevent` library.  Given a 40MB file I was able to start seeing consistent failures around 3-4 users, and a few failures at 2.  `LINK_TIMEOUT_VALUE` controls the TTL of the generated links.  In all cases I've seen, the higher this value, the fewer failures I'd see.

To run the test module:
```bash
PYTHONPATH=. python src/s3_connection_issue.py
```

To stop the module, use `Ctrl+C`.  This version of my test does not attempt to stop `gevent` gracefully.
