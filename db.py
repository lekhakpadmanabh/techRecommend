from __future__ import division
import os
import pymongo
from hn import get_all
from bson.objectid import ObjectId
from bcrypt import hashpw, gensalt
import nltk
from nltk.corpus import stopwords
from nltk import stem, word_tokenize
import string

nltk.data.path.append('./nltk_data/')
porter = stem.porter.PorterStemmer()
stopset = set(stopwords.words('english'))



try:
    conn=pymongo.MongoClient(os.getenv('MONGODB_URL'))
except pymongo.errors.ConnectionFailure, e:
    print "Could not connect to MongoDB: {}".format(e)

#database/collections init
db = conn.get_default_database()
u_coll = db.users
s_coll = db.stories

def preprocess(title):
    exclude = set(string.punctuation)
    title = ''.join(ch for ch in title if ch not in exclude)
    tokens = word_tokenize(title)
    stems = [porter.stem(i) for i in tokens]
    remove_stops = [x.lower() for x in stems if x not in stopwords.words("english")]
    return remove_stops

def add_new_user(username,password):
    if not u_coll.find_one({'username': username}):
        hashed = hashpw(password,gensalt(log_rounds=12))
        user = {
            "username": username,
            "hash": hashed,
            "stories_liked": [], 
            "stories_disliked": [],
            "total_pos":0,
            "total_neg":0,
            "total_pos_words":0,
            "total_neg_words": 0,
            "bag_of_words": {}
        }
        u_coll.insert(user)
        return True
    else:
        print "Username {0} signup attempted: taken".fomrat(username)
        return False

def verify_credentials(username,password_attempt):
    try:
        hsh = u_coll.find_one({'username': username},{'_id':0,'hash':1})['hash']
    except TypeError:
        print "No such username"
        return False
    if hashpw(password_attempt,hsh) == hsh:
        print "Creds verified"
        return True
    else:
        print "Password Mismatch"
        return False

def run_scraper():
    return get_all()

def add_scraped_stories_db(s):
    for story in s:
        if not s_coll.find_one({'id':story['id']}):
            story["labeled_by"] = []
            s_coll.insert(story)

def get_user_id(username):
    return u_coll.find_one({'username':username},{'_id':1})['_id']

def get_unlabeled_stories(user_id):
    return list(s_coll.find({'labeled_by': {'$ne':user_id}},
                            {'labeled_by':0}))

def get_liked_stories(user_id):
    s_ids = u_coll.find_one({'_id':user_id},{'stories_liked':1,'_id':0})['stories_liked']
    resp = []
    for sid in s_ids:
        resp.append(s_coll.find_one({'_id':sid},{'_id':0,'labeled_by':0}))
    return resp

def label_story(label,user_id,story_id):
    title = s_coll.find_one({'_id':story_id},
                            {'_id':0,'title':1})['title']
    tokens = preprocess(title)
    s_coll.update({'_id':story_id},{'$addToSet': {"labeled_by":user_id}})
    if label=='y':
        u_coll.update({'_id': user_id},{'$inc':{'total_pos':1}})
        u_coll.update({'_id': user_id},
                      {'$addToSet': {"stories_liked":story_id}})
    else:
        u_coll.update({'_id': user_id},{'$inc':{'total_neg':1}})
        u_coll.update({'_id': user_id},
                      {'$addToSet': {"stories_disliked":story_id}})
    for token in tokens:
        #if token in u_coll.find_one({'_id': user_id })['bag_of_words'].keys():
        if list(u_coll.find({'_id': user_id,
                u'bag_of_words.{}'.format(token):{'$exists':True}})):
            if label == 'y':
                u_coll.update(
                   {'_id': user_id},
                   {'$inc':{u'bag_of_words.{}.pos'.format(token):1}})
                u_coll.update(
                   {'_id': user_id},
                   {'$inc': {'total_pos_words':1} })
            else:
                u_coll.update(
                   {'_id': user_id},
                   {'$inc':{u'bag_of_words.{}.neg'.format(token):1}})
                u_coll.update(
                   {'_id': user_id},
                   {'$inc': {'total_neg_words':1} })
        else:
            if label == 'y':
                u_coll.update(
                    {'_id': user_id},
                    {'$set':{u'bag_of_words.{}'.format(token):{'pos':1,'neg':0}}})
                u_coll.update(
                   {'_id': user_id},
                   {'$inc': {'total_pos_words':1} })
            else:
                u_coll.update(
                    {'_id': user_id},
                    {'$set':{u'bag_of_words.{}'.format(token):{'pos':0,'neg':1}}})
                u_coll.update(
                   {'_id': user_id},
                   {'$inc': {'total_neg_words':1} })

def predict(title,user_id):
    """
    The response dictionary is for 
    debugging purposes, remove it later.
    """
    response = {}
    k=1 #smoothener
    tokens = preprocess(title)
    data = u_coll.find_one({'_id': user_id},
                           {'total_pos':1,
                            'total_neg':1,
                            'total_pos_words':1,
                            'total_neg_words':1,
                            'bag_of_words':1})
    total_pw = data["total_pos_words"]
    total_nw = data["total_neg_words"]
    total_vocab = len(u_coll.find_one({'_id': user_id})['bag_of_words'].keys())
    p_pos = data['total_pos']/(data['total_pos']+data['total_neg'])
    p_neg = data['total_neg']/(data['total_pos']+data['total_neg'])
    p_doc_pos = p_pos
    p_doc_neg = p_neg
    response['tpw'] = total_pw
    response['tnw'] = total_nw
    response['tp'] = data['total_pos']
    response['tn'] = data['total_neg']
    for token in tokens:
        if token in data['bag_of_words'].keys():
            token_pos_count = data['bag_of_words'][token]["pos"]
            token_neg_count = data['bag_of_words'][token]["neg"]
            response[token] = data['bag_of_words'][token]
        else:
            token_pos_count = 0
            token_neg_count = 0
            response[token] = {'pos':0,'neg':0};
        p_token_pos = (token_pos_count + k)/ (total_pw + k*total_vocab)
        p_token_neg = (token_neg_count + k)/ (total_nw + k*total_vocab)
        p_doc_pos = p_doc_pos * p_token_pos
        p_doc_neg = p_doc_neg * p_token_neg
    response['pdp'],response['pdn'] =  p_doc_pos, p_doc_neg
    if p_doc_pos > p_doc_neg:
        response['label'] = "y"
    else:
        response['label'] = "n"
    return response

def train(username):
    user_id = get_user_id(username)
    for el in get_unlabeled_stories(user_id):
        while True:
            ans = raw_input("Yay or nay?: ")
            if ans=='y' or ans=='n':
                break
        label_story(el['title'],ans,user_id,el['_id'])

"""
if __name__ == '__main__':
    s = run_scraper()
    add_scraped_stories_db(s)
    """

