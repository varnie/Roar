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
        event=requests.EventRequest(1073657)
        print event.getArtists()
        print event.getDescription()
        artist=requests.ArtistRequest("Sepultura")

        print "artist.getCorrection: ",artist.getCorrection()
        tags=["metal","black","death","ZZZ"]
        print artist.addTags(tags)
        print "artist.getTags: "
        for tag in artist.getTags():
            print tag,
        print ""
        print "artist.removeTag: "
        for tag in tags:
            print artist.removeTag("metal"),
        print ""
        print "artist.getShouts: ", artist.getShouts(4)
        print "artist.getSimilar: ",artist.getSimilar(2)
        print "artist.share: ",artist.share(["varnie"],"tettttwoho! cool band!11")
        print "artist.shout: ",artist.shout("I\
                glad Behemoth became an artist of the year 2010 in Poland!\
                Horns up\m/")
        print "artist.search: ", artist.search(3)
        print "artist.getEvents: ",artist.getEvents()

        print "user.shout: ", requests.UserRequest("user_name").shout("this is a test message")
    except errors.Error, e:
       print e
