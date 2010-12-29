class Error(Exception):
        def __init__(self, *args, **kwargs):
            super(Error, self).__init__(*args, **kwargs)

class BadResponseError(Error):
    def __init__(self):
        super(BadResponseError, self).__init__()

    def __str__(self):
        return "Wrong response"

class ResponseError(Error):
    def __init__(self, errorCode, errorMsg, *args, **kwargs):
        super(ResponseError, self).__init__(*args, **kwargs)
        self._errorCode=errorCode
        self._errorMsg=errorMsg

    def __str__(self):
        return "LastFM Error %s:%s" % (self._errorCode, self._errorMsg)