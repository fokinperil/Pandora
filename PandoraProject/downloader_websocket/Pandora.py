import      socket, time, json, hashlib, random, sys, os, constants, bson, shutil, re
from        threading                                                                               import Thread
from        SimpleWebSocketServer.SimpleWebSocketServer                                             import WebSocket, SimpleSSLWebSocketServer, SimpleWebSocketServer
from        pymongo                                                                                 import MongoClient
import      PandoraUtils
from        documentsManager                                                                        import DocumentsManager

# Git update 0x1

class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, bson.ObjectId):
            return str(o)
        return json.JSONEncoder.default(self, o)

def requireEywa(method):
    def f_wrap(*args):
        # arg[1] is the client instance passed as argument to dispatcher routines
        if not args[1].eywa_status:
            print ("Client tried to call a routine protected by Eywa without being connected to Eywa.")
            return False
        return method(*args)
    return f_wrap

class PandoraCitizen:

    def __init__(self, u_info):
        self._id = u_info.get('_id')
        self.name = u_info.get('name')
        self.pwd = u_info.get('pwd')
        self.registry = u_info.get('registry')
        self.island = u_info.get('island')
        self.token_check = u_info.get('token_check')
        self.auth_instances = []
        self.branches = u_info.get('branches')
        self.token_registry = u_info.get('token_registry')
        self.avatar = u_info.get('avatar')
        self.sharing_queue = u_info.get('sharing_queue')

    def updateTokenCheck(self, n_value):
        self.token_check = n_value

    def updateAvatar(self, n_avatar):
        self.avatar = n_avatar

    def inRegistry(self, burgeon_id):
        return burgeon_id in self.registry

    def inSharingQueue(self, burgeon_id):
        return burgeon_id in self.sharing_queue

    def pushRegistry(self, burgeon):
        self.registry.append(burgeon)

    def removeRegistry(self, burgeon):
        self.registry.remove(burgeon)

    def pushAuth(self, client):
        self.auth_instances.append(client)

    def removeAuth(self, client):
        self.auth_instances.remove(client)

    def pushQueue(self, s):
        self.sharing_queue.append(s)

    def removeQueue(self, s):
        self.sharing_queue.remove(s)

class PandoraHandler(WebSocket):

    def handleMessage(self):
        if self.data == constants._PING_: # ping
            self.sendMessage(constants._PONG_)
            return True

        print ("Received data frame: " + self.data)
        packet = json.loads(self.data)
        pid = packet.get('id')

        print ("Dispatching on %d ..." % (pid))
        pandora.Dispatcher.dispatch(pid, self, packet)

        return True

    def handleConnected(self):
        print ('[' + self.address[0] + ':' + str(self.address[1]) + '] connected.')
        print (self)
        self.eywa_status = False # Set the Eywa connection attribute

    def handleClose(self):
        print ("connection closed")
        print ('[' + self.address[0] + ':' + str(self.address[1]) + '] closed.')

        print (pandora)
        pandora.disconnectCitizen(self)

class PandoraDispatcher:

    def __init__(self, server):
        self.PandoraServer = server
        self.encode = self.PandoraServer.encode # Save the reference of the encoder function to encode packets

        # Each index represent a pointer to the corresponding method to dispatch
        self.dispatchTable = [
            self.Eywa,                              #  0  | Eywa(), connection
            self.buildBranch,                       #  1  | buildBranch(), Create a new empty branch without any burgeon
            self.destructBranch,                    #  2  | destructBranch(), Destruct an entire branch with all his burgeons
            self.createBurgeon,                     #  3  | createBurgeon(), Create a new burgeon on a branch
            self.raiseBurgeon,                      #  4  | raiseBurgeon(), Make the burgeon grow
            self.restBurgeon,                       #  5  | restBurgeon(), Let some rest to the burgeon
            self.destructBurgeon,                   #  6  | destructBurgeon(), Destruct a burgeon on a branch
            self.releaseBurgeon,                    #  7  | releaseBurgeon(), Release a burgeon on a branch, he will be considered as free and no reference would be saved of him
            self.relocateBurgeon,                   #  8  | relocateBurgeon(), Relocate a burgeon to an another branch
            self.shareBurgeon,                      #  9  | shareBurgeon(), Share a burgeon to an another account
            self.shareBurgeonHandshake,             #  10 | shareBurgeonHandshake(), Handle answer from a shared account
            self.unshareBurgeon,                    #  11 | unshareBurgeon(), Unshare a burgeon to a shared account
            self.changeNavi                         #  12 | changeNavi(), Change avatar
        ]

        self.dispatchTableSz = len(self.dispatchTable)

    # Dispatch() function takes 3 arguments, the index to retrieve the routine pointer from the dispatch table,
    #                                        the client instance for the dispatched method
    #                                        the packet reference for the dispatched method
    def dispatch(self, index, client, packet):
        if ( index > self.dispatchTableSz ):
            print ("No dispatch available for this index.")
            return False

        print ("Calling routine at %d in dispatch table." % (index))
        self.dispatchTable[index](client, packet)

    def sendAll(self, client, packet):
        for _client in list(client.citizen.auth_instances):
            try:
                _client.sendMessage(self.encode(packet))
            except:
                print ("+ sendAll -> Unable to send broadcast message to this client, probably deconnected.")

    def withEywa(self, index, client):
        if not client.eywa_status:
            print ("(" + str(index) + ") Try by not authenticated client.")
            client.sendMessage(json_encoder.encode({'id': index, 'status': 0x0}))
            return False
        return True

    # Methods ... Each method takes 2 arguments without taking care account of the instance (self), which are the client instance to communicate with him
    #                                                                                                         the packet to retrieve information for the dispatched method

    def Eywa(self, client, packet):
        # ...
        navi = str(packet.get('username')).upper()
        navi_entry = self.PandoraServer.mongoDB.users.find_one( {'name': navi} )
        print (navi_entry)

        if not navi_entry:
            print ("(auth) Client: Bad username.")
            client.sendMessage(self.encode({'id': constants._EYWA_, 'status': 0x0, 'is_token': packet.get('is_token'), 'expired': 0, 'message': '(100) Bad username.'}))
            return False

        _id = navi_entry.get('_id')

        c_time = int(time.time())
        if navi_entry.get("token_check") < c_time:
            # Trigger tokens validity check
            bulk = self.PandoraServer.mongoDB.users.initialize_unordered_bulk_op()
            for token in list(navi_entry.get("token_registry")):
                if navi_entry['token_registry'][token].get('expire') < c_time:
                    # Token has expired
                    del navi_entry['token_registry'][token]
                    print ("$unset -> " + 'token_registry.' + token)
                    bulk.find({'_id': _id}).update({'$unset': {'token_registry.' + token : 0}})

            next_check = c_time + 3600
            navi_entry['token_check'] = next_check
            bulk.find({'_id': _id}).update({'$set': {'token_check': next_check}})
            try:
                bulk.execute()
                print ("+ login -> Token check successfully proceed. Next at %d" % (next_check))
            except:
                print ("+ login -> Bulk_op Database error.")
                print (sys.exc_info()[0])

        if packet.get('is_token'):
            # Token login

            token = packet.get('login_token')

            token_entry = get_client_token(navi_entry, navi, client.address[0], token)
            print("Token get: %s" % (token_entry))
            if token_entry:
                if token_entry.get('expire') < c_time:
                    del navi_entry['token_registry'][token]

                    try:
                        self.PandoraServer.mongoDB.users.update_one( {'_id': _id}, {'$unset': {'token_registry.' + token: 0 } } )
                    except:
                        print ("+ login -> Database error while deleting token.")
                        client.sendMessage(self.encode({'id': constants._EYWA_, 'status': 0x0, 'is_token': 1, 'expired': 1, 'message': '(100) Databse error.'}))
                        return False

                    print ("+ login -> Client: token expired.")
                    client.sendMessage(self.encode({'id': constants._EYWA_, 'status': 0x0, 'is_token': 1, 'expired': 1, 'message': '(100) Token expired.'}))
                    return False

                if not _id in self.PandoraServer.citizenTable:
                    navi_entry['island'] = self.PandoraServer.conf.get('storage').get('world') + navi_entry.get('name') + '/'
                    citizen_instance = PandoraCitizen(navi_entry)
                    self.PandoraServer.citizenTable.update({_id: citizen_instance})

                client._id = _id
                client.citizen = self.PandoraServer.getCitizen(_id)
                client.eywa_status = True

                client.citizen.pushAuth(client)

                client.sendMessage(self.encode({'id': constants._EYWA_, 'status': 0x1, 'avatar': user_entry.get('avatar'), 'username': username, 'is_token': 1, 'message': '(100) Authenticated.'}))
                print ("(auth) New client authed with token: " + str(client))
            else:
                print ("(auth) Client: Bad ip/token.")
                client.sendMessage(self.encode({'id': constants._EYWA_, 'status': 0x0, 'is_token': 1, 'expired': 0, 'message': '(100) Bad ip/token.'}))
                return False

        else:
            pwd = packet.get('pwd')
            if PandoraUtils.login(navi_entry.get('pwd'), pwd):
                client_token = PandoraUtils.generate_client_token()
                expire = int(time.time()) + 3600
                navi_entry['token_registry'].update({client_token: {"ip": client.address[0], "expire": expire}}) # Add token entry with 1 hour expire

                try:
                    self.PandoraServer.mongoDB.users.update_one( {'_id': navi_entry.get('_id')}, {'$set': {'token_registry.' + client_token: navi_entry['token_registry'].get(client_token) }})
                except:
                    print ("+ login -> Database error while updating user token registry.")
                    client.sendMessage(self.encode({'id': constants._EYWA_, 'status': 0x0, 'is_token': 0, 'message': '(100) Databse error.'}))
                    return False

                if not _id in self.PandoraServer.citizenTable:
                    navi_entry['island'] = self.PandoraServer.conf.get('storage').get('world') + navi_entry.get('name') + '/'
                    citizen_instance = PandoraCitizen(navi_entry)
                    self.PandoraServer.citizenTable.update({_id: citizen_instance})

                client._id = _id
                client.citizen = self.PandoraServer.getCitizen(_id)
                client.eywa_status = True

                client.citizen.pushAuth(client)

                client.sendMessage(self.encode({'id': constants._EYWA_, 'status': 0x1, 'avatar': navi_entry.get('avatar'), 'username': navi, 'token': client_token, 'expire': expire, 'is_token': 0, 'message': '(100) Authenticated.'}))
                print ("(auth) New client authed: " + str(client))
            else:
                print ("(auth) Client: Bad password.")
                client.sendMessage(self.encode({'id': constants._EYWA_, 'status': 0x0, 'is_token': 0, 'message': '(100) Bad password.'}))
                return False

        # Bulding global informations
        burgeons = []

        try:
            for doc_id in list(client.citizen.registry):
                D_obj = self.PandoraServer.documentsManager.getDoc(doc_id)
                try:
                    informations = {
                        'id' : D_obj.str_id,
                        'state' : D_obj.state,
                        'file_location' : D_obj.file_location,
                        'branch' : D_obj.branch,
                        'name' : D_obj.name,
                        'size' : D_obj.size,
                        'left' : D_obj.left,
                        'timestamp' : D_obj.timestamp,
                        'protocol' : D_obj.protocol,
                        'sharing': D_obj.allowed,
                        'owner' : D_obj.str_owner
                    }

                    burgeons.append(informations)
                except:
                    print ("+ Handling global informations -> Unable to get download data, download probably removed.")
        except:
            print ("+ Handling global informations -> Error while getting downloads informations.")

        branches = client.citizen.branches

        sharing_queue = [];
        try:
            for share in list(client.citizen.sharing_queue):
                D_obj = self.PandoraServer.documentsManager.getDoc(share)
                print (share)
                print (D_obj)
                sharing_queue.append({'burgeon_id': share, 'by': D_obj.str_owner, 'name': D_obj.name})
        except:
            print ("Unable to generate sharing queue")

        client.sendMessage(self.encode({'id': constants._EYWA_INFORMATIONS_, 'branches': branches, 'burgeons': burgeons, 'sharing_queue': sharing_queue}))
        print ("+ Global informations sent.")
        return True # Etablish the connection with Eywa :D # Etablish connection with Eywa

    @requireEywa
    def buildBranch(self, client, packet): # Create a new empty branch without any burgeon
        # ...
        root_branch = packet.get('root_branch')
        branch_name = packet.get('branch_name')
        owner_branch = client.citizen.island
        tree = client.citizen.branches
        is_root = root_branch == '/'

        if not is_root:
            if '//' in root_branch:
                print ("+ new_sub -> Invalid root directory path.")
                client.sendMessage(self.encode({'id': constants._CREATE_BRANCH_, 'status': 0x0, 'message': 'Root directory is invalid.'}))
                return False

            build_string = 'branches.' + PandoraUtils.unslash_it(root_branch).replace('/', '.') + '.' + branch_name # Split path to be sure to not have / on left/right of the string then replace / by . for MongoDB request
            ref = PandoraUtils.walk_in_branches(root_branch, tree)
            if ref is None:
                print ("(new_sub) Root directory doesn't exists.")
                client.sendMessage(self.encode({'id': constants._CREATE_BRANCH_, 'status': 0x0, 'message': 'Root directory doesn\'t exists.'}))
                return False
        else:
            build_string = 'branches.' + branch_name
            ref = tree

        if not PandoraUtils.is_valid_branch_name(branch_name):
            print ("(new_sub) Sub name is invalid.")
            client.sendMessage(self.encode({'id': constants._CREATE_BRANCH_, 'status': 0x0, 'message': 'Sub name is invalid.'}))
            return False

        print("Creating sub_directory: %s" % (branch_name))

        try:
            if is_root:
                os.mkdir( owner_branch + branch_name )
            else:
                os.mkdir( owner_branch + PandoraUtils.unslash_it(root_branch) + '/' + branch_name )
        except:
            print("(new_sub) Unable to os.mkdir().")
            client.sendMessage(self.encode({'id': constants._CREATE_BRANCH_, 'status': 0x0, 'message': 'Unable to create sub directory'}))
            return False

        # Sub-directory is created
        ref.update( {branch_name: {}} )

        # Update user DB
        try:
            self.PandoraServer.mongoDB.users.update_one( {'_id': client._id}, { '$set': { build_string: {} } } )
        except:
            print ("+ create_sub_directory-> Database update_one() error.")
            print (sys.exc_info()[0])
            del ref[branch_name]
            try:
                if is_root:
                    os.rmdir( owner_branch + branch_name )
                else:
                    os.rmdir( owner_branch + PandoraUtils.unslash_it(root_branch) + '/' + branch_name )
            except:
                print ("+ create_sub_directory-> Unable to os.rmdir(), ghost sub directory is present now ...")

            client.sendMessage(self.encode({'id': constants._CREATE_BRANCH_, 'status': 0x0, 'message': 'Database error'}))
            return False

        print("+ create_sub_directory -> Sub directory successfully created.")
        self.sendAll(client, {'id': constants._CREATE_BRANCH_, 'status': 0x1, 'root_branch': root_branch, 'branch_name': branch_name, 'message': 'Sub directory successfully created'})
        return True

    @requireEywa
    def destructBranch(self, client, packet): # Destruct an entire branch with all his burgeons
        # ...
        tree = client.citizen.branches
        registry = client.citizen.registry
        root_branch = packet.get('root_branch')
        branch_name = packet.get('branch_name')
        is_root = root_branch == '/'

        if branch_name == '':
            print ("+ remove_sub_directory -> Name not specified.")
            client.sendMessage(self.encode({'id': constants._DESTRUCT_BRANCH_, 'status': 0x0, 'message': 'Please specify a name.'}))
            return False

        if not PandoraUtils.is_valid_branch_name(branch_name):
            print ("+ remove_sub_directory -> Name is invalid.")
            client.sendMessage(self.encode({'id': constants._DESTRUCT_BRANCH_, 'status': 0x0, 'message': 'Please specify a valid name.'}))
            return False

        passed = True
        blocks = []

        if not is_root:
            if '//' in root_branch:
                print ("+ remove_sub_directory -> Path can't contain //.")
                client.sendMessage(self.encode({'id': constants._DESTRUCT_BRANCH_, 'status': 0x0, 'message': 'Invalid sub directory path'}))
                return False

            full_path = '/' + PandoraUtils.unslash_it(root_branch) + '/' + branch_name + '/'
            parent_branch = PandoraUtils.walk_in_branches(root_branch, tree) # Will return the parent nest after checking if the last nest exists ( the sub directory to delete )
            if parent_branch is None:
                print ("+ remove_sub_directory -> Invalid sub directory path.")
                client.sendMessage(self.encode({'id': constants._DESTRUCT_BRANCH_, 'status': 0x0, 'message': 'Invalid sub directory path'}))
                return False
        else:
            full_path = '/' + branch_name + '/'
            parent_branch = tree

        print ("full_path: %s" % (full_path))
        for burgeon_id in registry:
            Burgeon = self.PandoraServer.documentsManager.getDoc(document_id)
            print ("checking for download -> %s" % (Burgeon._id))
            if Burgeon.branch.startswith(full_path): # The file linked to this download will be removed
                # Add it to download who blocks
                if passed:
                    passed = False

                blocks.append( {'name': Burgeon.name, 'in': Burgeon.branch} )


        if passed:
            print ("+ delete_sub -> Deleting nest of sub directory")
            del parent_branch[branch_name]

            # Proceed to remove
            try:
                """ ... """
                shutil.rmtree(client.citizen.island + PandoraUtils.unslash_it(root_branch) + '/' + branch_name)
            except:
                print ("+ remove_sub_directory -> Unable to remove sub directory, shutil error.")
                client.sendMessage(self.encode({'id': constants._DESTRUCT_BRANCH_, 'status': 0x0, 'io_error': True, 'message': 'Error while removing.'}))
                return False
        else:
            # Send blocks
            print ("+ remove_sub_directory -> Unable to remove sub directory, sending blocks...")
            client.sendMessage(self.encode({'id': constants._DESTRUCT_BRANCH_, 'status': 0x0, 'blocks': blocks}))
            return False

        try:
            """ ... """
            self.PandoraServer.mongoDB.users.update_one( {'_id': client._id}, {'$set': {'branches' : tree}})
        except:
            print ("+ remove_sub_directory -> Unable to update download database entry after relocation.")
            client.sendMessage(self.encode({'id': constants._DESTRUCT_BRANCH_, 'status': 0x0, 'message': 'Database error.'}))
            return False

        print ("+ remove_sub_directory -> %s was successfully deleted." % (PandoraUtils.slash_it(root_branch) + branch_name))
        self.sendAll(client, {'id': constants._DESTRUCT_BRANCH_, 'status': 0x1, 'information': {'root_branch': root_branch, 'branch_name': branch_name}})
        return True

    @requireEywa
    def createBurgeon(self, client, packet): # Create a new burgeon on a branch
        # ...
        file_location = packet.get('file_location')
        branch = packet.get('branch')
        burgeon_name = packet.get('burgeon_name')
        _raise = packet.get('raise')
        island = client.citizen.island
        tree = client.citizen.branches

        is_root = branch == '/'

        if not is_root:
            if '//' in branch:
                print ("+ new_download -> Sub directory path can't contain //")
                client.sendMessage(self.encode({'id': constants._CREATE_BURGEON_, 'status': 0x0, 'message': 'Sub directory is invalid.'}))
                return False

            c_name = '/' + burgeon_name # For concat after user root folder path
            check = PandoraUtils.walk_in_branches(branch, tree)
            if check is None:
                print ("(new_download) Sub directory is invalid.")
                client.sendMessage(self.encode({'id': constants._CREATE_BURGEON_, 'status': 0x0, 'message': 'Sub directory is invalid.'}))
                return False
        else:
            c_name = burgeon_name

        if not PandoraUtils.is_valid_burgeon_name(burgeon_name):
            print ("(new_download) Filename is invalid.")
            client.sendMessage(self.encode({'id': constants._CREATE_BURGEON_, 'status': 0x0, 'message': 'Filename is invalid.'}))
            return False

        print ("calling new_document")
        d_obj = self.PandoraServer.documentsManager.new_document(file_location, island + PandoraUtils.unslash_it(branch) + c_name, PandoraUtils.slash_it(branch), burgeon_name, island, client._id, client.citizen.name)
        if d_obj == None:
            print ("(new_download) Unable to perform add_download().")
            client.sendMessage(self.encode({'id': constants._CREATE_BURGEON_, 'status': 0x0, 'message': 'Unable to add new download.'}))
            return False

        print ("Burgeon object created")
        # Update user registry
        client.citizen.pushRegistry(d_obj._id)

        try:
            self.PandoraServer.mongoDB.users.update_one( {'_id': client._id}, { '$push': { "registry": d_obj._id } } )
        except:
            print ("+ new_download -> Database error")

        broadcast           = d_obj.allowed # List of users to broadcast

        informations = {
            "id"                : d_obj.str_id,
            "state"             : d_obj.state,
            "file_location"     : d_obj.file_location,
            "branch"            : d_obj.branch,
            "size"              : d_obj.size,
            "left"              : d_obj.left,
            "name"              : d_obj.name,
            "timestamp"         : d_obj.timestamp,
            "protocol"          : d_obj.protocol,
            "sharing"           : d_obj.allowed,
            "owner"             : d_obj.str_owner
        }

        if _raise:
            if not d_obj._raise():
                print ("+ new_download -> Unable to start download after the file was added.")
            else:
                print ("+ new_download -> New file download added with id: " + d_obj.str_id + " and download started.")
            informations['state'] = d_obj.state
        else:
            print ("+ new_download -> New file download added with id: " + d_obj.str_id)

        self.sendAll(client, {'id': constants._CREATE_BURGEON_, 'status': 0x1, 'information': informations})
        return True

    @requireEywa
    def raiseBurgeon(self, client, packet): # Make the burgeon grow
        # ...
        burgeon_id = packet.get('burgeon_id')

        informations = {
            "id": burgeon_id,
            "left": 0
        }

        burgeon_id = bson.ObjectId(burgeon_id)

        if self.PandoraServer.documentsManager.docExists(burgeon_id):
            Burgeon = self.PandoraServer.documentsManager.getDoc(burgeon_id)
            if not Burgeon.shareExists(client._id):
                print ("(start_download) Client tried to perform action on unauthorized download id.")
                client.sendMessage(self.encode({'id': constants._RAISE_BURGEON_, 'status': 0x0, 'information': informations, 'message': '(102) Unauthorized action on this download id.'}))
                return False
        else:
            print ("(start_download) Bad download id.")
            client.sendMessage(self.encode({'id': constants._RAISE_BURGEON_, 'status': 0x0, 'information': informations, 'message': '(102) Bad download id.'}))
            return False

        if Burgeon.state == constants._STATE_RAISING_:
            print ("(start_download) Client tried to start an already started download.")
            client.sendMessage(self.encode({'id': constants._RAISE_BURGEON_, 'status': 0x0, 'information': informations, 'message': '(102) Already in downloading.'}))
            return False

        if Burgeon.state == constants._STATE_WOODSPRITE_:
            print ("(start_download) Client tried to start an done download.")
            client.sendMessage(self.encode({'id': constants._RAISE_BURGEON_, 'status': 0x0, 'information': informations, 'message': '(102) Download is done.'}))
            return False

        print ("Calling _raise()")
        _raise = Burgeon._raise()
        if not _raise:
            print ("(start_download) Unable to start download.")
            client.sendMessage(self.encode({'id': constants._RAISE_BURGEON_, 'status': 0x0, 'information': informations, 'message': '(102) Unable to start download.'}))
            return False

        print ("(start_download) Download started: " + str(burgeon_id) + ".")

        try:
            self.PandoraServer.mongoDB.documents.update_one( {'_id': burgeon_id}, { '$set': { "state": constants._STATE_RAISING_ } } )
        except:
            print ("+ start_download -> Database error.")

        informations['left'] = Burgeon.left

        for share in Burgeon.allowed:
            _id = share.get('_id')
            if self.PandoraServer.viewCitizen(_id):
                for _client in list(self.PandoraServer.getCitizen(_id).auth_instances):
                    try:
                        _client.sendMessage(self.encode({'id': constants._RAISE_BURGEON_, 'status': 0x1, 'information': informations}))
                    except:
                        print ("(start_download) Unable to send broadcast message to this client, probably deconnected.")
        return True

    @requireEywa
    def restBurgeon(self, client, packet): # Let some rest to the burgeon
        # ...
        burgeon_id = packet.get('burgeon_id')

        informations = {
            "id": burgeon_id
        }

        burgeon_id = bson.ObjectId(burgeon_id) # Convert string to ObjectId() object

        if self.PandoraServer.documentsManager.docExists(burgeon_id):
            Burgeon = self.PandoraServer.documentsManager.getDoc(burgeon_id)
            if not Burgeon.shareExists(client._id):
                print ("(pause_download) Client tried to perform action on unauthorized download id.")
                client.sendMessage(self.encode({'id': constants._REST_BURGEON_, 'status': 0x0, 'information': informations, 'message': '(103) Unauthorized action on this download id.'}))
                return False
        else:
            print ("(pause_download) Bad download id.")
            client.sendMessage(self.encode({'id': constants._REST_BURGEON_, 'status': 0x0, 'information': informations, 'message': '(103) Bad download id.'}))
            return False

        if Burgeon.state != constants._STATE_RAISING_:
            if Burgeon.state == constants._STATE_WOODSPRITE_:
                print ("(pause_download) Client tried to pause an done download.")
                client.sendMessage(self.encode({'id': constants._REST_BURGEON_, 'status': 0x0, 'information': informations, 'message': '(103) Download is done.'}))
                return False
            else:
                print ("(pause_download) Client tried to pause an already paused download.")
                client.sendMessage(self.encode({'id': constants._REST_BURGEON_, 'status': 0x0, 'information': informations, 'message': '(103) Download is already paused or not started.'}))
                return False

        rest = self.PandoraServer.documentsManager.signal_rest(Burgeon)
        if not rest:
            print ("(pause_download) Unable to pause download.")
            client.sendMessage(self.encode({'id': constants._REST_BURGEON_, 'status': 0x0, 'information': informations, 'message': '(103) Unable to pause download of ' + D_obj.str_id + '.'}))
            return False

        print ("(pause_download) Download paused: " + Burgeon.str_id + ".")

        try:
            self.PandoraServer.mongoDB.documents.update_one( {'_id': Burgeon._id}, { '$set': { "state": constants._STATE_REST_ } } )
        except:
            print ("+ pause_download -> Database error.")


        for share in Burgeon.allowed:
            _id = share.get('_id')
            if self.PandoraServer.viewCitizen(_id):
                for _client in list(self.PandoraServer.getCitizen(_id).auth_instances):
                    try:
                        _client.sendMessage(self.encode({'id': constants._REST_BURGEON_, 'status': 0x1, 'information': informations, 'message': '(103) Download paused.'}))
                    except:
                        print ("(pause_download) Unable to send broadcast message to this client, probably deconnected.")
        return True

    @requireEywa
    def destructBurgeon(self, client, packet): # Destruct a burgeon on a branch
        # ...
        burgeon_id = packet.get('burgeon_id')

        informations = {
            "id": burgeon_id
        }

        burgeon_id = bson.ObjectId(burgeon_id) # Convert string to ObjectId() object

        if self.PandoraServer.documentsManager.docExists(burgeon_id):
            Burgeon = self.PandoraServer.documentsManager.getDoc(burgeon_id)
            if client._id != Burgeon.owner:
                print ("(remove_download) Client tried to perform action on unauthorized download id.")
                client.sendMessage(self.encode({'id': constants._DESTRUCT_BURGEON_, 'status': 0x0, 'information': informations, 'message': 'nauthorized action on this download id.'}))
                return False
        else:
            print ("(remove_download) Bad download id.")
            client.sendMessage(self.encode({'id': constants._DESTRUCT_BURGEON_, 'status': 0x0, 'information': informations, 'message': 'Bad download id.'}))
            return False

        if Burgeon.state == constants._STATE_RAISING_: # Pause file before remove all datas if file is in download
            rest = self.PandoraServer.documentsManager.signal_rest(Burgeon)
            if not rest:
                print ("+ remove_download -> Unable to pause download before removing.")
                client.sendMessage(self.encode({'id': constants._DESTRUCT_BURGEON_, 'status': 0x0, 'message': 'Unable to pause download before removing it.'}))
                return False
            print ("+ remove_download -> Download paused before removing :)")

        # Remove datas
        if os.path.isfile(Burgeon.save_location): # If file is created.
            try:
                os.remove(Burgeon.save_location)
            except:
                print ("+ remove_download -> Unable to remove file, probably unexisting.")
                client.sendMessage(self.encode({'id': constants._DESTRUCT_BURGEON_, 'status': 0x0, 'message': 'Unable to remove download file (IO Error).'}))
                return False
        else:
            print ("+ remove_download -> File of this download wasn't created, probably not started download.")

        # DB update
        try:
            self.PandoraServer.mongoDB.documents.delete_one( {'_id': burgeon_id} )
        except:
            print ("+ remove_download -> Database error.")
            client.sendMessage(self.encode({'id': constants._DESTRUCT_BURGEON_, 'status': 0x0, 'message': 'Database error.'}))
            return False

        for allow in Burgeon.allowed:
            user_id = allow.get('_id')
            if self.PandoraServer.viewCitizen(user_id):
                self.PandoraServer.getCitizen(user_id).removeRegistry(burgeon_id)

            try:
                self.PandoraServer.mongoDB.users.update_one({'_id': user_id}, {'$pull': {'registry': burgeon_id}})
            except:
                print ("+ remove_download -> Database error.")

        self.PandoraServer.documentsManager.removeDoc(burgeon_id)

        print ("+ remove_download -> Download %s removed." % (burgeon_id))

        for share in Burgeon.allowed:
            _id = share.get('_id')
            if self.PandoraServer.viewCitizen(_id):
                for _client in list(self.PandoraServer.getCitizen(_id).auth_instances):
                    try:
                        _client.sendMessage(self.encode({'id': constants._DESTRUCT_BURGEON_, 'status': 0x1, 'information': informations, 'message': 'Download removed.'}))
                    except:
                        print ("(remove_download) Unable to send broadcast message to this client, probably deconnected.")
        return True

    @requireEywa
    def releaseBurgeon(self, client, packet): # Release a burgeon on a branch, he will be considered as free and no reference would be saved of him
        # ...
        burgeon_id = packet.get('burgeon_id')

        informations = {
            "id": burgeon_id
        }

        burgeon_id = bson.ObjectId(burgeon_id) # Convert string to ObjectId() object

        if self.PandoraServer.documentsManager.docExists(burgeon_id):
            Burgeon = self.PandoraServer.documentsManager.getDoc(burgeon_id)
            if client._id != Burgeon.owner:
                print ("+ release -> Client tried to perform action on unauthorized download id.")
                client.sendMessage(self.encode({'id': constants._RELEASE_BURGEON_, 'status': 0x0, 'message': 'Unauthorized action on this download id.'}))
                return False
        else:
            print ("+ release -> Bad download id.")
            client.sendMessage(self.encode({'id': constants._RELEASE_BURGEON_, 'status': 0x0, 'message': 'Bad download id.'}))
            return False

        if Burgeon.state != constants._STATE_WOODSPRITE_:
            print ("+ release -> Download is not done.")
            client.sendMessage(self.encode({'id': constants._RELEASE_BURGEON_, 'status': 0x0, 'message': 'Download is not done, can\'t clear.'}))
            return False

        # DB update
        try:
            self.PandoraServer.mongoDB.documents.delete_one( {'_id': burgeon_id} )
        except:
            print ("+ release -> Database error.")
            client.sendMessage(self.encode({'id': constants._RELEASE_BURGEON_, 'status': 0x0, 'message': 'Database error.'}))
            return False

        for allow in Burgeon.allowed:
            user_id = allow.get('_id')
            if self.PandoraServer.viewCitizen(user_id):
                self.PandoraServer.getCitizen(user_id).removeRegistry(burgeon_id)

            try:
                self.PandoraServer.mongoDB.users.update_one({'_id': user_id}, {'$pull': {'registry': burgeon_id}})
            except:
                print ("+ release -> Database error.")

        print ("+ release -> Download %s cleared." % (burgeon_id))

        for share in Burgeon.allowed:
            _id = share.get('_id')
            if self.PandoraServer.viewCitizen(_id):
                for _client in list(self.PandoraServer.getCitizen(_id).auth_instances):
                    try:
                        _client.sendMessage(self.encode({'id': constants._RELEASE_BURGEON_, 'status': 0x1, 'information': informations, 'message': 'Download cleared.'}))
                    except:
                        print ("+ release -> Unable to send broadcast message to this client, probably deconnected.")
        return True

    @requireEywa
    def relocateBurgeon(self, client, packet): # Relocate a burgeon to an another branch
        # ...
        branches = client.citizen.branches
        registry = client.citizen.registry
        island = client.citizen.island
        relocation = packet.get('relocation')
        burgeon_id = packet.get('burgeon_id')

        is_root = relocation == '/'

        informations = {
            'burgeon_id': burgeon_id,
            'relocation': PandoraUtils.slash_it(relocation)
        }

        burgeon_id = bson.ObjectId(burgeon_id)

        if not client.citizen.inRegistry(burgeon_id):
            print ("+ relocate_download -> Invalid download id.")
            client.sendMessage(self.encode({'id': constants._RELOCATE_BURGEON_, 'status': 0x0, 'message': 'Invalid download id.'}))
            return False

        Burgeon = self.PandoraServer.documentsManager.getDoc(burgeon_id)

        if Burgeon.owner != client._id:
            print ("+ relocate_download -> User not permitted.")
            client.sendMessage(self.encode({'id': constants._RELOCATE_BURGEON_, 'status': 0x0, 'message': 'Permission exception.'}))
            return False

        if Burgeon.state == constants._STATE_RAISING_:
            print ("+ relocate_download -> Download is active, sending to client to pause it because.")
            client.sendMessage(self.encode({'id': constants._RELOCATE_BURGEON_, 'status': 0x0, 'message': 'Download is active, please pause it before moving it.'}))
            return False

        if relocation != '/': # If relocation is / then the user just want to relocate the document in the root_folder, so there is not object entry, this is the global object who represent /
            if '//' in relocation:
                print ("+ relocate_download -> Relocation path can't contain '//'.")
                client.sendMessage(self.encode({'id': constants._RELOCATE_BURGEON_, 'status': 0x0, 'message': 'Invalid sub directory path'}))
                return False

            # Check for relocation validity
            ref = PandoraUtils.walk_in_branches(relocation, branches)
            if ref is None:
                print ("+ relocate_download -> Invalid relocation path.")
                client.sendMessage(self.encode({'id': constants._RELOCATE_BURGEON_, 'status': 0x0, 'message': 'Invalid sub directory path'}))
                return False

        # Process to move
        try:
            if os.path.isfile(Burgeon.save_location): # If some bytes was already got we move the file, else we just modify database
                if not is_root:
                    shutil.move(Burgeon.save_location, island + PandoraUtils.unslash_it(relocation) + '/' + Burgeon.name)
                else:
                    shutil.move(Burgeon.save_location, island + Burgeon.name)
            else:
                print ("+ relocate_download -> No byte already downloaded yet, nothing to move. Pass to updates :)")
        except:
            print ("+ relocate_download -> IO Error while moving download file...")
            client.sendMessage(self.encode({'id': constants._RELOCATE_BURGEON_, 'status': 0x0, 'message': 'Unable to move file (IO Error).'}))
            return False

        # File was moved, refresh relocation informations
        Burgeon.save_location = island + PandoraUtils.unslash_it(relocation) + '/' + Burgeon.name
        Burgeon.branch = PandoraUtils.slash_it(relocation)

        try:
            self.PandoraServer.mongoDB.documents.update_one( {'_id': burgeon_id}, { '$set': { "save_location": Burgeon.save_location, "branch": Burgeon.branch } } )
        except:
            print ("+ relocate_download -> Unable to update download database entry after relocation.")
            client.sendMessage(self.encode({'id': constants._RELOCATE_BURGEON_, 'status': 0x0, 'message': 'Database error.'}))
            return False

        print ("+ relocate_download -> Burgeon successfully relocated.")

        for share in Burgeon.allowed:
            _id = share.get('_id')
            if self.PandoraServer.viewCitizen(_id):
                for _client in list(self.PandoraServer.getCitizen(_id).auth_instances):
                    try:
                        _client.sendMessage(self.encode({'id': constants._RELOCATE_BURGEON_, 'status': 0x1, 'information': informations}))
                    except:
                        print ("+ relocate_download -> Unable to send broadcast message to this client, probably deconnected.")
        return True

    @requireEywa
    def shareBurgeon(self, client, packet): # Share a burgeon to an another account
        # ...
        burgeon_id = packet.get('burgeon_id')
        bson_burgeon_id = bson.ObjectId(burgeon_id)
        shared_user = packet.get('share_to').upper()

        if not self.PandoraServer.documentsManager.docExists(bson_burgeon_id):
            print ("+ send_share -> Invalid download ID.")
            client.sendMessage(self.encode({'id': constants._SHARE_BURGEON_, 'status': 0x00, 'message': 'Invalid download ID'}))
            return False

        Burgeon = self.PandoraServer.documentsManager.getDoc(bson_burgeon_id)

        if Burgeon.owner != client._id: # Only the owner of the download can share it
            print ("+ send_share -> Unauthorized action on this download.")
            client.sendMessage(self.encode({'id': constants._SHARE_BURGEON_, 'status': 0x00, 'message': 'Permission exception.'}))
            return False

        shared_user_document = self.PandoraServer.mongoDB.users.find_one({'name': shared_user})
        if not shared_user_document:
            print ("+ send_share -> Unknown user to share.")
            client.sendMessage(self.encode({'id': constants._SHARE_BURGEON_, 'status': 0x00, 'message': 'User doesn\'t exists.'}))
            return False

        if bson_burgeon_id in shared_user_document.get('sharing_queue'):
            print ("+ send_share -> User already has received a sharing request for this download.")
            client.sendMessage(self.encode({'id': constants._SHARE_BURGEON_, 'status': 0x00, 'message': 'User already has received a sharing request for this download'}))
            return False

        shared_user_id = shared_user_document.get('_id')
        if Burgeon.shareExists(shared_user_id): # User has already been shared
            print ("+ send_share -> User has already been shared.")
            client.sendMessage(self.encode({'id': constants._SHARE_BURGEON_, 'status': 0x00, 'message': 'User has already been shared.'}))
            return False

        # Update sharing queue
        try:
            self.PandoraServer.mongoDB.users.update_one({'_id': shared_user_id}, {'$push': {'sharing_queue': bson_burgeon_id}})
        except:
            print ("+ send_share -> Unable to update sharing queue.")
            client.sendMessage(self.encode({'id': constants._SHARE_BURGEON_, 'status': 0x00, 'message': 'DB Error.'}))
            return False

        # Sharing queue updated
        informations = {
            'to': shared_user,
            'burgeon_id': burgeon_id
        }
        print ("+ send_share -> Share request sent to %s." % (shared_user))

        client.sendMessage(self.encode({'id': constants._SHARE_BURGEON_, 'status': 0x01, 'information': informations}))

        # Update live info if at least one client is authenticated on shared account
        if self.PandoraServer.viewCitizen(shared_user_id):
            shared_user_instance = self.PandoraServer.getCitizen(shared_user_id)
            queue_item = {"by": client.citizen.name, 'name': Burgeon.name, 'burgeon_id': burgeon_id}
            shared_user_instance.pushQueue(bson_burgeon_id)

            for _client in list(shared_user_instance.auth_instances):
                try:
                    _client.sendMessage(self.encode({'id': constants._SHARE_BURGEON_REQ_, 'status': 0x1, 'share': queue_item}))
                except:
                    print ("+ send_share -> Unable to send broadcast message to this client, probably deconnected.")
        return True

    @requireEywa
    def shareBurgeonHandshake(self, client, packet): # Handle response from a shared account
        """ ... """
        burgeon_id = packet.get('burgeon_id')
        bson_burgeon_id = bson.ObjectId(burgeon_id)
        answer = packet.get('answer')

        if  not client.citizen.inSharingQueue(bson_burgeon_id):
            print ("+ share_answer -> This download wasn't shared to this account.")
            client.sendMessage(self.encode({'id': constants._SHARE_BURGEON_HANDSHAKE_, 'status': 0x00, 'message': 'Permission exception'}))
            return False

        if not self.PandoraServer.documentsManager.docExists(bson_burgeon_id):
            print ("+ share_answer -> Invalid download ID.")
            client.sendMessage(self.encode({'id': constants._SHARE_BURGEON_HANDSHAKE_, 'status': 0x00, 'message': 'Invalid download ID'}))
            return False

        Burgeon = self.PandoraServer.documentsManager.getDoc(bson_burgeon_id)
        informations = {
            "name": Burgeon.name,
            "answer": answer
        }

        if answer == constants._CONTINUE_HANSHAKE_:
            print ("+ share_answer + accept...")
            share_object = {'_id': client._id, 'name': client.citizen.name}
            try:
                self.PandoraServer.mongoDB.documents.update_one({'_id': bson_burgeon_id}, {'$push': {'allowed': share_object}})
            except:
                print ("+ share_answer + accept -> Unable to update download database document.")
                client.sendMessage(self.encode({'id': constants._SHARE_BURGEON_HANDSHAKE_, 'status': 0x00, 'message': 'DB Error.'}))
                return False

            Burgeon.allowed.append(share_object)

            # Update data for sharing
            try:
                self.PandoraServer.mongoDB.users.update_one({'_id': client._id}, {'$push': {'registry': bson_burgeon_id}, '$pull': {'sharing_queue': bson_burgeon_id}})
            except:
                print ("+ share_answer + accept -> Unable to update user download database document.")
                client.sendMessage(self.encode({'id': constants._SHARE_BURGEON_HANDSHAKE_, 'status': 0x00, 'message': 'DB Error.'}))
                return False

            client.citizen.pushRegistry(bson_burgeon_id)
            client.citizen.removeQueue(bson_burgeon_id)

            print ("+ share_answer + accept -> Sharing request successfully accepted by %s" % (client.citizen.name))

            client.sendMessage(self.encode({'id': constants._SHARE_BURGEON_HANDSHAKE_, 'status': 0x01, 'information': informations}))

            update_share = {"_id": client._id, "name": client.citizen.name}
            for share in Burgeon.allowed:
                user_id = share.get('_id')
                if self.PandoraServer.viewCitizen(user_id) and user_id != client._id :
                    for _client in list(self.PandoraServer.getCitizen(user_id).auth_instances):
                        try:
                            _client.sendMessage(self.encode({'id': constants._SHARE_BURGEON_UPDATE_, 'burgeon_id': burgeon_id, 'update': update_share}))
                        except:
                            print ("+ share_answer + accept -> Unable to send broadcast message to this client, probably deconnected.")

            share_informations = {
                'id' : Burgeon.str_id,
                'state' : Burgeon.state,
                'file_location' : Burgeon.file_location,
                'branch' : Burgeon.branch,
                'name' : Burgeon.name,
                'size' : Burgeon.size,
                'left' : Burgeon.left,
                'timestamp' : Burgeon.timestamp,
                'protocol' : Burgeon.protocol,
                'sharing': Burgeon.allowed,
                'owner' : Burgeon.str_owner
            }

            for _client in list(client.citizen.auth_instances):
                try:
                    _client.sendMessage(self.encode({'id': constants._SHARE_BURGEON_NEW_, 'status': 0x1, 'share': share_informations}))
                except:
                    print ("+ share_answer + accept -> Unable to send broadcast message to this client, probably deconnected.")

        elif answer == constants._FIN_HANDSHAKE_:
            print ("+ share_answer + Decline...")
            try:
                self.PandoraServer.mongoDB.users.update_one({'_id': _id}, {'$pull': {'sharing_queue': bson_burgeon_id}})
            except:
                print ("+ share_answer + decline -> Unable to update user download database document.")
                client.sendMessage(self.encode({'id': constants._SHARE_BURGEON_HANDSHAKE_, 'status': 0x00, 'message': 'DB Error.'}))
                return False

            client.removeQueue(bson_burgeon_id)

            print ("+ share_answer + decline -> Share request successfully declined.")
            client.sendMessage(self.encode({'id': constants._SHARE_BURGEON_HANDSHAKE_, 'status': 0x01, 'information': informations}))

        else:
            client.sendMessage(self.encode({'id': constants._SHARE_BURGEON_HANDSHAKE_, 'status': 0x00, 'message': 'Invalid answer.'}))

        return True

    @requireEywa
    def unshareBurgeon(self, client, packet): # Unshare a burgeon to a shared account
        """ ... """
        burgeon_id = packet.get('burgeon_id')
        bson_burgeon_id = bson.ObjectId(burgeon_id)
        unshared_user = packet.get('unshare_to').upper()

        if not self.PandoraServer.documentsManager.docExists(bson_burgeon_id):
            print ("+ unshare_download -> Invalid download ID.")
            client.sendMessage(self.encode({'id': constants._UNSHARE_BURGEON_, 'status': 0x00, 'message': 'Invalid download ID'}))
            return False

        Burgeon = self.PandoraServer.documentsManager.getDoc(bson_burgeon_id)
        if Burgeon.owner != client._id: # Only the owner of the download can share it
            print ("+ unshare_download -> Unauthorized action on this download.")
            client.sendMessage(self.encode({'id': constants._UNSHARE_BURGEON_, 'status': 0x00, 'message': 'Permission exception.'}))
            return False

        unshared_user_document = self.PandoraServer.mongoDB.users.find_one({'name': unshared_user})
        if not unshared_user_document:
            print ("+ unshare_download -> Unknown user.")
            client.sendMessage(self.encode({'id': constants._UNSHARE_BURGEON_, 'status': 0x00, 'message': 'User doesn\'t exists.'}))
            return False

        unshared_user_id = unshared_user_document.get('_id')
        if not Burgeon.shareExists(unshared_user_id): # User has never been shared
            print ("+ unshare_download -> User has never been shared.")
            client.sendMessage(self.encode({'id': constants._UNSHARE_BURGEON_, 'status': 0x00, 'message': 'User has never been shared.'}))
            return False

        # Update data for unsharing
        unshare_object = {'_id': unshared_user_id, 'name': unshared_user}
        try:
            self.PandoraServer.mongoDB.documents.update_one({'_id': bson_burgeon_id}, {'$pull': {'allowed': unshare_object}})
        except:
            print ("+ unshare_download -> Unable to update download database document.")
            client.sendMessage(self.encode({'id': constants._UNSHARE_BURGEON_, 'status': 0x00, 'message': 'DB Error.'}))
            return False

        Burgeon.removeShare(unshare_object)

        try:
            self.PandoraServer.mongoDB.users.update_one({'_id': unshared_user_id}, {'$pull': {'registry': bson_burgeon_id}})
        except:
            print ("+ unshare_download -> Unable to update user download database document.")
            client.sendMessage(self.encode({'id': constants._UNSHARE_BURGEON_, 'status': 0x00, 'message': 'DB Error.'}))
            return False

        if self.PandoraServer.viewCitizen(unshared_user_id): # Someone in authenticated on account who just been shared
            self.PandoraServer.citizenTable.get(unshared_user_id).removeRegistry(bson_burgeon_id)

        print ("+ unshare_download -> Burgeon successfully unshared from %s" % (unshared_user))
        informations = {
            "update_unshared_object": unshare_object,
            "burgeon_id": burgeon_id
        }
        client.sendMessage(self.encode({'id': constants._UNSHARE_BURGEON_, 'status': 0x01, 'information': informations, 'message': 'Download was successfully unshared.'}))

        if self.PandoraServer.viewCitizen(unshared_user_id):
            informations = {
                'burgeon_id' : Burgeon.str_id
            }
            for _client in list(self.PandoraServer.getCitizen(unshared_user_id).auth_instances):
                try:
                    _client.sendMessage(self.encode({'id': constants._UNSHARE_BURGEON_UPDATE_, 'status': 0x1, 'information': informations}))
                except:
                    print ("+ unshare_download -> Unable to send broadcast message to this client, probably deconnected.")

        return True

    @requireEywa
    def changeNavi(self, client, packet): # Change avatar
        """ ... """
        avatar_location = packet.get('location')

        regex = re.compile(
                            r'^(?:http|ftp)s?://' # http:// or https://
                            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
                            r'localhost|' #localhost...
                            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
                            r'(?::\d+)?' # optional port
                            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

        if regex.match(avatar_location) is None:
            print ("+ change_avatar -> Invalid URL.")
            client.sendMessage( self.encode( { 'id': constants._CHANGE_AVATAR_, 'status': 0x00, 'message': 'Invalid URL.' } ) )
            return False

        # Update DB
        try:
            self.PandoraServer.mongoDB.users.update_one({'_id': client._id}, {'$set': {'avatar': avatar_location}})
        except:
            print ("+ change_avatar -> Unable to update user database entry.")
            client.sendMessage( self.encode( { 'id': constants._CHANGE_AVATAR_, 'status': 0x00, 'message': 'DB Error.' } ) )
            return False

        client.citizen.updateAvatar(avatar_location)

        print ("+ change_avatar -> Avatar successfully changed to %s" % (avatar_location))
        self.sendAll(client, { 'id': constants._CHANGE_AVATAR_, 'status': 0x01, 'avatar': avatar_location} )
        return True



class Pandora:
    def __init__(self, conf_file):
        print ("Initializing conf...")
        try:
            self.conf = json.loads(open(conf_file, "r").read())
        except:
            print ("Unable to read config file. Config file need to contain valid JSON data, be located at %s." % (conf_file))
            sys.exit(0)

        print ("Verifying conf...")
        if not self.validateConf():
            print ("Config JSON is invalid.")
            sys.exit(0)

        print ("Connecting to database (%s:%d)..." % (self.conf.get('db').get('hostname'), self.conf.get('db').get('port')))
        try:
            self.mongoClient = MongoClient( self.conf.get('db').get('hostname'), self.conf.get('db').get('port'), serverSelectionTimeoutMS = self.conf.get('db').get('timeout') )
            self.mongoClient.server_info() # Force connection by simple query

            self.mongoDB = self.mongoClient[self.conf.get('db').get('db_name')]

        except pymongo.errors.ServerSelectionTimeoutError as err:
            print ("Error while connecting to MongoDB database.")
            sys.exit(0)

        print ("Initializing server variables...")
        self.encode = JSONEncoder().encode # Encoder that support ObjectId convertion to string
        self.citizenTable = {} # Will contains citizen instance from unserialized database document when at least one client of the citizen is authenticated on the server
        self.documentsManager = DocumentsManager(self.mongoDB, self.download_done)
        self.Dispatcher = PandoraDispatcher(self)

        self.broadcastThread = Thread(target = self.broadcast_burgeons_state)
        self.broadcastThread.daemon = True
        self.broadcastThread.start()

        self.ws_host = self.conf.get('server').get('listen') # * Localhost
        self.ws_port = self.conf.get('server').get('port')

    def launchPandora(self):
        print ("Launching Pandora...")
        self.ws = SimpleWebSocketServer(self.ws_host, self.ws_port, PandoraHandler)
        print ("Pandora running on " + self.ws_host + ":" + str(self.ws_port))
        self.ws.serveforever()

    def viewCitizen(self, citizen_id):
        return True if type(self.citizenTable.get(citizen_id)) != type(None) else False

    def getCitizen(self, citizen_id):
        return self.citizenTable.get(citizen_id)

    def disconnectCitizen(self, instance):
        if instance.eywa_status:
            instance.citizen.auth_instances.remove(instance)
        else:
            print ("Client wasn't connected with Eywa, do nothing...")

    def broadcast_burgeons_state(self):
        informations = {
            "id" : None,
            "left": None
        }

        while True:
            if len(self.citizenTable) > 0:
                for user_id in self.citizenTable: # Iterate each user entry which says that at least one user is authenticated on
                    user = self.getCitizen(user_id)
                    broadcast = {'id': constants._UPDATE_BROADCAST_, 'burgeons_list': []}

                    try:
                        for burgeon_id in list(user.registry):
                            try:
                                d_obj = self.documentsManager.getDoc(burgeon_id)
                                if d_obj.state == constants._STATE_RAISING_:
                                    print ("+ Broadcast -> ObjectId('%s')" % (burgeon_id))
                                    broadcast['burgeons_list'].append( { 'id': d_obj.str_id, 'left': d_obj.left } )
                            except:
                                print ("(broadcast_burgeons_state) Unable to get burgeon data, burgeon probably destructed.")
                        if len(broadcast['burgeons_list']) > 0:
                            print ("packet to send: %s" % (broadcast))
                            for _client in list(user.auth_instances): # Broadcast all users authenticated on this user
                                _client.sendMessage(self.encode(broadcast))
                    except:
                        print ("(broadcast_burgeons_state) Unable to broadcast user, user probably removed.")
            time.sleep(2)

    def download_done(self, D_obj):
        informations = {
            "id": D_obj.str_id
        }

        try:
            self.mongoDB.documents.update_one( {'_id': D_obj._id}, { '$set': { "state": constants._STATE_WOODSPRITE_ } } )
        except:
            print ("+ done -> Database error.")


        broadcast = D_obj.allowed
        for share in broadcast:
            _id = share.get('_id')
            if self.viewCitizen(_id): # At least one client is authenticated as this user, we need to broadcast him
                for _client in list(self.getCitizen(_id).auth_instances):
                    try:
                        _client.sendMessage(self.encode({'id': constants._UPDATE_WOODSPRITE_, 'status': 0x1, 'information': informations, 'message': '(1005) Download done.'}))
                    except:
                        print ("(handle_download_done) Unable to send broadcast message to this client, probably deconnected.")
        return True

    def validateConf(self):
        # Checking server fields
        validation = {
            "server": ['listen', 'port', 'name'],
            "db": ['hostname', 'port', 'timeout', 'db_name'],
            "storage": ['world']
        }

        for key in validation:
            entry = self.conf.get(key)
            if not entry:
                return False

            for field in validation.get(key):
                if not entry.get(field):
                    return False

        return True


pandora = Pandora("config.json")
pandora.launchPandora()
