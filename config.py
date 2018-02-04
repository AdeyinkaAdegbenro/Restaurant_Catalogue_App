import os


class Auth:
    CLIENT_ID = ('21410508069-jldvijrq0vme6vchdj2gl7hma0qb8sbp'
                 '.apps.googleusercontent.com')
    CLIENT_SECRET = 'agLcUVQ4MGYg2zgnKIfxeyuc'
    REDIRECT_URI = 'http://localhost:5000/oauth2callback'
    AUTH_URI = 'https://accounts.google.com/o/oauth2/auth'
    TOKEN_URI = 'https://accounts.google.com/o/oauth2/token'
    USER_INFO = 'https://www.googleapis.com/userinfo/v2/me'
    SCOPE = ("https://www.googleapis.com/auth/userinfo.profile",
             " https://www.googleapis.com/auth/userinfo.email",
             " https://www.googleapis.com/auth/calendar")


class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
