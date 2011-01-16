import xmlutils
import hashlib
import errors
import urllib
import urlparse
import urllib2
import re
from collections import namedtuple

ImageType = namedtuple("Image","title,url,dateadded,format,owner,sizes,thumbsup,thumbsdown")

def url_fix(s, charset='utf-8'):
    if isinstance(s, unicode):
        s = s.encode(charset, 'ignore')

    scheme, netloc, path, qs, anchor = urlparse.urlsplit(s)
    path = urllib.quote(path, '/%')
    qs = urllib.quote_plus(qs, ':&=')
    return urlparse.urlunsplit((scheme, netloc, path, qs, anchor))

def _statusHandler(ret):
    return xmlutils.extract_elem(ret,"status",True)

def _getShoutsHandler(ret):
    return [(xmlutils.extract_subelem(shout,"author").text, xmlutils.extract_subelem(shout,"body").text) for shout in xmlutils.extract_elems(ret,".//shouts/shout") ]

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

    def __str__(self):
        return 'Client'

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
        for k in paramsMap.keys():
            v = paramsMap[k]
            if v is None:
                paramsMap.pop(k)
            else:
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
        paramsMap.update({'sk':self.mobileSession, 'api_key':self._api_key})
        self._fix_params(paramsMap)
        paramsMap.update({'api_sig':self._get_sign(paramsMap)}) #NB: api_sig must be calculated after all params have been supplied

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
        return _statusHandler(ret)

    def getShouts(self,limit=50,autocorrect=0,page=None):
        if limit < 0:
            raise errors.Error("wrong limit supplied")
        if page:
            if page > limit:
                raise errors.Error("wrong page supplied")

        if autocorrect not in (0,1):
            raise errors.Error("wrong autocorrect supplied")

        ret=self._client.call_GET(method="user.getShouts",user=self._name,autocorrect=autocorrect,limit=limit,page=page)
        return _getShoutsHandler(ret)

    def getName(self):
        return self._name

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
        ret=self._client.call_GET(method="artist.getCorrection",artist=self._name)

        return [ArtistRequest(client=self._client,name=the_name) for the_name in xmlutils.extract_elems(ret,".//correction/artist/name")]

    def getPastEvents(self,autocorrect=0,limit=50,page=1):
        if limit < 0:
            raise errors.Error("wrong limit supplied")

        if page < 0 or page > limit:
            raise errors.Error("wrong page supplied")

        res=self._client.call_GET(method="artist.getPastEvents",artist=self._name,page=page,autocorrect=autocorrect,limit=limit)
        return [EventRequest(client=self._client,id=xmlutils.extract_subelem(event,"id").text) for event in xmlutils.extract_elems(res,".//events/event")]

    def getPodcast(self):
#TODO
        pass

    def getTopAlbums(self,autocorrect=0):
        if autocorrect not in (0,1):
            raise errors.Error("wrong autocorrect supplied")

        ret=self._client.call_GET(method="artist.getTopAlbums",autocorrect=autocorrect,artist=self._name)
        result=[]
        for album in xmlutils.extract_elems(ret,".//topalbums/album"):
            name=xmlutils.extract_subelem(album,".//name").text
            result.append(AlbumRequest(client=self._client,name=name,artist=self._name))

        return result

    def getTopFans(self,autocorrect=0):
        if autocorrect not in (0,1):
            raise errors.Error("wrong autocorrect supplied")

        ret=self._client.call_GET(method="artist.getTopFans",autocorrect=autocorrect,artist=self._name)
        result=[]
        for user in xmlutils.extract_elems(ret,".//topfans/user"):
            name=xmlutils.extract_subelem(user,".//name").text
            result.append(UserRequest(client=self._client,name=name))

        return result

    def getTopTags(self,autocorrect=0):
        if autocorrect not in (0,1):
            raise errors.Error("wrong autocorrect supplied")

        ret=self._client.call_GET(method="artist.getTopTags",autocorrect=autocorrect,artist=self._name)
        result=[]
        for tag in xmlutils.extract_elems(ret,".//toptags/tag"):
            name=xmlutils.extract_subelem(tag,".//name").text
            url=xmlutils.extract_subelem(tag,".//url").text
            result.append(TagRequest(client=self._client, name=name,url=url))

        return result

    def getTopTracks(self,autocorrect=0):
        if autocorrect not in (0,1):
            raise errors.Error("wrong autocorrect supplied")

        ret=self._client.call_GET(method="artist.getTopTracks",autocorrect=autocorrect,artist=self._name)
        result=[]
        for track in xmlutils.extract_elems(ret,".//toptracks/track"):
            name=xmlutils.extract_subelem(track,".//name").text
            result.append(TrackRequest(client=self._client,name=name,artist=self._name))

        return result

    def search(self,limit=30,page=1):
        if limit < 0:
            raise errors.Error("wrong limit supplied")

        if page < 0 or page > limit:
            raise errors.Error("wrong page supplied")

        ret=self._client.call_GET(method="artist.search",artist=self._name,limit=limit,page=page)

        result=[]
        for artist in xmlutils.extract_elems(ret, ".//artistmatches/artist"):
            the_name = xmlutils.extract_subelem(artist,"name").text
            if self._name != the_name:
                result.append(ArtistRequest(client=self._client,name=the_name))
            else:
                if not self in result:
                    result.append(self)

        return result

    def getEvents(self,autocorrect=0):
        if autocorrect not in (0,1):
            raise errors.Error("wrong autocorrect supplied")

        ret=self._client.call_GET(method="artist.getEvents",artist=self._name,autocorrect=autocorrect)
        return [EventRequest(client=self._client, id=id.text) for id in xmlutils.extract_elems(ret,".//events/event/id")]

    def shout(self,message):
        ret=self._client.call_POST(artist=self._name,method="artist.shout",message=message)
        return _statusHandler(ret)

    def getShouts(self,limit=50,autocorrect=0,page=None):
        if limit < 0:
            raise errors.Error("wrong limit supplied")
        if page:
            if page > limit:
                raise errors.Error("wrong page supplied")

        if autocorrect not in (0,1):
            raise errors.Error("wrong autocorrect supplied")

        ret=self._client.call_GET(method="artist.getShouts",artist=self._name,autocorrect=autocorrect,limit=limit,page=page)
        return _getShoutsHandler(ret)

    def addTags(self,tags):
        if len(tags) > 10:
            raise errors.Error("too many tags supplied. Max 10 tags")

        ret=self._client.call_POST(method='artist.addTags',artist=self._name,tags=','.join(tag.getName() for tag in tags))
        return _statusHandler(ret)

    def removeTag(self,tag):
        ret=self._client.call_POST(method='artist.removeTag',artist=self._name,tag=tag.getName())
        return _statusHandler(ret)

    def getTags(self,autocorrect=0):
        if autocorrect not in (0,1):
            raise errors.Error("wrong autocorect supplied")

        ret=self._client.call_POST(method='artist.getTags',artist=self._name,autocorrect=autocorrect)
        return [TagRequest(client=self._client, name=xmlutils.extract_subelem(tag,"name").text, url=xmlutils.extract_subelem(tag,"url").text) for tag in xmlutils.extract_elems(ret,".//tags/tag")]

    #TODO: refactor passing User objects instead of plain strings
    def share(self,recipients,message=None,public=0):
        if len(recipients) < 0 or len(recipients) > 10:
            raise errors.Error("wrong recipients count supplied")

        for user in recipients:
            if "@" in user and not ArtistRequest.re_email.match(user):
                raise errors.Error("wrong recipient supplied '%s'" % (user))

        if public not in (0,1):
            raise errors.Error("wrong public supplied")

        ret=self._client.call_POST(artist=self._name,method="artist.share",message=message,public=public,recipient=','.join(recipients))
        return _statusHandler(ret)

    def getSimilar(self,limit=50,autocorrect=0):
        if limit < 0:
            raise errors.Error("wrong limit supplied")

        if autocorrect not in (0,1):
            raise errors.Error("wrong autocorrect supplied")

        ret=self._client.call_GET(method="artist.getSimilar",artist=self._name,limit=limit,autocorrect=autocorrect)

        result=[]
        for artist in xmlutils.extract_elems(ret,".//similarartists/artist"):
            print artist
            the_name = xmlutils.extract_subelem(artist,"name").text
            if self._name != the_name:
                result.append(ArtistRequest(client=self._client, name=the_name))

        return result

    def getImages(self,limit=50,autocorrect=0,page=None):
        if limit < 0:
            raise errors.Error("wrong limit supplied")
        if page:
            if page > limit:
                raise errors.Error("wrong page supplied")

        if autocorrect not in (0,1):
            raise errors.Error("wrong autocorrect supplied")

        ret=self._client.call_GET(method="artist.getImages",artist=self._name,autocorrect=autocorrect,limit=limit,page=page)

        result=[]
        for image in xmlutils.extract_elems(ret,".//images/image"):

            title=xmlutils.extract_subelem(image,"title").text
            title = title if title else ""
            url=xmlutils.extract_subelem(image,"url").text
            dateadded=xmlutils.extract_subelem(image,".//dateadded").text
            format=xmlutils.extract_subelem(image,".//format").text
            owner=UserRequest(client=self._client,name=xmlutils.extract_subelem(image,"owner"))
            sizes=[size.text for size in xmlutils.extract_subelems(image,".//sizes/size")]
            thumbsup=xmlutils.extract_subelem(image,".//votes/thumbsup").text
            thumbsdown=xmlutils.extract_subelem(image,".//votes/thumbsdown").text

            result.append(ImageType(title,url,dateadded,format,owner,sizes,thumbsup,thumbsdown))

        return result

    def _getInfo(self,lang='en',autocorrect=0,username=None):
        if autocorrect not in (0,1):
            raise errors.Error("wrong autocorrect supplied")

        return self._client.call_GET(method="artist.getInfo",artist=self._name,lang=lang,autocorrect=autocorrect,username=username)

    def isStreamable(self):
        ret=self._getInfo()
        return xmlutils.extract_elem(ret,".//artist/streamable").text == "1"

    def getListeners(self):
        return xmlutils.extract_elem(self._getInfo(), ".//artist/stats/listeners").text

    def getPlayCount(self,username=None):
        return xmlutils.extract_elem(self._getInfo(username=username), ".//artist/stats/playcount").text

    def getBioSummary(self):
        return xmlutils.extract_elem(self._getInfo(), ".//artist/bio/summary").text

    def getBioContent(self):
        return xmlutils.extract_elem(self._getInfo(), ".//artist/bio/content").text

class VenueRequest(Request):

    def __init__(self,client,id,name):
        super(VenueRequest,self).__init__(client)
        self._id = id
        self._name=name

    def __repr__(self):
        return "VenueRequest(%r,%r,%r)" % (self._client,self._name,self._id)

    def getEvents(self):
        res=self._client.call_GET(method="venue.getEvents",venue=self._id)
        return [EventRequest(client=self._client,id=xmlutils.extract_subelem(event,"id").text) for event in xmlutils.extract_elems(res,".//events/event")]

    def getPastEvents(self,page=1,limit=50):
        if limit < 0:
            raise errors.Error("wrong limit supplied")

        if page < 0 or page > limit:
            raise errors.Error("wrong page supplied")

        res=self._client.call_GET(method="venue.getPastEvents",venue=self._id,page=page,limit=limit)

        return [EventRequest(client=self._client,id=xmlutils.extract_subelem(event,"id").text) for event in xmlutils.extract_elems(res,".//events/event")]

    def search(self,page=1,limit=50):
        if limit < 0:
            raise errors.Error("wrong limit supplied")

        if page < 0 or page > limit:
            raise errors.Error("wrong page supplied")

        res=self._client.call_GET(method="venue.search",venue=self._name,limit=limit,page=page)

        result = []
        for venue in xmlutils.extract_elems(res,".//results/venuematches/venue"):
            the_id = xmlutils.extract_subelem(venue,"id").text
            if self._id != the_id:
                the_name = xmlutils.extract_subelem(venue, "name").text
                result.append(VenueRequest(client=self._client,id=the_id,name=the_name))
            else:
                if self not in result:
                    result.append(self)

        return result

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

    def getAttendees(self):
        ret=self._client.call_GET(method="event.getAttendees",event=self._id)

        result=[]
        for user in xmlutils.extract_elems(ret,".//attendees/user"):
            name=xmlutils.extract_subelem(user,".//name").text
            result.append(UserRequest(client=self._client,name=name))

        return result

    def attend(self,status):
        if status not in (0,1,2):
            raise errors.Error("wrong parameter supplied")

        ret=self._client.call_POST(method="event.attend",event=self._id,status=status)
        return _statusHandler(ret)

    def getArtists(self):
        return [ArtistRequest(client=self._client, name=artist.text) for artist in xmlutils.extract_elems(self._getInfo(),".//event/artists/artist")]

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

    def getImagesURLs(self):
        return [image.text for image in xmlutils.extract_elems(self._getInfo(),".//event/image")]

    def getVenue(self):
        res = xmlutils.extract_elem(self._getInfo(),".//event/venue")
        return VenueRequest(client=self._client,id=xmlutils.extract_subelem(res,"id").text, name=xmlutils.extract_subelem(res,"name").text)

    def getWebsite(self):
        return xmlutils.extract_elem(self._getInfo(),".//event/website").text

    def _getInfo(self):
        return self._client.call_GET(method="event.getInfo",event=self._id)

    #TODO: refactor passing User objects instead of plain strings
    def share(self,recipients,message=None,public=0):
        if len(recipients) < 0 or len(recipients) > 10:
            raise errors.Error("wrong recipients count supplied")

        for user in recipients:
            if "@" in user and not ArtistRequest.re_email.match(user):
                raise errors.Error("wrong recipient supplied '%s'" % (user))

        if public not in (0,1):
            raise errors.Error("wrong public supplied")

        ret=self._client.call_POST(event=self._id,method="event.share",message=message,public=public,recipient=','.join(recipients))
        return _statusHandler(ret)

class TrackRequest(Request):

    def __init__(self,client,name,artist):
        super(TrackRequest,self).__init__(client)
        self._name=name
        self._artist=artist

    def _getInfo(self,autocorrect=0,username=None):
        if autocorrect not in (0,1):
            raise errors.Error("wrong autocorrect supplied")

        return self._client.call_GET(method="track.getInfo",track=self._name,artist=self._artist.getName(),autocorrect=autocorrect,username=username)

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

        ret=self._client.call_GET(method="track.getShouts",track=self._name,artist=self._artist.getName(),autocorrect=autocorrect,limit=limit,page=page)
        return _getShoutsHandler(ret)

#TODO: refactor passing User objects instead of plain strings
    def share(self,recipients,message=None,public=0):
        if len(recipients) < 0 or len(recipients) > 10:
            raise errors.Error("wrong recipients count supplied")

        for user in recipients:
            if "@" in user and not ArtistRequest.re_email.match(user):
                raise errors.Error("wrong recipient supplied '%s'" % (user,))

        if public not in (0,1):
            raise errors.Error("wrong public supplied")

        ret=self._client.call_POST(track=self._name,artist=self._artist.getName(),method="track.share",message=message,public=public,recipient=','.join(recipients))
        return _statusHandler(ret)

    def addTags(self,tags):
        if len(tags) > 10:
            raise errors.Error("too many tags supplied. Max 10 tags")

        ret=self._client.call_POST(method='track.addTags',track=self._name,artist=self._artist.getName(),tags=','.join(tag.getName() for tag in tags))
        return _statusHandler(ret)

    def removeTag(self,tag):
        ret=self._client.call_POST(method='track.removeTag',track=self._name,artist=self._artist.getName(),tag=tag.getName())
        return _statusHandler(ret)

    def getTags(self,autocorrect=0):
        if autocorrect not in (0,1):
            raise errors.Error("wrong autocorect supplied")

        ret=self._client.call_POST(method='track.getTags',track=self._name,artist=self._artist.getName(),autocorrect=autocorrect)
        return [TagRequest(client=self._client, name=xmlutils.extract_subelem(tag,"name").text, url=xmlutils.extract_subelem(tag,"url").text) for tag in xmlutils.extract_elems(ret,".//tags/tag")]

    def getName(self):
        return self._name

    def getUrl(self,autocorrect=0,username=None):
        return xmlutils.extract_elem(self._getInfo(autocorrect,username),".//track/url").text

    def getID(self,autocorrect=0,username=None):
        return xmlutils.extract_elem(self._getInfo(autocorrect,username),".//track/id").text

    def getDuration(self,autocorrect=0,username=None):
        return xmlutils.extract_elem(self._getInfo(autocorrect,username),".//track/duration").text

    def getListeners(self,autocorrect=0,username=None):
        return  xmlutils.extract_elem(self._getInfo(autocorrect,username),".//track/listeners").text

    def getPlaycount(self,autocorrect=0,username=None):
        return xmlutils.extract_elem(self._getInfo(autocorrect,username),".//track/playcount").text

    def getTopTags(self,autocorrect=0):
        if autocorrect not in (0,1):
            raise errors.Error("wrong autocorrect supplied")

        ret=self._client.call_GET(method="track.getTopTags",autocorrect=autocorrect,artist=self._artist.getName(),track=self._name)
        result=[]
        for tag in xmlutils.extract_elems(ret,".//toptags/tag"):
            name=xmlutils.extract_subelem(tag,".//name").text
            url=xmlutils.extract_subelem(tag,".//url").text
            result.append(TagRequest(client=self._client,name=name,url=url))

        return result

    def getTopFans(self,autocorrect=0):
        if autocorrect not in (0,1):
            raise errors.Error("wrong autocorrect supplied")

        ret=self._client.call_GET(method="track.getTopFans",autocorrect=autocorrect,artist=self._artist.getName(),track=self._name)
        result=[]
        for user in xmlutils.extract_elems(ret,".//topfans/user"):
            name=xmlutils.extract_subelem(user,".//name").text
            result.append(UserRequest(client=self._client,name=name))

        return result

    def getAlbum(self,autocorrect=0):
        title= xmlutils.extract_elem(self._getInfo(autocorrect=autocorrect),".//track/album/title").text
        return AlbumRequest(client=self._client,name=title,artist=self._artist.getName())

    def getArtist(self):
        return self._artist

    def ban(self):
        ret=self._client.call_POST(method="track.ban",track=self._name,artist=self._artist.getName())
        return xmlutils.extract_elem(ret,"status",True)

    def unban(self):
        ret=self._client.call_POST(method="track.unban",track=self._name,artist=self._artist.getName())
        return xmlutils.extract_elem(ret,"status",True)

    def love(self):
        ret=self._client.call_POST(method="track.love",track=self._name,artist=self._artist.getName())
        return xmlutils.extract_elem(ret,"status",True)

    def unlove(self):
        ret=self._client.call_POST(method="track.unlove",track=self._name,artist=self._artist.getName())
        return xmlutils.extract_elem(ret,"status",True)

    def getBuylinks(self,autocorrect=0,country='united kingdom'):
        """country: A country name, as defined by the ISO 3166-1 country names standard."""

        if autocorrect not in (0,1):
            raise errors.Error("wrong autocorrect supplied")

        ret=self._client.call_GET(method="track.getBuylinks",country=country,track=self._name,artist=self._artist.getName(),autocorrect=autocorrect)

        result=[]
        for affiliation in xmlutils.extract_elems(ret,".//affiliations/physicals/affiliation"):
            buyLink=xmlutils.extract_subelem(affiliation,".//buyLink").text
            result.append(buyLink)

        for affiliation in xmlutils.extract_elems(ret,".//affiliations/downloads/affiliation"):
            buyLink=xmlutils.extract_subelem(affiliation,".//buyLink").text
            result.append(buyLink)

        return result

    def search(self,limit=30,page=1,artist=None):
        """artist argument: Narrow your search by specifying an artist."""

        if limit < 0:
            raise errors.Error("wrong limit supplied")

        if page < 0 or page > limit:
            raise errors.Error("wrong page supplied")

        artist=artist if artist else self._artist

        ret=self._client.call_GET(method="track.search",track=self._name,artist=artist.getName(),limit=limit,page=page)

        result=[]
        for track in xmlutils.extract_elems(ret,".//trackmatches/track"):
            the_name= xmlutils.extract_subelem(track, "name").text
            if self._name != the_name:
                result.append(TrackRequest(client=self._client, name = the_name, artist=artist))
            else:
                if self not in result:
                    result.append(self)

        return result

    def getCorrection(self):
        ret=self._client.call_GET(method="track.getCorrection",track=self._name,artist=self._artist.getName())

        result=[]
        for track in xmlutils.extract_elems(ret, ".//correction/track"):
            the_name = xmlutils.extract_subelem(track, "name").text
            the_artist = xmlutils.extract_subelem(track, "artist/name").text
            result.append(TrackRequest(client=self._client, name=the_name, artist=the_artist))

        return result

    def getShouts(self,limit=50,autocorrect=0,page=None):
        if limit < 0:
            raise errors.Error("wrong limit supplied")
        if page:
            if page > limit:
                raise errors.Error("wrong page supplied")

        if autocorrect not in (0,1):
            raise errors.Error("wrong autocorrect supplied")

        ret=self._client.call_GET(method="track.getShouts",track=self._name,artist=self._artist.getName(),autocorrect=autocorrect,limit=limit,page=page)
        return _getShoutsHandler(ret)

    def getSimilar(self,limit=50,autocorrect=0):
        if limit < 0:
            raise errors.Error("wrong limit supplied")

        if autocorrect not in (0,1):
            raise errors.Error("wrong autocorrect supplied")

        ret=self._client.call_GET(method="track.getSimilar",track=self._name,artist=self._artist.getName(),limit=limit,autocorrect=autocorrect)

        result=[]
        for track in xmlutils.extract_elems(ret,".//similartracks/track"):
            the_name=xmlutils.extract_subelem(track, "name").text
            the_artist=xmlutils.extract_subelem(track, "artist/name").text
            if self._artist != the_artist or self._name != the_name:
                result.append(TrackRequest(client=self._client,name=the_name,artist=the_artist))

        return result

class AlbumRequest(Request):

    def __init__(self,client,name,artist):
        super(AlbumRequest,self).__init__(client)
        self._name=name
        self._artist=artist

    def __repr__(self):
        return "AlbumRequest(%r,%r,%r)" % (self._client,self._name,self._artist)

    def getArtist(self):
        return self._artist

    def _getInfo(self,autocorrect=0,username=None,lang='en'):
        if autocorrect not in (0,1):
            raise errors.Error("wrong autocorrect supplied")

        return self._client.call_GET(method="album.getInfo",album=self._name,artist=self._artist.getName(),autocorrect=autocorrect,username=username,lang=lang)

    def getName(self):
        return self._name

    def getID(self):
        return xmlutils.extract_elem(self._getInfo(), ".//album/id").text

    def getURL(self):
        return xmlutils.extract_elem(self._getInfo(), ".//album/url").text

    def getReleaseDate(self):
        return xmlutils.extract_elem(self._getInfo(), ".//album/releasedate").text

    def getListeners(self):
        return xmlutils.extract_elem(self._getInfo(), ".//album/listeners").text

    def getPlayCount(self,username=None):
        return xmlutils.extract_elem(self._getInfo(username=username), ".//album/playcount").text

    def getImagesURLs(self):
        return [image.text for image in xmlutils.extract_elems(self._getInfo(),".//album/image")]

    def getWikiSummary(self):
        return xmlutils.extract_elem(self._getInfo(), ".//album/wiki/summary").text

    def getWikiContent(self):
        return xmlutils.extract_elem(self._getInfo(), ".//album/wiki/content").text

    def getTopTags(self):
        ret = self._getInfo()
        return [TagRequest(client=self._client,name=xmlutils.extract_subelem(tag,"name").text, url=xmlutils.extract_subelem(tag,"url").text) for tag in xmlutils.extract_elems(ret,".//toptags/tag")]

    def addTags(self,tags):
        if len(tags) > 10:
            raise errors.Error("too many tags supplied. Max 10 tags")

        ret=self._client.call_POST(method='album.addTags',album=self._name,artist=self._artist.getName(),tags=','.join(tag.getName() for tag in tags))
        return _statusHandler(ret)

    def removeTag(self,tag):
        ret=self._client.call_POST(method='album.removeTag',album=self._name,artist=self._artist.getName(),tag=tag.getName())
        return _statusHandler(ret)

    def getTags(self,autocorrect=0):
        if autocorrect not in (0,1):
            raise errors.Error("wrong autocorect supplied")

        ret=self._client.call_POST(method='album.getTags',album=self._name,artist=self._artist.getName(),autocorrect=autocorrect)
        return [TagRequest(client=self._client, name=xmlutils.extract_subelem(tag,"name").text, url=xmlutils.extract_subelem(tag,"url").text) for tag in xmlutils.extract_elems(ret,".//tags/tag")]

#TODO: refactor passing User objects instead of plain strings
    def share(self,recipients,message=None,public=0):
        if len(recipients) < 0 or len(recipients) > 10:
            raise errors.Error("wrong recipients count supplied")

        for user in recipients:
            if "@" in user and not ArtistRequest.re_email.match(user):
                raise errors.Error("wrong recipient supplied '%s'" % (user,))

        if public not in (0,1):
            raise errors.Error("wrong public supplied")

        ret=self._client.call_POST(album=self._name,artist=self._artist.getName(),method="album.share",message=message,public=public,recipient=','.join(recipients))
        return _statusHandler(ret)

    def getShouts(self,limit=50,autocorrect=0,page=None):
        if limit < 0:
            raise errors.Error("wrong limit supplied")
        if page:
            if page > limit:
                raise errors.Error("wrong page supplied")

        if autocorrect not in (0,1):
            raise errors.Error("wrong autocorrect supplied")

        ret=self._client.call_GET(method="album.getShouts",album=self._name,artist=self._artist.getName(),autocorrect=autocorrect,limit=limit,page=page)
        return _getShoutsHandler(ret)

    def search(self,limit=30,page=1):
        if limit < 0:
            raise errors.Error("wrong limit supplied")

        if page < 0 or page > limit:
            raise errors.Error("wrong page supplied")

        ret=self._client.call_GET(method="album.search",album=self._name,limit=limit,page=page)

        result=[]
        for album in xmlutils.extract_elems(ret,".//albummatches/album"):
            the_name = xmlutils.extract_subelem(album, "name").text
            the_artist = xmlutils.extract_subelem(album, "artist").text
            if self._name != the_name or self._artist.getName() != the_artist:
                result.append(AlbumRequest(client=self._client,name=the_name, artist=the_artist))
            else:
                if self not in result:
                    result.append(self)

        return result

    def getBuylinks(self,autocorrect=0,country='united kingdom'):
        """country: A country name, as defined by the ISO 3166-1 country names standard."""

        if autocorrect not in (0,1):
            raise errors.Error("wrong autocorrect supplied")

        ret=self._client.call_GET(method="album.getBuylinks",country=country,album=self._name,artist=self._artist.getName(),autocorrect=autocorrect)

        result=[]
        for affiliation in xmlutils.extract_elems(ret,".//affiliations/physicals/affiliation"):
                buyLink=xmlutils.extract_subelem(affiliation,".//buyLink").text
                result.append(buyLink)

        for affiliation in xmlutils.extract_elems(ret,".//affiliations/downloads/affiliation"):
                buyLink=xmlutils.extract_subelem(affiliation,".//buyLink").text
                result.append(buyLink)

        return result

class TagRequest(Request):
    def __init__(self,client,name,url):
        super(TagRequest, self).__init__(client)
        self._name = name
        self._url=url

    def __repr__(self):
        return 'TagRequest(%r,%r,%r)' % (self._client,self._name, self._url)

    def getName(self):
        return self._name

    def search(self,limit=30,page=1):
        if limit < 0:
            raise errors.Error("wrong limit supplied")

        if page < 0 or page > limit:
            raise errors.Error("wrong page supplied")

        ret=self._client.call_GET(method="tag.search",tag=self._name,limit=limit,page=page)

        result=[]
        for tag in xmlutils.extract_elems(ret,".//tagmatches/tag"):
            the_name=xmlutils.extract_subelem(tag,"name").text
            the_url = xmlutils.extract_subelem(tag,"url").text
            if self._name != the_name or self._url != the_url:
                result.append(TagRequest(client=self._client,name=the_name,url=the_url))
            else:
                if self not in result:
                    result.append(self)

    def _getInfo(self):
        return self._client.call_GET(method="tag.getInfo",tag=self._name)

    def getUrl(self):
        return self._url

    def getReach(self):
        return xmlutils.extract_elem(self._getInfo(),".//tag/reach").text

    def getTaggings(self):
        return xmlutils.extract_elem(self._getInfo(),".//tag/taggings").text

    def isStreamable(self):
        return xmlutils.extract_elem(self._getInfo(),".//tag/streamable").text == "1"

    def getWikiPublished(self):
        return xmlutils.extract_elem(self._getInfo(),".//tag/wiki/published").text

    def getWikiSummary(self):
        return xmlutils.extract_elem(self._getInfo(),".//tag/wiki/summary").text

    def getWikiContent(self):
        return xmlutils.extract_elem(self._getInfo(),".//tag/wiki/content").text

class LibraryRequest(Request):
    def __init__(self, client):
        super(LibraryRequest, self).__init__(client)

    def __repr__(self):
        return 'LibraryRequest(%r)' % (self._client, )

    def addAlbum(self, album):
        ret=self._client.call_POST(method="library.addAlbum", artist=album.getArtist().getName(), album=album.getName())
        return _statusHandler(ret)

    def addTrack(self, track):
        ret = self._client.call_POST(method="library.addTrack", artist=track.getArtist().getName(), track=track.getName())
        return _statusHandler(ret)

    def addArtist(self, artist):
        ret=self._client.call_POST(method="library.addArtist", artist=artist.getName())
        return _statusHandler(ret)
