"""this module supposed to hold authorization data"""
from collections import namedtuple

AuthDataType = namedtuple("AuthData","api_key,secret,username,userpass")

authData=None
URL=None
def newAuthData(api_key,api_secret,login,password):
    global authData
    authData=AuthDataType(api_key,api_secret,login,password)


