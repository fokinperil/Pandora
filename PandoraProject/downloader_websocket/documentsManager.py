import socket, select
import http.client
from urllib.parse import urlparse
import threading, sys, time
import hashlib, random
import os, json, re
import bson
import constants

class PandoraDocument:

    def __init__(self, **kwargs):
        self.parent = kwargs.get('parent')

        # Runtime var
        self.fd = None
        self.reader = None
        self._http = None

        # DB var
        self._id = kwargs.get('_id')
        self.str_id = kwargs.get('str_id')
        self.owner = kwargs.get('owner')
        self.str_owner = kwargs.get('str_owner')
        self.allowed = kwargs.get('allowed')
        self.owner_island = kwargs.get('owner_island')
        self.name = kwargs.get('name')
        self.file_location = kwargs.get('file_location')
        self.save_location = kwargs.get('save_location')
        self.branch = kwargs.get('branch')
        self.hostname = kwargs.get('hostname')
        self.port = kwargs.get('port')
        self.protocol = kwargs.get('protocol')
        self.get = kwargs.get('get')
        self.state = kwargs.get('state')
        self.size = kwargs.get('size')
        self.timestamp = kwargs.get('timestamp')
        self.left = kwargs.get('left')

    def __repr__(self):
        return "<DocumentManager.Document id=%s, owner=%s, save_location=%s, hostname=%s, port=%s, protocol=%s, get=%s, state=%d, left=%d, name=%s>" % (
            self._id,
            self.owner,
            self.save_location,
            self.hostname,
            self.port,
            self.protocol,
            self.get,
            self.state,
            self.left,
            self.name
        )

    def shareExists(self, uid):
        for share in self.allowed:
            if share.get('_id') == uid:
                return True
        return False

    def removeShare(self, s_obj):
        self.allowed.remove(s_obj)

    def open_fd(self):
        """"""
        try:
            self.fd = open(self.save_location, 'ab') # Open in append-binary mode.
            print ("Document object # Document file opened.")
            return True
        except:
            print ("Document object # Unable to open file.")
            return False

    def close_fd(self):
        self.fd.close()
        return True

    def write_fd(self, data):
        """"""
        try:
            self.fd.write(data)
            return True
        except:
            print ("Document object # Unable to write data in file.")
            return False

    def read_sock(self):
        recv = self.reader.read(4096)
        if self.write_fd(recv):
            self.left -= len(recv)
        else:
            print ("Document object # Unable to write to file.")
            return False
        return True

    def close_sock(self):
        self.reader.close()
        return True

    def close_all(self):
        if self.reader is not None:
            self.reader.close()
        self.fd.close()
        return True

    def _raise(self):
        """"""
        print ("Document object # Starting Document... %s" % (self))

        if not self.open_fd():
            return False

        try:
            if self.protocol == 'http':
                self._http = http.client.HTTPConnection(self.hostname, port=self.port)
            elif self.protocol == 'https':
                self._http = http.client.HTTPSConnection(self.hostname, port=self.port)
        except:
            print ("Document object # Unable to create HTTP/HTTPSConnection.")
            return False
        print ("Document object # HTTP/HTTPSConnection object created.")

        # Requesting the file
        try:
            print ("Requesting GET=%s" % (self.get))
            self._http.request("GET", self.get, None, {
                "Connection": "keep-alive",
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'fr-FR,fr;q=0.8,en-US;q=0.6,en;q=0.4',
                'Accept-Encoding': 'gzip',
                'Upgrade-Insecure-Requests': '1',
                "User-Agent": "User-Agent: Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chromeupda45.0.2454.85 Safariupda537.36",
                "Range": "bytes=%d-%d" % ((self.size - self.left), self.size)
            })
            self.reader = self._http.getresponse()
            check_length = self.reader.getheader('content-length')
            print ("check_length: %s" % (check_length))
            if check_length and int(check_length) != self.left:
                print ("Document object # Size of file on server changed since last check.")
                self.close_all()
                return False
        except:
            self.close_all()
            print ("Document object # Unable to get HTTPResponse object back.")
            return False

        print ("Document object # HTTPResponse object fetched.")

        http_code = self.reader.getcode()
        print ("Code: %d" % (http_code))
        if http_code != 206 and http_code != 200:
            print ("Document object # Wrong HTTP code: %d" % (http_code))
            self.close_all()
            return False

        self.state = constants._STATE_RAISING_
        self.parent.http_socks.append(self.reader)
        self.parent.httpobject_table.update({self.reader: self})
        return True

    def rest(self):
        self.parent.http_socks.remove(self.reader)
        del self.parent.httpobject_table[self.reader]
        self.close_all()
        self.state = constants._STATE_REST_
        print ("Document object # Document paused.")
        return True


class DocumentsManager:

    def __init__(self, db_ref, f_ptr_download_done):
        self.mongo_database = db_ref
        self.done_callback = f_ptr_download_done

        self.documentsTable = {}
        self.httpobject_table = {}

        # Select
        self.http_socks = [] # Socket to read

        # Pause
        self.rest_queue = []

        self.init_Documents()

        self.process_documents_thread = threading.Thread(target=self.process_documents, daemon=True).start() # Process to the downloading in a new thread

    def docExists(self, doc_id):
        return True if type(self.documentsTable.get(doc_id)) != type(None) else False

    def getDoc(self, doc_id):
        return self.documentsTable.get(doc_id)

    def removeDoc(self, doc_id):
        del self.documentsTable[doc_id]

    def init_Documents(self):
        documents = self.mongo_database.documents.find() # Fetch all Documents

        # Initialize Documents objects
        for doc in documents:
            if doc.get('state') != constants._STATE_BURGEON_: # If we already received bytes from this document
                if os.path.isfile(doc.get('save_location')):
                    fsize = os.stat(doc.get('save_location')).st_size

                    if fsize == doc.get('size') and doc.get('state') != constants._STATE_WOODSPRITE_: # Document is done but not correctly updated
                        doc['left'] = 0
                        doc['state'] = constants._STATE_WOODSPRITE_
                        database_response = self.mongo_database.documents.update_one({'_id': doc.get('_id')}, { "$set": { 'left': doc.get('left'), 'state': doc.get('state') } } )
                        if database_response.modified_count < 1:
                            print ("Unable to update to done document.")

                    elif doc.get('left') != doc.get('size') and doc.get('state') == constants._STATE_BURGEON_: # Document started but not correctly updated
                        doc['state'] = constants._STATE_RAISING_ # Set on active document
                        database_response = self.mongo_database.documents.update_one({'_id': doc.get('_id')}, { "$set": { 'state': doc.get('state') } } )
                        if database_response.modified_count < 1:
                            print ("Unable to update active document.")

                    elif fsize != doc.get('size') - doc.get('left'):
                            print ("document stats missed some bytes, patching ...")
                            doc['left'] = doc.get('size') - fsize
                            database_response = self.mongo_database.documents.update_one({'_id': doc.get('_id')}, { "$set": { 'left': doc.get('left') } } )
                            if database_response.modified_count < 1:
                                print ("Unable to patch document data left in database.")

                else:
                    print ("(init_Documents) # document file does not exist anymore, document will be removed.")
                    d_id = doc.get('_id');
                    for _id in doc.get('allowed'):
                        user = self.mongo_database.users.find_one({'_id': _id})
                        if not user:
                            print ("Unable to get user database entry.")
                        else:
                            database_response = self.mongo_database.users.update_one({'_id': _id}, { "$pull": {'registry': d_id } } )
                            if database_response.modified_count < 1:
                                print ("Unable to remove user registry entry.")

                    database_response = self.mongo_database.documents.delete_one( {'_id': d_id} )
                    if database_response.deleted_count < 1:
                        print ("Unable to remove document from documents collection.")

            d_obj = PandoraDocument(
                parent = self,
                _id = doc.get('_id'),
                str_id = str(doc.get('_id')),
                owner = doc.get('owner'),
                str_owner = doc.get('str_owner'),
                allowed = doc.get('allowed'),
                owner_island = doc.get('owner_island'),
                name = doc.get('name'),
                branch = doc.get('branch'),
                file_location = doc.get('file_location'),
                save_location = doc.get('save_location'),
                hostname = doc.get('hostname'),
                port = doc.get('port'),
                protocol = doc.get('protocol'),
                get = doc.get('get'),
                state = doc.get('state'),
                size = doc.get('size'),
                timestamp = doc.get('timestamp'),
                left = doc.get('left')
            )

            self.documentsTable.update( {doc.get('_id'): d_obj} )

            if d_obj.state == constants._STATE_RAISING_: # Last state was downloading
                if not d_obj._raise():
                    print ("(init_Documents) Document object state was set to 1, but unable to start document.")

        print("Documents initialized: ")
        print(self.documentsTable)
        return True




    def get_new_id(self):
        sc_t = str(time.time())
        s = str(random.randrange(0, 128000))
        return hashlib.sha1(bytes(sc_t+s, 'ISO 8859-1')).hexdigest()

    def get_ext(self, s):
        reg = re.search("(.*?)\.", s.strip('/')[::-1])
        if reg:
            return reg.group(0)[::-1]
        return False

    def url_split(self, url):
        e_url = urlparse(url)
        if e_url.hostname and e_url.scheme and e_url.path: # if urlparse returned minimal configuration
            if e_url.scheme not in ('http', 'https'):
                print ("url_split # Scheme is not in ('http', 'https')")
                return None
            return (e_url.hostname,
                    e_url.port,
                    e_url.scheme,
                    e_url.path) if e_url.port else (e_url.hostname,
                                                    80,
                                                    e_url.scheme,
                                                    e_url.path) if e_url.scheme == 'http' else (e_url.hostname,
                                                                                                443,
                                                                                                e_url.scheme,
                                                                                                e_url.path)
        else: # else urlparse returned bad configuration
            return None

    def get_headers(self, hostname, port, protocol, get):
        try:
            if protocol == 'http':
                http_conn = http.client.HTTPConnection(hostname, port)
            elif protocol == 'https':
                http_conn = http.client.HTTPSConnection(hostname, port)
            http_conn.request("GET", get, headers={'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                                                   'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.85 Safari/537.36',
                                                   'Accept-Language': 'fr-FR,fr;q=0.8,en-US;q=0.6,en;q=0.4',
                                                   'Accept-Encoding': 'gzip',
                                                   'Upgrade-Insecure-Requests': '1'})
            http_response = http_conn.getresponse()
            if http_response.status != 200: # 200 is the only acceptable satus code here.
                print ("(get_headers) HTTP Error: " + str(http_response.status))
                return None
            http_conn.close()
            return http_response
        except:
            if protocol == 'https':
                print ("get_headers # Unable to query headers, SSL Certificate verification probably failed.")
            else:
                print ("get_headers # Unable to query headers.")
            return None

    def new_document(self, file_location, save_location, branch, name, owner_island, owner, str_owner):

        _id = bson.ObjectId() # Generate new _id value

        spl_url = self.url_split(file_location) # Extract url elements
        if not spl_url:
            print ("(new_document) Unable to handle URL.")
            return None

        hostname, port, protocol, get = spl_url

        ext = self.get_ext(get)
        if ext:
            name += ext
            save_location += ext

        # Checking if filename is available in filesystem
        try:
            fd = open(save_location, 'w+')
            fd.close()
        except:
            print ("+ new_document -> Unable to create file in file system, it probably already exists as a sub directory or normal file.")
            return None

        timestamp = int(time.time())

        http_obj = self.get_headers(hostname, port, protocol, get)
        if http_obj == None:
            print ("(new_document) Unable to get HTTP Response for headers.")
            return None

        size = http_obj.getheader("Content-Length")
        if size == None:
            print ("(new_document) Unable to extract headers value.")
            return None

        size = int(size)

        print ("Instantiating ...")
        D_obj = PandoraDocument(
            parent = self,
            _id = _id,
            str_id = str(_id),
            owner = owner,
            str_owner = str_owner,
            allowed = [{'_id': owner, 'name': str_owner}],
            owner_island = owner_island,
            name = name,
            save_location = save_location,
            file_location = file_location,
            branch = branch,
            hostname = hostname,
            port = port,
            protocol = protocol,
            get = get,
            state = constants._STATE_BURGEON_,
            size = size,
            timestamp = timestamp,
            left = size
        )

        print ("D_obj instantiated")

        document = {
            '_id': _id,
            'owner': owner,
            'str_owner': str_owner,
            'allowed': [{'_id': owner, 'name': str_owner}],
            'owner_island': owner_island,
            'name': name,
            'save_location': save_location,
            'file_location': file_location,
            'branch': branch,
            'hostname': hostname,
            'port': port,
            'protocol': protocol,
            'get': get,
            'state': constants._STATE_BURGEON_,
            'size': size,
            'timestamp': timestamp,
            'left': size
        }

        try:
            self.mongo_database.documents.insert_one(document)
        except:
            print("+ new_document -> Unable to insert document in documents collection.")
            return False

        self.documentsTable.update( { _id: D_obj } )

        return D_obj

    def signal_rest(self, D_obj):
        try:
            print ("Signaling pause...")
            self.rest_queue.append(D_obj)
            while D_obj in self.rest_queue:
                pass
            return True
        except:
            return False

    def process_documents(self):
        print ("(process_documents) Documents thread started !")

        while True:
            for D_obj in list(self.rest_queue):
                print ("Pause signal received.")
                D_obj.rest()
                self.rest_queue.remove(D_obj)

            if len(self.http_socks) > 0:
                for update in list(self.http_socks):
                    D_obj = self.httpobject_table[update]
                    if update.isclosed():
                        print ("process_documents # HTTP Socket closed, pausing document...")
                        D_obj.rest()
                        self.pause.remove(D_obj)
                        continue

                    # Some stuff there
                    D_obj.read_sock()

                    if D_obj.left == 0:
                        print ("(process_documents) Document of (" + D_obj.str_id + ") is done.")
                        self.http_socks.remove(update)
                        D_obj.close_all()
                        D_obj.state = constants._STATE_WOODSPRITE_

                        self.done_callback(D_obj)
                    elif D_obj.left < 0:
                        print ("(process_documents) Error with document of (" + str(D_obj.id) + "), received too much bytes.")
                        self.http_socks.remove(update)
                        D_obj.close_all()
                        D_obj.state = constants._STATE_WOODSPRITE_
