import webapp2
import os
import jinja2
import json
import time
import utils
import logging
import utils
import time
import re
import math
import random

from google.appengine.api import memcache
from google.appengine.ext import db


# setup for using templates
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True) 

#constants
SUBJECT_RE = re.compile(r"^.{3,50}$")

## superclass
class BaseHandler(webapp2.RequestHandler):

    # shorthand function for response.out.write
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    # render a template
    def render_str(self, template, **params):
        params['user'] = self.user #add user as default argument
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, *a, **kw):
        self.response.out.write(self.render_str(template, *a, **kw))

    def set_secure_cookie(self, name, value):
        cookie_value = utils.make_secure_value(value)
        self.response.headers.add_header("Set-Cookie", "%s=%s; Path=/" % (name, cookie_value))

    def get_secure_cookie(self, name):
        cookie_value = self.request.cookies.get(name)
        return cookie_value and utils.check_secure_value(cookie_value)

    def render_json(self, posts_list):
        json_txt = json.dumps(posts_list)
        self.response.headers['Content-Type'] = "application/json; charset=UTF-8"
        self.write(json_txt)

    def __init__(self, request, response):
        webapp2.RequestHandler.initialize(self, request, response)
        user_id = self.get_secure_cookie('user_id')
        self.user = user_id and User.by_id(int(user_id))


## handlers
class RegisterHandler(BaseHandler):

    def get(self):
        self.render("signup.html")

    def post(self):

        # get user input
        input_username = self.request.get('username')
        input_password = self.request.get('password')
        input_verify = self.request.get('verify')
        input_email = self.request.get('email')

        valid_input, validate_params = validate_form(True, input_username, input_password, input_verify, input_email)
        # matching_usernames, matching_param = compare_usernames(input_username)

        # user exists
        exists = user_exists(input_username)
        if exists:
            print "user exists"
            self.render("signup.html", authorize=True, error_exist="User exists already")
            return

        # invalid input
        if not valid_input:
            self.render("signup.html", **validate_params)
            return

        # user does not exist and valid input
        user = User.register(input_username, input_password, input_email) # create user

        user.put()
        time.sleep(0.5)

        #debug: delete tuples from table
        #db.delete(users)

        user_id = get_user_id(input_username)

        cookie_value = self.get_secure_cookie(user_id)

        # cookie exists
        if cookie_value:

            # secure cookie: redirect to welcome page
            if check_secure_value(cookie_value):
                self.redirect('/welcome')

            # insecure cookie: redirect to signup page
            else:
                self.redirect('/signup')

        # cookie does not exist, create cookie and redirect to welcome page
        else:
            if user_id:
                self.set_secure_cookie('user_id', str(user_id))
                self.redirect('/')

class LoginHandler(BaseHandler):

    def get(self):

        # login with cookie if cookie exists
        cookie_value = self.request.cookies.get("user_id")
        if cookie_value and utils.check_secure_value(cookie_value):
            self.redirect('/')
        else:
            self.render("login.html", authorize=True)
    
    def post(self):

        # get user input
        input_username = self.request.get('username')
        input_password = self.request.get('password')
        input_verify = self.request.get('verify') 

        # validate user input
        valid_input, validate_params = validate_form(False, input_username, input_password, input_verify)

        # check if user exists
        exists = user_exists(input_username)
        print "exists: ", exists
        if not exists:
            print "user does not exist"
            self.render('login.html', authorize=True, error_not_exist="User does not exist")
            return;

        # invalid username or password
        if not valid_input:
            self.render('login.html', authorize=True, **validate_params)
            return;

        # valid username and password and username exists in database
        # create cookie for returned entry
        user = User.by_name(input_username)
        user_id = user.key().id()
        self.set_secure_cookie('user_id', str(user_id))

        # show front page
        self.redirect('/')

class LogoutHandler(BaseHandler):

    def get(self):

        #redirect to front page
        self.redirect('/')

        # clear cookie
        self.response.headers.add_header("Set-Cookie", "%s=%s; Path=/" % ('user_id', ""))

class FrontPage(BaseHandler):

    def get(self):

        # get posts stored in database
        posts = top_posts()

        # delete all posts
        #db.delete(Post.all())

        # get time since last query
        query_time = memcache.get("query_time")
        time_passed_str = utils.time_since_query(query_time)

        self.render('frontpage.html', posts=posts, time=time_passed_str)

class NewPost(BaseHandler):

    def get(self):

        # login required for adding posts
        cookie_val = self.get_secure_cookie("user_id")
        if cookie_val:
            # self.render_form()
            self.render("newpost.html")
        else:
            self.redirect('/login')

    def post(self):

    	#get user input
    	subject = self.request.get('subject')	
    	content = self.request.get('content')
        error = False

        # new post requires subject and content
        missing_error = ""
    	if not subject or not content:
            missing_error = 'provide both message subject and content'
            error = True

        # newpost restricts length of subject
        length_error = ""
        if not SUBJECT_RE.match(subject):
            length_error = "enter subject with min 3 and max 50 characters"
            error = True

        # invalid data
        if error:
            self.render('newpost.html', missing_error=missing_error, length_error=length_error, content=content, subject=subject)
        
        # valid data
        else:
            # create new post

            color = "hsl(" + str(random.randrange(0,360)) + ",60%, 80%)"
            print color

            post = Post.make_post(subject, content, color)
            post.put()
            time.sleep(0.5)

            # update top posts stored in memcache
            top_posts(True)

            # redirect to permalink of new post
            permalink = post.key().id()
            out = "/" + str(permalink)
            self.redirect(out)


class Permalink(BaseHandler):
    def get(self, post_id):
        post = Post.by_id(int(post_id))

        # get time since last query
        query_time = memcache.get("query_time")
        time_passed_str = utils.time_since_query(query_time)

        self.render('permalink.html', post=post, time=time_passed_str)

class BlogJsonHandler(BaseHandler):

    def get(self):

        # get stuff from 10 most recent posts and store in python datastructure
        #posts = get_posts(10)
        posts = Post.get_posts(10)
        posts_list = store_posts(posts)
        self.render_json(posts_list)

class PermalinkJsonHandler(BaseHandler):

    def get(self, post_id):
        post = Post.by_id(int(post_id))
        post = [post]
        posts_list = store_posts(post)
        self.render_json(posts_list)

class FlushHandler(BaseHandler):
    def get(self):

        #delete cash
        memcache.flush_all()

        #redirect to blog FrontPage
        self.redirect('/')

        #check: cache is zero seconds old


## models
class User(db.Model):

    #define properties and types
    username = db.StringProperty(required = True)
    password_hash = db.StringProperty(required = True)
    email = db.StringProperty()

    @classmethod
    def by_id(cls, uid):
        """
        return user by id
        """
        return User.get_by_id(uid, parent = users_key())

    @classmethod
    def by_name(cls, username):
        user = User.all().filter('username =', username).get()
        return user

    @classmethod
    def register(cls, name, pw, email = None):
        """
        returns a new user
        """

        pw_hash = utils.make_pw_hash(name, pw)
        return User(parent = users_key(),
                    username = name,
                    password_hash = pw_hash,
                    email = email)

class Post(db.Model):
    #define properties and types
    subject = db.StringProperty(required = True)
    content = db.TextProperty(required = True)
    color = db.StringProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
    last_modified = db.DateTimeProperty(auto_now = True)

    def as_dict(self):
        d = {"subject": self.subject,
            "content": self.content,
            "color": self.color,
            "created": self.created.strftime("%c"),
            "last_modified": self.last_modified.strftime("%c")}
        return d   

    @classmethod
    def get_posts(cls, num_posts):
        """
        returns number of most recent posts
        """
        posts = Post.all().order('-created')
        return [post for post in posts.run(limit=num_posts)]

    @classmethod
    def make_post(cls, subject, content, color):
        return Post(parent = posts_key(),
                    subject = subject,
                    content = content,
                    color = color)

    @classmethod
    def by_id(cls, pid):
        """
        return post by id
        """
        return Post.get_by_id(pid, parent = posts_key())


## helper functions
def users_key(group = 'default'):
    """
    creates a user key
    """
    return db.Key.from_path('users', group)

def posts_key(group = 'default'):
    """
    creates a posts key
    """
    return db.Key.from_path('posts', group)

def get_user_id(username):
    users = db.GqlQuery("SELECT * FROM User")
    user_id = None
    for user in users:
        if username == user.username:
            user_id = user.key().id()
    return user_id

def user_exists(username):

    exists = False
    users = db.GqlQuery("SELECT * FROM User")
    for user in users:
        if username == user.username:
            exists = True
    return exists   

def validate_form(signup, input_username, input_password, input_verify=None, input_email=None):
    """
    params: 
     - signup: true for signup validation, false for login validation  
     - username and password
     - input_verify, input_email: optional parameters
    returns: 
      - returns true if input is valid, false otherwise and
      - dictionary (params) of errors
    """

    params = {}
    valid_input = True

    valid_username = utils.valid_username(input_username)
    if not valid_username:
        valid_input = False
        params['error_username'] = "Invalid username"

    valid_password = utils.valid_password(input_password)
    if not valid_password:
        valid_input = False
        params['error_password'] = "Invalid password"

    if not input_verify and signup:
        valid_input = False
        params['error_verify'] = "verify password"        

    if input_verify and signup:
        valid_verify = utils.valid_password(input_verify)
        if input_password != input_verify:
            valid_input = False
            params['error_verify'] = "Password and Verification do not match"

    if input_email and signup:
        valid_email = utils.valid_email(input_email)
        if not valid_email:
                params['error_email'] = "Invalid email address"
                params['return_email'] = input_email

    return valid_input, params       

def store_posts(posts):
    """
    """
    return [post.as_dict() for post in posts]  

def top_posts(update=False):
    """
    returns 10 most recent posts, either from cache or database
    """
    key = 'top'
    posts = memcache.get(key)
    if posts is None or update:
        logging.error('QUERY')
        posts = db.GqlQuery( "SELECT * FROM Post WHERE ANCESTOR IS :1 ORDER BY created DESC LIMIT 10", posts_key())
        posts = list(posts) # store result of query as a list
        memcache.set(key, posts)
        memcache.set("query_time", time.time())
    return posts
