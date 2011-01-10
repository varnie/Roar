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
        print "venue.getPastEvents: ", venue.getPastEvents()
        print "venue.search: ",  venue.search(1,1)

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
        print "artist.getShouts: ", artist.getShouts(2)
        print "artist.getSimilar: ",artist.getSimilar()
        print "artist.share: ",artist.share(["varnie"],"tettttwoho! cool band!11")
        print "artist.shout: ",artist.shout("Horns up\m/")
        print "artist.search: ", artist.search()
        print "artist.getEvents: ",artist.getEvents()
        print "artist.getImages: ", artist.getImages()
        print "artist.getTopAlbums: ", artist.getTopAlbums()
        print "artist.getTopFans: ", artist.getTopFans()
        print "artist.getTopTags: ", artist.getTopTags()
        print "artist.getTopTracks: ", artist.getTopTracks()
        print "artist.getPastEvents: ", artist.getPastEvents()

        print "track APIs"
        track=requests.TrackRequest(client,"LAM","Behemoth")
        print "track.share: ", track.share(["varnie"],"tetwoo! this track is shared with you") 
        print "track.addTags: ", track.addTags(tags)
        print "track.getTags: ", track.getTags()
        print "track.removeTag: "
        for tag in tags:
            print track.removeTag(tag),
        print ""
        print "track.getShouts: ", track.getShouts(2)

        print "user APIs"
        user=requests.UserRequest(client,"varnie")
        print "user.shout: ", user.shout("this is a test message")
        print "user.getShouts: ",user.getShouts(2) 

        print "album APIs"
        album=requests.AlbumRequest(client,"Demigod","Behemoth")
        print "album.share: ", album.share(["varnie"],"album share")
        print "album.addTags: ", album.addTags(tags)
        print "album.getTags: ", album.getTags()
        print "album.removeTag: ",
        for tag in tags:
            print album.removeTag(tag),
        print ""
        print "album.getShouts: ",album.getShouts(2)
        print "album.getName: ", album.getName()
        print "album.getID: ", album.getID()
        print "album.getURL: ", album.getURL()
        print "album.getReleaseDate: ", album.getReleaseDate()
        print "album.getListeners: ", album.getListeners()
        print "album.getPlayCount: ", album.getPlayCount()
        print "album.getImagesURLs: ", album.getImagesURLs()
        print "album.getTopTags: ", album.getTopTags()
        print "album.getBuylinks: ", album.getBuylinks()

        print "user APIs"
        user=requests.UserRequest(client=client,name='varnie')
        print "user.shout: ", user.shout("this is a test message")
        print "user.getShouts: ", user.getShouts()

    except errors.Error, e:
       print e
