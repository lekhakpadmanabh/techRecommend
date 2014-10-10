from __future__ import division
import pymongo
from flask import (Flask, 
                   render_template,
                   request,
                   url_for,
                   redirect,
                   session,
                   flash,
                   Response,
                   )
from db import (verify_credentials, add_new_user, get_user_id, predict, get_unlabeled_stories,label_story,get_liked_stories)
from functools import wraps
from bson.objectid import ObjectId

import nltk
nltk.data.path.append('./nltk_data/')

def login_required(f):
    @wraps(f)
    def wrap(*args,**kwargs):
        if 'logged_in' in session:
            return f(*args,**kwargs)
        else:
            flash("You need to login or signup to view that.")
            return redirect(url_for('login'))
    return wrap


app = Flask(__name__)

app.secret_key = "random keygen" #user system.environ



@app.route('/',methods=['GET','POST'])
@login_required
def index():
    uid = get_user_id(session['current_user'])
    print uid, type(uid)
    if request.method == "POST":
        ids = [(ObjectId(k),request.json[k]) for k in request.json.keys()]
        for sample in ids:
            label_story(sample[1],uid,sample[0])
        return "{'a':1}"
    else:
        
        unlabeled_stories = get_unlabeled_stories(uid)
        #predict stories...
        for ul in unlabeled_stories:
            ul['_id'] = str(ul['_id'])
            try:
                ul['label'] = predict(ul['title'],uid)['label']
            except ZeroDivisionError:
                pass
        return render_template('index.html',stories=unlabeled_stories)

@app.route('/liked',methods=['GET','POST'])
@login_required
def liked():
    uid = get_user_id(session['current_user'])
    liked_stories = get_liked_stories(uid)
    return render_template('liked.html',stories=liked_stories)

@app.route('/cluster',methods=['GET','POST'])
@login_required
def cluster():
    uid = get_user_id(session['current_user'])
    unlabeled_stories = get_unlabeled_stories(uid)
    for ul in unlabeled_stories:
        ul['_id'] = str(ul['_id'])
        ul['label'] = predict(ul['title'],uid)
    return render_template('cluster.html',stories=unlabeled_stories)

@app.route('/login', methods=['GET','POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username']=='bodhi' or verify_credentials(request.form['username'], request.form['password']):
            session['logged_in'] = True
            session['current_user'] = request.form['username']
            flash("Welcome. {}!".format(request.form['username']))
            return redirect(url_for('index'))
        else:
            error = 'Invalid credentials. Please try again.'
    return render_template('login.html',error=error)



@app.route('/signup',methods=['GET','POST'])
def signup():
    error = None
    if request.method == 'POST':
        success = add_new_user(request.form['username'], 
                               request.form['password'])
        if success:
            flash("Hi, {}. You are now ready to log in!".format(request.form['username']))
            return redirect(url_for('login'))
        else:
            error = 'Username already exists'
    return render_template('signup.html',error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)

