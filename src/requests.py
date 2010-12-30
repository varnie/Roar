import abc
import authinfo
import xmlutils
import hashlib
import errors
import urllib
import urlparse
import urllib2

def url_fix(s, charset='utf-8'):
    if isinstance(s, unicode):
        s = s.encode(charset, 'ignore')

    scheme, netloc, path, qs, anchor = urlparse.urlsplit(s)
    path = urllib.quote(path, '/%')
    qs = urllib.quote_plus(qs, ':&=')
    return urlparse.urlunsplit((scheme, netloc, path, qs, anchor))

class Request(object):
    __metaclass__=abc.ABCMeta

    GET_TYPE,POST_TYPE=(0,1)

    def __init__(self, wsdata, rtype):
        self._wsdata = wsdata
        self._paramsMap={"api_key":self._wsdata.authInfo.api_key}
        if rtype not in (Request.GET_TYPE, Request.POST_TYPE):
            raise errors.Error("wrong request type supplied")
        self._rtype=rtype

    def call(self, fmfunc, addSign=False):
        return self._get_call(fmfunc, addSign) if self._rtype == Request.GET_TYPE else self._post_call(fmfunc, addSign)

    def _get_call(self, fmfunc, addSign=False):
        self._paramsMap["method"]=fmfunc

        url = "http://%s/2.0/?method=%s" % (self._wsdata.URL, fmfunc)
        for k, v in self._paramsMap.iteritems():
            if k is not "method":
                url += "&%s=%s" % (k, v)

        if addSign:
            url += "&api_sig=%s" % self.get_sign()

        headers={"Content-type": "application/x-www-form-urlencoded", "Accept-Charset": "utf-8",
                 "User-Agent": "lastfm_client"}

        url=url_fix(url)

        try:
            request=urllib2.Request(url,headers=headers)
            resp_string=urllib2.urlopen(request).read()
        except urllib2.HTTPError, e:
            resp_string=e.read()
            self._process_errors(resp_string)

        return resp_string

    def _post_call(self, fmfunc, addSign=False):
        self._paramsMap["method"]=fmfunc

        if addSign and "api_sig" not in self._paramsMap:
            self._paramsMap["api_sig"]=self.get_sign()

        params=urllib.urlencode(self._paramsMap)
        headers={"Content-type": "application/x-www-form-urlencoded", "Accept-Charset": "utf-8",
                 "User-Agent": "lastfm_client"}

        url=url_fix("http://%s/2.0/" % (self._wsdata.URL))

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

        result.append(self._wsdata.authInfo.secret)

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
    def __init__(self,wsdata,rtype):
        super(AuthRequest,self).__init__(wsdata,rtype)
        self._authToken=None

    def getToken(self):
        ret = self.call("auth.getToken",True)
        return xmlutils.extract_elem(ret,"token").text

    def _create_authToken(self):
        if self._authToken is None:
            m = hashlib.new('md5')
            m.update(self._wsdata.authInfo.userpass)
            value = self._wsdata.authInfo.username.lower() + m.hexdigest()
            m = hashlib.new('md5')
            m.update(value)
            self._authToken = m.hexdigest()
        return self._authToken

    def getMobileSession(self):
        self._paramsMap.update({"username":self._wsdata.authInfo.username, "authToken":self._create_authToken()})
        ret = self.call("auth.getMobileSession",True)
        elem=xmlutils.extract_elem(ret,"session/key")
        if elem is None:
            raise errors.BadResponseError()
        else:
            return elem.text

class UserRequest(Request):
    def __init__(self,wsdata,rtype):
      super(UserRequest,self).__init__(wsdata,rtype)

    def shout(self,user,message):
        self._paramsMap.update({"user":user,"message":message,"sk":self._wsdata.mobileSession})
        ret=self.call("user.Shout",True)
        return xmlutils.extract_elem(ret,"status",True)


class ArtistRequest(Request):
    def __init__(self,wsdata,rtype):
        super(ArtistRequest,self).__init__(wsdata,rtype)

    def addTags(self,artist,tags):
        if len(tags) > 10:
            raise errors.Error("too many tags supplied. Max 10 tags")

        self._paramsMap.update({"artist":artist,"tags":','.join(tags),"sk":self._wsdata.mobileSession})
        ret=self.call("artist.addTags",True)
        return xmlutils.extract_elem(ret,"status",True)

    def removeTag(self,artist,tag):
        self._paramsMap.update({"artist":artist,"tag":tag,"sk":self._wsdata.mobileSession})
        ret=self.call("artist.removeTag",True)
        return xmlutils.extract_elem(ret,"status",True)

    def getTags(self,artist,autocorrect=0):
        if autocorrect not in (0,1):
            raise errors.Error("wrong autocorect supplied")
        self._paramsMap.update({"artist":artist,"autocorrect":str(autocorrect),"sk":self._wsdata.mobileSession})
        ret=self.call("artist.getTags",True)
        return [(xmlutils.extract_subelem(tag,"name").text, xmlutils.extract_subelem(tag,"url").text) for tag in xmlutils.extract_elems(ret,".//tags/tag") ]         

    def getCorrection(self,artist):
        self._paramsMap.update({"artist":artist})
        ret=self.call("artist.getCorrection",False)
        return [i.text for i in xmlutils.extract_elems(ret,".//correction/artist/name")]

    def getShouts(self,artist,limit=50,autocorrect=0,page=None):
        if limit < 0:
            raise errors.Error("wrong limit supplied")
        if page: 
            if page > limit:
                raise errors.Error("wrong page supplied")
            self._paramsMap["page"]=page

        if autocorrect not in (0,1):
            raise errors.Error("wrong autocorrect supplied")

        self._paramsMap.update({"artist":artist,"autocorrect":str(autocorrect),"limit":limit})
        ret=self.call("artist.getShouts",False)
        return [(xmlutils.extract_subelem(shout,"author").text, xmlutils.extract_subelem(shout,"body").text) for shout in xmlutils.extract_elems(ret,".//shouts/shout") ]
 
    def getSimilar(self,artist,autocorrect=0):
        if autocorrect not in (0,1):
            raise errors.Error("wrong autocorrect supplied")
        self._paramsMap.update({"artist":artist,"autocorrect":str(autocorrect)})
        ret=self.call("artist.getSimilar",False)
        return [(xmlutils.extract_subelem(artist,"name").text, xmlutils.extract_subelem(artist,"url").text) for artist in xmlutils.extract_elems(ret,".//similarartists/artist")]

