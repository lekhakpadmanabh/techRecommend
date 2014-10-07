#!/usr/bin/python
import os
import time 
from hn import get_all
from db import add_scraped_stories_db


"""
from celery import Celery
CELERY_RESULT_BACKEND = "mongodb"
sched = Celery('scheduler', broker = os.getenv('MONGODB_URL'))

@sched.tasks
def scrape()
    front = get_all()
    new = get_all('https://news.ycombinator.com/newest')
    add_scraped_stories_db(front)
    add_scraped_stories_db(new)
"""

front = get_all()
add_scraped_stories_db(front)
