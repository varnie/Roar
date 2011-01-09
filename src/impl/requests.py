import abc
import xmlutils
import hashlib
import errors
import urllib
import urlparse
import urllib2
import re
from collections import namedtuple

TagType = namedtuple("Tag","name,url")

def url_fix(s, charset='utf-8'):
    if isinstance(s, unicode):
        s = s.encode(charset, 'ignore')

    scheme, netloc, path, qs, anchor = urlparse.urlsplit(s)
    path = urllib.quote(path, '/%')
    qs = urllib.quote_plus(qs, ':&=')
    return urlparse.urlunsplit((scheme, netloc, path, qs, anchor))

def statusHandler(ret):
    return xmlutils.extract_elem(ret,"status",True)

def getShoutsHandler(ret):
    return [(xmlutils.extract_subelem(shout,"author").text, xmlutils.extract_subelem(shout,"body").text) for shout in xmlutils.extract_elems(ret,".//shouts/shout") ]

def getTagsHandler(ret):
    return [TagType(xmlutils.extract_subelem(tag,"name").text, xmlutils.extract_subelem(tag,"url").text) for tag in xmlutils.extract_elems(ret,".//tags/tag")]

def getSimilarArtistHandler(ret):
    return [ArtistRequest(xmlutils.extract_subelem(artist,"name").text) for artist in xmlutils.extract_elems(ret,".//similarartists/artist")]

class Request(object):

    def __init__(self,client):
        super(Request,self).__init__()
        self._client=client

    def __repr__(self):
        return 'Request(%r)' % (self._client,)

class Client(object):

    def __init__(self,URL,api_key,api_secret,username,password):
        super(Client,self).__init__()
        self._URL=URL
        self._api_key,self._api_secret,self._username,self._password=api_key,api_secret,username,password
        self._authToken=None
        self._sk=None

    def __repr(self):
        return 'Client(%r,%r,%r,%r,%r)' % (self._URL,self._api_key,self._api_secret,self._username,self._password)

    def getToken(self):
        ret = self.call_GET(addSign=True,method="auth.getToken")
        return xmlutils.extract_elem(ret,"token").text

    @property
    def mobileSession(self):
        if self._sk is None:
            ret=self.call_GET(addSign=True,method="auth.getMobileSession",username=self._username,authToken=self.authToken)
            elem=xmlutils.extract_elem(ret,"session/key")
            if elem is None:
                raise errors.BadResponseError()
            else:
                self._sk=elem.text
        return self._sk

    @property
    def authToken(self):
        if self._authToken is None:
            m = hashlib.new('md5')
            m.update(self._password)
            value = self._username.lower() + m.hexdigest()
            m = hashlib.new('md5')
            m.update(value)

            self._authToken = m.hexdigest()
        return self._authToken

    def _fix_params(self,paramsMap):
        try:
            paramsMap.pop(None)
        except KeyError,e:
            pass

        for k,v in paramsMap.iteritems():
            paramsMap[k]=str(v)

    def call_GET(self, addSign=False, **paramsMap):
        self._fix_params(paramsMap)
        paramsMap['api_key']=self._api_key

        url = "http://%s/2.0/?method=%s" % (self._URL, paramsMap['method'])
        for k, v in paramsMap.iteritems():
            if k is not "method":
                url += "&%s=%s" % (k, v)

        if addSign:
            url += "&api_sig=%s" % self._get_sign(paramsMap)

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

    def call_POST(self,**paramsMap):
        paramsMap['sk']=self.mobileSession
        paramsMap['api_key']=self._api_key
        self._fix_params(paramsMap)
        paramsMap.update({'api_sig':self._get_sign(paramsMap)})

        params=urllib.urlencode(paramsMap)
        url=url_fix("http://%s/2.0/" % (self._URL,))

        headers={"Content-type": "application/x-www-form-urlencoded", "Accept-Charset": "utf-8",
                 "User-Agent": "lastfm_client"}
        try:
            request=urllib2.Request(url,params,headers)
            resp_string=urllib2.urlopen(request).read()
        except urllib2.HTTPError, e:
            resp_string=e.read()
            self._process_errors(resp_string)

        return resp_string

    def _get_sign(self,paramsMap):
        result = []

        for param,value in sorted(paramsMap.iteritems()):
            encoded_param = param.encode('utf-8')

            result.append(encoded_param)
            result.append(value)

        result.append(self._api_secret)

        m=hashlib.new('md5')
        m.update(''.join(result))

        return m.hexdigest()

    def _process_errors(self, resp_string):
        elem=xmlutils.extract_elem(resp_string,"error")
        if elem is None:
            raise errors.BadResponseError()
        else:
            raise errors.ResponseError(elem.get("code"), elem.text)

class UserRequest(Request):

    def __init__(self,client,name):
        super(UserRequest,self).__init__(client)
        self._name=name

    def __repr__(self):
        return 'UserRequest(%r,%r)' % (self._client,self._name)

    def shout(self,message):
        ret=self._client.call_POST(user=self._name,method="user.shout",message=message)
        return statusHandler(ret)

    def getShouts(self,limit=50,autocorrect=0,page=None):
        if limit < 0:
            raise errors.Error("wrong limit supplied")
        if page:
            if page > limit:
                raise errors.Error("wrong page supplied")

        if autocorrect not in (0,1):
            raise errors.Error("wrong autocorrect supplied")

        ret=self._client.call_GET(method="user.getShouts",user=self._name,autocorrect=autocorrect,limit=limit,page=page)
        return getShoutsHandler(ret)

class ArtistRequest(Request):

    re_email=re.compile(r"(?:^|\s)[-a-z0-9_.]+@(?:[-a-z0-9]+\.)+[a-z]{2,6}(?:\s|$)",re.IGNORECASE)

    def __init__(self,client,name):
        super(ArtistRequest,self).__init__(client)
        self._name=name

    def __repr__(self):
        return 'ArtistRequest(%r,%r)' % (self._client,self._name)

    def getName(self):
        return self._name

    def getCorrection(self):
        ret=self._client.call_GET(addSign=False,method="artist.getCorrection",artist=self._name)
        return [i.text for i in xmlutils.extract_elems(ret,".//correction/artist/name")]

    def search(self,limit=30,page=1):
        if limit < 0:
            raise errors.Error("wrong limit supplied")

        if page < 0 or page > limit:
            raise errors.Error("wrong page supplied")

        ret=self._client.call_GET(addSign=False,method="artist.search",artist=self._name,limit=limit,page=page)
        return [ArtistRequest(client=self._client,name=xmlutils.extract_subelem(artist,"name").text) for artist in
            xmlutils.extract_elems(ret,".//artistmatches/artist")]

    def getEvents(self,autocorrect=0):
        if autocorrect not in (0,1):
            raise errors.Error("wrong autocorrect supplied")

        ret=self._client.call_GET(addSign=False,method="artist.getEvents",artist=self._name,autocorrect=autocorrect)
        return [EventRequest(client=self._client, id=id.text) for id in
                xmlutils.extract_elems(ret,".//events/event/id")]

    def shout(self,message):
        ret=self._client.call_POST(artist=self._name,method="artist.shout",message=message)
        return statusHandler(ret)

    def getShouts(self,limit=50,autocorrect=0,page=None):
        if limit < 0:
            raise errors.Error("wrong limit supplied")
        if page:
            if page > limit:
                raise errors.Error("wrong page supplied")

        if autocorrect not in (0,1):
            raise errors.Error("wrong autocorrect supplied")

        ret=self._client.call_GET(method="artist.getShouts",artist=self._name,autocorrect=autocorrect,limit=limit,page=page)
        return getShoutsHandler(ret)

    def addTags(self,tags):
        if len(tags) > 10:
            raise errors.Error("too many tags supplied. Max 10 tags")

        ret=self._client.call_POST(method='artist.addTags',artist=self._name,tags=','.join(tags))
        return statusHandler(ret)

    def removeTag(self,tag):
        ret=self._client.call_POST(method='artist.removeTag',artist=self._name,tag=tag)
        return statusHandler(ret)

    def getTags(self,autocorrect=0):
        if autocorrect not in (0,1):
            raise errors.Error("wrong autocorect supplied")

        ret=self._client.call_POST(method='artist.getTags',artist=self._name,autocorrect=autocorrect)
        return getTagsHandler(ret)

    def share(self,recipients,message=None,public=0):
        if len(recipients) < 0 or len(recipients) > 10:
            raise errors.Error("wrong recipients count supplied")

        for user in recipients:
            if "@" in user and not Request.re_email.match(user):
                raise errors.Error("wrong recipient supplied '%s'" % (recipient))

        if public not in (0,1):
            raise errors.Error("wrong public supplied")

        ret=self._client.call_POST(artist=self._name,method="artist.share",message=message,public=public,recipient=','.join(recipients))
        return statusHandler(ret)

    def getSimilar(self,limit=50,autocorrect=0):
        if limit < 0:
            raise errors.Error("wrong limit supplied")

        if autocorrect not in (0,1):
            raise errors.Error("wrong autocorrect supplied")

        ret=self._client.call_GET(addSign=False,method="artist.getSimilar",artist=self._name,limit=limit,autocorrect=autocorrect)
        return [ArtistRequest(client=self._client,name=xmlutils.extract_subelem(artist,"name").text) for artist in xmlutils.extract_elems(ret,".//similarartists/artist")]

class VenueRequest(Request):

    def __init__(self,client,id,name):
        super(VenueRequest,self).__init__(client)
        self._id = id
        self._name=name

    def __repr__(self):
        return "VenueRequest(%r,%r,%r)" % (self._client,self._name,self._id)

    def getEvents(self):
        res=self._client.call_GET(addSign=False,method="venue.getEvents",venue=self._id)
        return [EventRequest(client=self._client,id=xmlutils.extract_subelem(event,"id").text) for event in xmlutils.extract_elems(res,".//events/event")]

    def getPastEvents(self,page=1,limit=50):
        if limit < 0:
            raise errors.Error("wrong limit supplied")

        if page < 0 or page > limit:
            raise errors.Error("wrong page supplied")

        res=self._client.call_GET(addSign=False,method="venue.getPastEvents",venue=self._id,page=page,limit=limit)

        return [EventRequest(client=self._client,id=xmlutils.extract_subelem(event,"id").text) for
                event in xmlutils.extract_elems(res,".//events/event")]

    def search(self,page=1,limit=50):
        if limit < 0:
            raise errors.Error("wrong limit supplied")

        if page < 0 or page > limit:
            raise errors.Error("wrong page supplied")

        res=self._client.call_GET(addSign=False,method="venue.search",venue=self._name,limit=limit,page=page)
        return [EventRequest(client=self._client,id=xmlutils.extract_subelem(event,"id").text) for event in  xmlutils.extract_elems(res,".//results/venuematches/venue")]

class EventRequest(Request):

    def __init__(self,client,id):
        super(EventRequest,self).__init__(client)
        self._id=id

    def __repr__(self):
        return "EventRequest(%r,%r)" % (self._client,self._id)

    def getID(self):
        return self._id

    def getTitle(self):
        return xmlutils.extract_elem(self._getInfo(),".//event/title").text

    def getArtists(self):
        return [ArtistRequest(client=self._client, name=artist.text) for artist in
                xmlutils.extract_elems(self._getInfo(),".//event/artists/artist")]

    def getAttendance(self):
        return xmlutils.extract_elem(self._getInfo(),".//event/attendance").text

    def getReviews(self):
        return  xmlutils.extract_elem(self._getInfo(),".//event/reviews").text

    def getUrl(self):
        return xmlutils.extract_elem(self._getInfo(),".//event/url").text

    def getStartDate(self):
        return xmlutils.extract_elem(self._getInfo(),".//event/startDate").text

    def getDescription(self):
        res=xmlutils.extract_elem(self._getInfo(),".//event/description").text
        return res if res else ""

    def getImages(self):
        return [image.text for image in xmlutils.extract_elems(self._getInfo(),".//event/image")]

    def getVenue(self):
        res = xmlutils.extract_elem(self._getInfo(),".//event/venue")
        return VenueRequest(client=self._client,id=xmlutils.extract_subelem(res,"id").text, name=xmlutils.extract_subelem(res,"name").text)

    def getTag(self):
        #TODO
        pass

    def getWebsite(self):
        return xmlutils.extract_elem(self._getInfo(),".//event/website").text

    def getTickets(self):
        #TODO
        pass

    def _getInfo(self):
        return self._client.call_GET(addSign=False,method="event.getInfo",event=self._id)

    def share(self,recipients,message=None,public=0):
        if len(recipients) < 0 or len(recipients) > 10:
            raise errors.Error("wrong recipients count supplied")

        for user in recipients:
            if "@" in user and not Request.re_email.match(user):
                raise errors.Error("wrong recipient supplied '%s'" % (recipient))

        if public not in (0,1):
            raise errors.Error("wrong public supplied")

        ret=self._client.call_POST(event=self._id,method="event.share",message=message,public=public,recipient=','.join(recipients))
        return statusHandler(ret)

class TrackRequest(Request):

    def __init__(self,client,name,artist):
        super(TrackRequest,self).__init__(client)
        self._name=name
        self._artist=artist

    def _getInfo(self,autocorrect=0,username=None):
        if autocorrect not in (0,1):
            raise errors.Error("wrong autocorrect supplied")

        return self._client.call_GET(method="track.getInfo",track=self._name,artist=self._artist,autocorrect=autocorrect,username=username)

    def __repr(self):
        return 'TrackRequest(%r,%r,%r)' % (self._client,self._name,self._artist)

    def getShouts(self,limit=50,autocorrect=0,page=None):
        if limit < 0:
            raise errors.Error("wrong limit supplied")
        if page:
            if page > limit:
                raise errors.Error("wrong page supplied")

        if autocorrect not in (0,1):
            raise errors.Error("wrong autocorrect supplied")

        ret=self._client.call_GET(addSign=False,method="track.getShouts",track=self._name,artist=self._artist,autocorrect=autocorrect,limit=limit,page=page)
        return getShoutsHandler(ret)

    def share(self,recipients,message=None,public=0):
        if len(recipients) < 0 or len(recipients) > 10:
            raise errors.Error("wrong recipients count supplied")

        for user in recipients:
            if "@" in user and not Request.re_email.match(user):
                raise errors.Error("wrong recipient supplied '%s'" % (recipient,))

        if public not in (0,1):
            raise errors.Error("wrong public supplied")

        ret=self._client.call_POST(track=self._name,artist=self._artist,method="track.share",message=message,public=public,recipient=','.join(recipients))
        return statusHandler(ret)

    def addTags(self,tags):
        if len(tags) > 10:
            raise errors.Error("too many tags supplied. Max 10 tags")

        ret=self._client.call_POST(method='track.addTags',track=self._name,artist=self._artist,tags=','.join(tags))
        return statusHandler(ret)

    def removeTag(self,tag):
        ret=self._client.call_POST(method='track.removeTag',track=self._name,artist=self._artist,tag=tag)
        return statusHandler(ret)

    def getTags(self,autocorrect=0):
        if autocorrect not in (0,1):
            raise errors.Error("wrong autocorect supplied")

        ret=self._client.call_POST(method='track.getTags',track=self._name,artist=self._artist,autocorrect=autocorrect)
        return getTagsHandler(ret)

class AlbumRequest(Request):

    def __init__(self,client,name,artist):
        super(AlbumRequest,self).__init__(client)
        self._name=name
        self._artist=artist

    def __repr__(self):
        return "AlbumRequest(%r,%r,%r)" % (self._client,self._name,self._artist)

    def addTags(self,tags):
        if len(tags) > 10:
            raise errors.Error("too many tags supplied. Max 10 tags")

        ret=self._client.call_POST(method='album.addTags',album=self._name,artist=self._artist,tags=','.join(tags))
        return statusHandler(ret)

    def removeTag(self,tag):
        ret=self._client.call_POST(method='album.removeTag',album=self._name,artist=self._artist,tag=tag)
        return statusHandler(ret)

    def getTags(self,autocorrect=0):
        if autocorrect not in (0,1):
            raise errors.Error("wrong autocorect supplied")

        ret=self._client.call_POST(method='album.getTags',album=self._name,artist=self._artist,autocorrect=autocorrect)
        return getTagsHandler(ret)

    def share(self,recipients,message=None,public=0):
        if len(recipients) < 0 or len(recipients) > 10:
            raise errors.Error("wrong recipients count supplied")

        for user in recipients:
            if "@" in user and not Request.re_email.match(user):
                raise errors.Error("wrong recipient supplied '%s'" % (recipient,))

        if public not in (0,1):
            raise errors.Error("wrong public supplied")

        ret=self._client.call_POST(album=self._name,artist=self._artist,method="album.share",message=message,public=public,recipient=','.join(recipients))
        return statusHandler(ret)

    def getShouts(self,limit=50,autocorrect=0,page=None):
        if limit < 0:
            raise errors.Error("wrong limit supplied")
        if page:
            if page > limit:
                raise errors.Error("wrong page supplied")

        if autocorrect not in (0,1):
            raise errors.Error("wrong autocorrect supplied")

        ret=self._client.call_GET(addSign=False,method="album.getShouts",album=self._name,artist=self._artist,autocorrect=autocorrect,limit=limit,page=page)
        return getShoutsHandler(ret)
