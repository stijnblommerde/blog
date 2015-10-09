# import libraries
import webapp2

# import app files
import blog

class MainPage(blog.BaseHandler):
  def get(self):
      self.write('Udacity Web Development CS253')

# map path to handler
app = webapp2.WSGIApplication([ ('/', blog.FrontPage),
                                ('/signup', blog.RegisterHandler),
                                ('/login', blog.LoginHandler),
                                ('/logout', blog.LogoutHandler),
                                ('/newpost', blog.NewPost),
                                ('/([0-9]+)', blog.Permalink),
                                ('/.json', blog.BlogJsonHandler),
                                ('/([0-9]+).json', blog.PermalinkJsonHandler),
                                ('/flush', blog.FlushHandler)], debug=True)
