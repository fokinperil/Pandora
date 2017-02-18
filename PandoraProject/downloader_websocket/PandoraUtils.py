import hashlib, time, random

def is_shared(_id, shareds):
    for share in shareds:
        if share.get('_id') == _id:
            return True
    return False

def login(safe_pwd, cmp_pwd):
    cmp_pwd = hashlib.sha1(bytes(cmp_pwd, 'ISO 8859-1')).hexdigest()
    return True if safe_pwd == cmp_pwd else False

def get_client_token(entry, username, ip, token):
    if token in entry.get('token_registry'):
        _token = entry['token_registry'][token]
        if _token.get('ip') == ip:
            return _token

    return False

def generate_client_token():
    sc_t = str(time.time())
    s = str(random.randrange(0, 128000))
    return hashlib.sha1(bytes(sc_t + s, 'ISO 8859-1')).hexdigest()

def walk_in_branches(input_route, check_route):
    input_route = unslash_it(input_route).split('/')
    if len(input_route) < 1:
        return None

    ref = check_route
    for way in input_route:
        ref = ref.get(way)
        if ref is None:
            return None

    return ref

def is_valid_branch_name(bc_name):
    unauthorized = ['/', '..', '$', '.']
    for pattern in unauthorized:
        if pattern in bc_name:
            return False
    return True

def is_valid_burgeon_name(b_name):
    unauthorized = ['/', '..', '$', '.']
    for pattern in unauthorized:
        if pattern in b_name:
            return False
    return True


def unslash_it(path): # This function just return the path stripped of his slashes on left and right side
    return path.strip('/')

def slash_it(path): # This function will add slash to left/right of a path if there are not already there
    if path[0] != '/':
        path = '/' + path

    if path[-1] != '/':
        path = path + '/'

    return path
