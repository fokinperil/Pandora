# Burgeon state constants
_STATE_BURGEON_ = 0
_STATE_RAISING_ = 1
_STATE_REST_ = 2
_STATE_WOODSPRITE_ = 3

# Connection constants
_PING_ = '0'
_PONG_ = '1'

# Indexes
_RAWMESSAGE_                                                                        = -1

_EYWA_, _EYWA_INFORMATIONS_                                                         = 0, 10
_CREATE_BRANCH_                                                                      = 1
_DESTRUCT_BRANCH_                                                                   = 2
_CREATE_BURGEON_                                                                    = 3
_RAISE_BURGEON_                                                                     = 4
_REST_BURGEON_                                                                      = 5
_DESTRUCT_BURGEON_                                                                  = 6
_RELEASE_BURGEON_                                                                   = 7
_RELOCATE_BURGEON_                                                                  = 8
_SHARE_BURGEON_, _SHARE_BURGEON_REQ_                                                = 9, 90
_SHARE_BURGEON_HANDSHAKE_, _SHARE_BURGEON_UPDATE_, _SHARE_BURGEON_NEW_              = 10, 100, 101
_UNSHARE_BURGEON_, _UNSHARE_BURGEON_UPDATE_                                         = 11, 110
_CHANGE_AVATAR_                                                                     = 12

_UPDATE_BROADCAST_                                                                  = 1000
_UPDATE_WOODSPRITE_                                                                 = 1001

# Handshake
_CONTINUE_HANSHAKE_ = 1
_FIN_HANDSHAKE_ = 0
