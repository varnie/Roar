import requests
import errors
import auth

if __name__=="__main__":

    #setup required data
    auth.URL="ws.audioscrobbler.com"
    api_key=raw_input("Please enter your api_key: ")
    secret=raw_input("Please enter your secret: ")
    username=raw_input("Please enter your username: ")
    userpass=raw_input("Please enter your userpass: ")

    auth.newAuthData(api_key,secret,username,userpass)

    #do smth interesting!
    try:
        #event APIs
        event=requests.EventRequest(1073657)
        print "constructing event: ",event
        print "event.getArtists: ", event.getArtists()
        print "event.getDescription: ",event.getDescription()
        print "event.getAttendance: ",event.getAttendance()
        print "event.getTitle: ", event.getTitle()
        print "event.getUrl: ", event.getUrl()
        print "event.getReviews: ", event.getReviews()
        print "event.getStartDate: ",event.getStartDate()
        print "event.getImages: ",event.getImages()
        print "event.getWebsite: ",event.getWebsite()

        #venue APIs
        venue=event.getVenue()
        print "event.getVenue: ",venue
        print "venue.getEvents: ", venue.getEvents()
        print "venue.getPastEvents: ", venue.getPastEvents()
        print "venue.search: ",  venue.search(1,1)

        #artist APIs
        artist=requests.ArtistRequest("Sepultura")
        print "constructing an artist", artist
        print "artist.getCorrection: ",artist.getCorrection()
        tags=["metal","black","death","ZZZ"]
        print "artist.addTags: ", artist.addTags(tags)
        print "artist.getTags: ", artist.getTags()
        print "artist.removeTag: "
        for tag in tags:
            print artist.removeTag("metal"),
        print ""
        print "artist.getShouts: ", artist.getShouts(2)
        print "artist.getSimilar: ",artist.getSimilar(2)
        print "artist.share: ",artist.share(["varnie"],"tettttwoho! cool band!11")
        print "artist.shout: ",artist.shout("Horns up\m/")
        print "artist.search: ", artist.search(2)
        print "artist.getEvents: ",artist.getEvents()

        #user APIs
        print "user.shout: ", requests.UserRequest("user_name").shout("this is a test message")
    except errors.Error, e:
       print e
