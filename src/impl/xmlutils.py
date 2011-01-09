import xml.etree.ElementTree as xml

def extract_elem(body, elemName, searchInRoot=False):
    return XMLParser(body).extract_elem(elemName,searchInRoot)

def extract_elems(body, elemName):
    return XMLParser(body).extract_elems(elemName)

def extract_subelems(ownerElem, elemName):
    return ownerElem.findall(elemName)

def extract_subelem(ownerElem, elemName):
    return ownerElem.find(elemName)

class XMLParser(object):

    def __init__(self,XMLbody):
	super(XMLParser,self).__init__()
	self._XMLbody=XMLbody
	self._xmlTree=self._createXMLTree()

    def __repr__(self):
	return 'XMLParser(%r)' % (self._XMLbody,)

    def _createXMLTree(self):
        parser=xml.XMLTreeBuilder()
        parser.feed(self._XMLbody)
        return xml.ElementTree(parser.close())

    def extract_elems(self, elemName):
        return self._xmlTree.findall(elemName)

    def extract_elem(self, elemName, searchInRoot=False):
        if searchInRoot:
            return self._xmlTree.getroot().get(elemName)
        else:
            return self._xmlTree.find(elemName)
