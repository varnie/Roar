import abc
import xmlutils
import hashlib
import errors
import urllib
import urlparse
import urllib2
import re
import auth
from collections import namedtuple

TagType = namedtuple("Tag","name,url")

def encode(s, charset='utf-8'):
    return s.encode(charset,'ignore')

def url_fix(s, charset='utf-8'):
    if isinstance(s, unicode):
        s = s.encode(charset, 'ignore')

    scheme, netloc, path, qs, anchor = urlparse.urlsplit(s)
    path = urllib.quote(path, '/%')
    qs = urllib.quote_plus(qs, ':&=')
    return urlparse.urlunsplit((scheme, netloc, path, qs, anchor))

class Request(object):

    def __init__(self):
        self._paramsMap={}

    def _getParams(self):
        return {"api_key":auth.authData.api_key}

    @property
    def mobileSession(self):
        global _authRequest
        if not _authRequest:
            _authRequest=AuthRequest()
        return _authRequest.mobileSession

    def _call_GET(self, fmfunc, addSign=False):
        self._paramsMap["method"]=fmfunc

        url = "http://%s/2.0/?method=%s" % (auth.URL, fmfunc)
        for k, v in self._paramsMap.iteritems():
            if k is not "method":
                url += "&%s=%s" % (k, v)

        if addSign:
            url += "&api_sig=%s" % self.get_sign()

        url=url_fix(url)

        headers={"Content-type": "application/x-www-form-urlencoded", "Accept-Charset": "utf-8",
                 "User-Agent": "lastfm_client"}

        try:
            request=urllib2.Request(url,headers=headers)
            resp_string=urllib2.urlopen(request).read()
        except urllib2.HTTPError, e:
            resp_string=e.read()
            self._process_errors(resp_string)

        return resp_string

    def _call_POST(self, fmfunc, addSign=False):
        self._paramsMap["method"]=fmfunc

        if addSign and "api_sig" not in self._paramsMap:
            self._paramsMap["api_sig"]=self.get_sign()

        params=urllib.urlencode(self._paramsMap)
        url=url_fix("http://%s/2.0/" % (auth.URL))

        headers={"Content-type": "application/x-www-form-urlencoded", "Accept-Charset": "utf-8",
                 "User-Agent": "lastfm_client"}

        try:
            request=urllib2.Request(url,params,headers)
            resp_string=urllib2.urlopen(request).read()
        except urllib2.HTTPError, e:
            resp_string=e.read()
            self._process_errors(resp_string)

        return resp_string

    def get_sign(self):
        result = []

        for param in sorted(self._paramsMap.keys()):
            encoded_param = param.encode('utf-8')
            value = self._paramsMap[param]

            result.append(encoded_param)
            result.append(value)

        result.append(auth.authData.secret)

        m=hashlib.new('md5')
        m.update(''.join(result))

        return m.hexdigest()

    def _process_errors(self, resp_string):
        elem=xmlutils.extract_elem(resp_string,"error")
        if elem is None:
            raise errors.BadResponseError()
        else:
            raise errors.ResponseError(elem.get("code"), elem.text)

class AuthRequest(Request):
    def __init__(self):
        super(AuthRequest,self).__init__()
        self._authToken=None

    def getToken(self):
        self._paramsMap=self._getParams()
        ret = self._call_GET("auth.getToken",True)
        return xmlutils.extract_elem(ret,"token").text

    def _create_authToken(self):
        if self._authToken is None:
            m = hashlib.new('md5')
            m.update(auth.authData.userpass)
            value = auth.authData.username.lower() + m.hexdigest()
            m = hashlib.new('md5')
            m.update(value)
            self._authToken = m.hexdigest()
        return self._authToken

    @property
    def mobileSession(self):
        self._paramsMap=self._getParams()
        self._paramsMap.update({"username":auth.authData.username, "authToken":self._create_authToken()})
        ret = self._call_GET("auth.getMobileSession",True)
        elem=xmlutils.extract_elem(ret,"session/key")
        if elem is None:
            raise errors.BadResponseError()
        else:
            return elem.text

class UserRequest(Request):
    def __init__(self,name):
        super(UserRequest,self).__init__()
        self._name=encode(name) 
    
    def __repr__(self):
        return self._name

    def _getParams(self):
        params={"user":self._name}
        params.update(super(UserRequest,self)._getParams())
        return params

    def shout(self,message):
        self._paramsMap=self._getParams()
        self._paramsMap.update({"message":message,"sk":self.mobileSession})
        ret=self._call_POST("user.Shout",True)
        return xmlutils.extract_elem(ret,"status",True)


class ArtistRequest(Request):

    re_email=re.compile(r"(?:^|\s)[-a-z0-9_.]+@(?:[-a-z0-9]+\.)+[a-z]{2,6}(?:\s|$)",re.IGNORECASE)

    def __init__(self,name):
        super(ArtistRequest,self).__init__()
        self._name=encode(name)

    def __repr__(self):
        return self._name

    def getName(self):
        return self._name

    def _getParams(self):
        p=super(ArtistRequest,self)._getParams()
        params={"artist":self._name}
        params.update(p)
        return params

    def addTags(self,tags):
        if len(tags) > 10:
            raise errors.Error("too many tags supplied. Max 10 tags")

        self._paramsMap=self._getParams()
        self._paramsMap.update({"tags":','.join(tags),"sk":self.mobileSession})
        ret=self._call_POST("artist.addTags",True)
        return xmlutils.extract_elem(ret,"status",True)

    def removeTag(self,tag):
        self._paramsMap=self._getParams()
        self._paramsMap.update({"tag":tag,"sk":self.mobileSession})
        ret=self._call_POST("artist.removeTag",True)
        return xmlutils.extract_elem(ret,"status",True)

    def getTags(self,autocorrect=0):
        if autocorrect not in (0,1):
            raise errors.Error("wrong autocorect supplied")

        self._paramsMap=self._getParams()
        self._paramsMap.update({"autocorrect":str(autocorrect),"sk":self.mobileSession})
        ret=self._call_POST("artist.getTags",True)
        return [TagType(xmlutils.extract_subelem(tag,"name").text,
            xmlutils.extract_subelem(tag,"url").text) for tag in
            xmlutils.extract_elems(ret,".//tags/tag")]

    def getCorrection(self):
        self._paramsMap=self._getParams()
        ret=self._call_GET("artist.getCorrection",False)
        return [i.text for i in xmlutils.extract_elems(ret,".//correction/artist/name")]

    def getShouts(self,limit=50,autocorrect=0,page=None):
        if limit < 0:
            raise errors.Error("wrong limit supplied")
        if page:
            if page > limit:
                raise errors.Error("wrong page supplied")
            self._paramsMap["page"]=page

        if autocorrect not in (0,1):
            raise errors.Error("wrong autocorrect supplied")

        self._paramsMap=self._getParams()
        self._paramsMap.update({"autocorrect":str(autocorrect),"limit":str(limit)})
        ret=self._call_GET("artist.getShouts",False)
        return [(xmlutils.extract_subelem(shout,"author").text, xmlutils.extract_subelem(shout,"body").text) for shout in xmlutils.extract_elems(ret,".//shouts/shout") ]

    def getSimilar(self,limit=50,autocorrect=0):
        if limit < 0:
            raise errors.Error("wrong limit supplied")

        if autocorrect not in (0,1):
            raise errors.Error("wrong autocorrect supplied")

        self._paramsMap=self._getParams()
        self._paramsMap.update({"autocorrect":str(autocorrect),"limit":str(limit)})
        ret=self._call_GET("artist.getSimilar",False)
        return [ArtistRequest(xmlutils.extract_subelem(artist,"name").text) for artist in xmlutils.extract_elems(ret,".//similarartists/artist")]

    def share(self,recipients,message=None,public=0):
        if len(recipients) < 0 or len(recipients) > 10:
            raise errors.Error("wrong recipients count supplied")

        for user in recipients:
            if "@" in user and not ArtistRequest.re_email.match(user):
                raise errors.Error("wrong recipient supplied '%s'" % (recipient))

        if public not in (0,1):
            raise errors.Error("wrong public supplied")

        self._paramsMap=self._getParams()
        if message:
            self._paramsMap["message"]=message

        self._paramsMap.update({"recipient":",".join(recipients),"public":str(public),"sk":self.mobileSession})
        ret=self._call_POST("artist.share",True)
        return xmlutils.extract_elem(ret,"status",True) 

    def shout(self,message):
        self._paramsMap=self._getParams()
        self._paramsMap.update({"message":message,"sk":self.mobileSession})

        ret=self._call_POST("artist.shout",True)
        return xmlutils.extract_elem(ret,"status",True)

    def search(self,limit=30,page=1):
        if limit < 0:
            raise errors.Error("wrong limit supplied")

        if page < 0 or page > limit:
            raise errors.Error("wrong page supplied")

        self._paramsMap=self._getParams()
        self._paramsMap.update({"limit":str(limit),"page":str(page)})
        ret=self._call_GET("artist.search",False)
        return [ArtistRequest(xmlutils.extract_subelem(artist,"name").text) for artist in
            xmlutils.extract_elems(ret,".//artistmatches/artist")]

    def getEvents(self,autocorrect=0):
        if autocorrect not in (0,1):
            raise errors.Error("wrong autocorrect supplied")
        self._paramsMap=self._getParams()
        self._paramsMap.update({"autocorrect":str(autocorrect)})
        ret=self._call_GET("artist.getEvents",False)
        return [EventRequest(id.text) for id in
                xmlutils.extract_elems(ret,".//events/event/id")]

class EventRequest(Request):
    def __init__(self,id):
        super(EventRequest,self).__init__()
        self._id=id

    def __str__(self):
        return "EventRequest"

    def __repr__(self):
        return "EventRequest(%s)" % (str(self._id))

    def _getParams(self):
        params={"event":str(self._id)}
        params.update(super(EventRequest,self)._getParams())
        return params

    def getID(self):
        return self._id

    def getTitle(self):
        ret=self._getInfo()
        return xmlutils.extract_elem(ret,".//event/title").text

    def getArtists(self):
        ret=self._getInfo()
        return [ArtistRequest(artist.text) for artist in
                xmlutils.extract_elems(ret,".//event/artists/artist")]

    def getVenue(self):
        #TODO
        pass

    def getStartDate(self):
        return xmlutils.extract_elem(self._getInfo(),".//event/startData").text

    def getDescription(self):
        res=xmlutils.extract_elem(self._getInfo(),".//event/description").text
        return res if res else ""

    def getImages(self):
        #TODO
        pass

    def getAttendance(self):
        #TODO
        pass

    def getTag(self):
        #TODO
        pass

    def getURL(self):
        #TODO
        pass

    def getWebsite(self):
        #TODO
        pass

    def getTickets(self):
        #TODO
        pass

    def _getInfo(self):
        self._paramsMap=self._getParams()
        return self._call_GET("event.getInfo",False)

_authRequest=None
