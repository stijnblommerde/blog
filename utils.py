import re
import hmac
import random
import string
import hashlib
import time

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$") 	#at least 3 characters long
PASSWORD_RE = re.compile(r"^.{3,20}$") 				#at least 3 characters long
EMAIL_RE = re.compile(r"^[\S]+@[\S]+\.[\S]+$")

SECRET = 'imsosecret'

def valid_username(username):
    """
    """
    return username and USERNAME_RE.match(username)

def valid_password(password):
    """
    """
    return password and PASSWORD_RE.match(password)

def valid_email(email):
    """
    """
    return not email or EMAIL_RE.match(email)

def make_secure_value(s):
    """
    params: any string s
    returns: string 's,hash'
    """
    HASH = hash_str(s)
    return "%s|%s" % (s,HASH)

def check_secure_value(h):
    """
    params: h combines original string and its hash value. 's,hash' 
    returns: function checks hash value. returns orginal string if check passes, otherwise None
    """
    s = h.split('|')[0]
    if h == make_secure_value(s):
        return s

def hash_str(s):
    """
    params: string
    returns: hash
    """
    return hmac.new(SECRET, s).hexdigest()

def make_salt():
    """
    returns: random string of 5 letters
    """
    return ''.join(random.choice(string.letters) for x in xrange(5))

def make_pw_hash(name, pw, salt=None):
    """
    params:
        - name is authentication user_name (string),
        - pw is corresponding password
        - salt. optional parameter used to recreate existing hash
    returns: password hash of form 'h,salt' (string)
    """
    if not salt:
        salt = make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    return '%s|%s' % (h, salt)

def valid_pw(name, pw, h):
    """
    params: name, password (pw) and hash (h)
    returns: returns true if password matches it's hash h.

    user provides name and pw. database stores name and h.
    """
    salt = h.split('|')[1]
    return h == make_pw_hash(name, pw, salt)

def time_since_query(query_time):
    """
    params: query_time is time in seconds since epoch till last db query
    return: string containing number of seconds since last db query
    """
    time_passed = 0
    if query_time:
        time_passed = int(time.time() - float(query_time))
        time_passed_str = "Queried " + str(time_passed) + " seconds ago"
    return time_passed_str