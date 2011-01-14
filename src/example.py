import impl.requests as requests
import impl.errors as errors

if __name__=="__main__":

    #setup required data
    URL="ws.audioscrobbler.com"

    api_key=raw_input("Please enter your api_key: ")
    api_secret=raw_input("Please enter your secret: ")
    username=raw_input("Please enter your username: ")
    userpass=raw_input("Please enter your userpass: ")

    #do smth interesting!
    try:
        client=requests.Client(URL,api_key,api_secret,username,userpass)

        print "event APIs"
        event=requests.EventRequest(client,1073657)
        print "event.share: ", event.share(["varnie"],"this event is shared with you!")
        print "event.getArtists: ", event.getArtists()
        print "event.getDescription: ",event.getDescription()
        print "event.getAttendance: ",event.getAttendance()
        print "event.getTitle: ", event.getTitle()
        print "event.getUrl: ", event.getUrl()
        print "event.getReviews: ", event.getReviews()
        print "event.getStartDate: ",event.getStartDate()
        print "event.getImagesURLs: ",event.getImagesURLs()
        print "event.getWebsite: ",event.getWebsite()
        print "event.getAttendees: ", event.getAttendees()
        print "event.attend: ", event.attend(0)

        print "venue APIs"
        venue=event.getVenue()
        print "event.getVenue: ",venue
        print "venue.getEvents: ", venue.getEvents()
        print "venue.getPastEvents: ", venue.getPastEvents(limit=5)
        print "venue.search: ",  venue.search(limit=5)

        print "artist APIs"
        artist=requests.ArtistRequest(client,"Sepultura")
        print "artist.getCorrection: ",artist.getCorrection()
        tags=["metal","black","death","ZZZ"]
        print "artist.addTags: ", artist.addTags(tags)
        print "artist.getTags: ", artist.getTags()
        print "artist.removeTag: "
        for tag in tags:
            print artist.removeTag(tag),
        print ""
        print "artist.getShouts: ", artist.getShouts(limit=5)
        print "artist.getSimilar: ",artist.getSimilar(limit=5)
        print "artist.share: ",artist.share(["varnie"],"tettttwoho! cool band!11")
        print "artist.shout: ",artist.shout("Horns up\m/")
        print "artist.search: ", artist.search(limit=5)
        print "artist.getEvents: ",artist.getEvents()
        print "artist.getImages: ", artist.getImages(limit=5)
        print "artist.getTopAlbums: ", artist.getTopAlbums()
        print "artist.getTopFans: ", artist.getTopFans()
        print "artist.getTopTags: ", artist.getTopTags()
        print "artist.getTopTracks: ", artist.getTopTracks()
        print "artist.getPastEvents: ", artist.getPastEvents(limit=5)
        print "artist.isStreamable: ", artist.isStreamable()
        print "artist.getListeners: ", artist.getListeners()
        print "artist.getPlayCount: ", artist.getPlayCount()
        print "artist.getBioSummary: ", artist.getBioSummary()
        print "artist.getBioContent: ", artist.getBioContent()

        print "track APIs"
        track=requests.TrackRequest(client,"LAM","Behemoth")
        print "track.share: ", track.share(["varnie"],"tetwoo! this track is shared with you") 
        print "track.addTags: ", track.addTags(tags)
        print "track.getTags: ", track.getTags()
        print "track.removeTag: "
        for tag in tags:
            print track.removeTag(tag),
        print ""
        print "track.getCorrection: ", track.getCorrection()
        print "track.getSimilar: ", track.getSimilar(limit=5)
        print "track.getTopFans: ", track.getTopFans()
        print "track.getTopTags: ", track.getTopTags()
        print "track.getShouts: ", track.getShouts(limit=5)
        print "track.getName: ", track.getName()
        print "track.getUrl: ", track.getUrl()
        print "track.getID: ", track.getID()
        print "track.getDuration: ", track.getDuration()
        print "track.getListeners: ", track.getListeners()
        print "track.getPlaycount: ", track.getPlaycount()
        print "track.getAlbum: ", track.getAlbum()
        print "track.ban: ", track.ban()
        print "track.unban: ", track.unban()
        print "track.love: ", track.love()
        print "track.unlove: ", track.unlove()
        print "track.getArtist: ", track.getArtist()
        print "track.getBuylinks: ", track.getBuylinks()
        print "track.search: ", track.search(limit=5)

        print "album APIs"
        album=requests.AlbumRequest(client,"Demigod","Behemoth")
        print "album.share: ", album.share(["varnie"],"album share")
        print "album.addTags: ", album.addTags(tags)
        print "album.getTags: ", album.getTags()
        print "album.removeTag: ",
        for tag in tags:
            print album.removeTag(tag),
        print ""
        print "album.getShouts: ",album.getShouts(limit=5)
        print "album.getName: ", album.getName()
        print "album.getID: ", album.getID()
        print "album.getURL: ", album.getURL()
        print "album.getReleaseDate: ", album.getReleaseDate()
        print "album.search: ", album.search(limit=5)
        print "album.getListeners: ", album.getListeners()
        print "album.getPlayCount: ", album.getPlayCount()
        print "album.getImagesURLs: ", album.getImagesURLs()
        print "album.getTopTags: ", album.getTopTags()
        print "album.getBuylinks: ", album.getBuylinks()
        print "album.getPlayCount: ", album.getPlayCount()
        print "album.getWikiSummary: ", album.getWikiSummary()
        print "album.getWikiContent: ", album.getWikiContent()

        print "user APIs"
        user=requests.UserRequest(client=client,name='varnie')
        print "user.shout: ", user.shout("this is a test message")
        print "user.getShouts: ", user.getShouts()

        print "tags APIs"
        tag=requests.TagRequest(client=client,name='black metal')
        print "tag.getName: ", tag.getName()
        print "tag.getUrl: ", tag.getUrl()
        print "tag.search: ", tag.search()
        print "tag.getReach: ", tag.getReach()
        print "tag.isStreamable:  ", tag.isStreamable()
        print "tag.getTaggings: ", tag.getTaggings()
        print "tag.getWikiPublished: ", tag.getWikiPublished()
        print "tag.getWikiSummary: ", tag.getWikiSummary()
        print "tag.getWikiContent: ", tag.getWikiContent()
    except errors.Error, e:
       print e
