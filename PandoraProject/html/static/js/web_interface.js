// Burgeon state constants
_STATE_BURGEON_ = 0
_STATE_RAISING_ = 1
_STATE_REST_ = 2
_STATE_WOODSPRITE_ = 3

// Connection constants
var _PING_ = '0',
    _PONG_ = '1';

// Indexes
var _RAWMESSAGE_                                                                    = -1;

var _EYWA_                                                                          = 0,
    _EYWA_INFORMATIONS_                                                             = 10,
    _CREATE_BRANCH_                                                                 = 1,
    _DESTRUCT_BRANCH_                                                               = 2,
    _CREATE_BURGEON_                                                                = 3,
    _RAISE_BURGEON_                                                                 = 4,
    _REST_BURGEON_                                                                  = 5,
    _DESTRUCT_BURGEON_                                                              = 6,
    _RELEASE_BURGEON_                                                               = 7,
    _RELOCATE_BURGEON_                                                              = 8,
    _SHARE_BURGEON_                                                                 = 9,
    _SHARE_BURGEON_REQ_                                                             = 90,
    _SHARE_BURGEON_HANDSHAKE_                                                       = 10,
    _SHARE_BURGEON_UPDATE_                                                          = 100,
    _SHARE_BURGEON_NEW_                                                             = 101,
    _UNSHARE_BURGEON_                                                               = 11,
    _UNSHARE_BURGEON_UPDATE_                                                        = 110,
    _CHANGE_AVATAR_                                                                 = 12;


// Handshake
var _CONTINUE_HANSHAKE_ = 1,
    _FIN_HANDSHAKE_ = 0;

var _UPDATE_BROADCAST_                                                              = 1000
    _UPDATE_WOODSPRITE_                                                             = 1001

var _ANSWER_ACCEPT_ = 1,
    _ANSWER_DECLINE_ = 0;

var _NOTIFICATION_BASIC_ = 0,
    _NOTIFICATION_ACCEPT_ = 1;

var waiting_redirection = '';

var leftLogin_state = 0;
var ping_t = 0;
var ping_intervalID = 0;

var c_info_burgeon = undefined;

var is_retrying = false,
    continue_retry = true;

var in_downloading = 0;
var notifications_count = 0;
var notification_ctx = undefined; // This variable will contain the notification context each times the user will click down on a notification

var sort_spot;

String.prototype.strip = function (chrs) {
    var str = String(this);
    var range = [0, str.length];

    var l_s = false, r_s = false;

    for ( var i = 0; i < str.length; i++ ) {
        for ( var y = 0; y < chrs.length; y++ ) {
            if ( str[i] == chrs[y] ) {
                range[0]++;
                l_s = true;
                break;
            }
        }

        if ( !l_s )
            break;
        l_s = false;
    }

    for ( var i = str.length - 1; i > 0; i-- ) {
        for ( var y = 0; y < chrs.length; y++ ) {
            if ( str[i] == chrs[y] ) {
                range[1]--;
                r_s = true;
                break;
            }
        }

        if ( !r_s )
            break;
        r_s = false;
    }

    return str.slice(range[0], range[1]);
}

function escapeHtml(text) {
  var map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  };

  return text.replace(/[&<>"']/g, function(m) { return map[m]; });
}

var notification_drag = false;
var initial_impact = {'x': 0, 'y': 0};
var drag;

function has_class(e, c) {
  if ( typeof e == "string" )
     e = document.getElementById(e);

  if ( e === undefined )
      return false;

  var classes = e.classList;
  for ( var i=0; i < classes.length; i++ )
      if ( classes[i] == c )
         return true;

  return false;
}

function get_parent_by_classname(c, e) {
    if ( typeof e == "string" )
        e = document.getElementById(e);
    if ( e === undefined )
        return false;
    while ( e.parentElement ) {
		console.log(e.parentElement);
        if ( has_class(e.parentElement, c) )
            return e.parentElement
        e = e.parentElement
    }
    return false;
}

$(document).ready(function(){

    console.log('Document ready ...');
    // Create WebSocket connection
    window.wss = new WebSocket('ws://' + document.domain + ':8000/server_ws/');
    wss.onopen = wss_onOpen;
    wss.onclose = wss_onClose;
    wss.onmessage = wss_onMessage;

    window.client = new ClientConstructor();
    if ( client.token_ready ) {
        client.tokenEywa();
    }

    window.notification_handler = new Notification(document.getElementById('notification-container'));

    /*setInterval(function () {
        draw_graph([]);
    }, 1000);*/

    sort_spot = document.getElementById('enum-date-header');

    document.getElementById('submit-login').addEventListener('submit', function (e) {
        e.preventDefault();
        send_login();
    });

    document.getElementById('enum-date-header').addEventListener('click', function (e) {
        var header = document.getElementById('enum-date-header');
        var arrow = header.getElementsByClassName('arrow-sort')[0];

        if ( header != sort_spot ) {
            sort_spot.getElementsByClassName('arrow-sort')[0].style.display = "none";
            arrow.style.display = "inline-block";
            sort_spot = header; // Change current spot reference
        }

        // Switch asc/desc
        if ( arrow.dataset.asc == "0" ) { // Switch to desc
            arrow.dataset.asc = "1";
            arrow.innerHTML = '&#xe8c4;';
            sort_burgeons_by("timestamp", 1);
        }
        else { // Switch to asc
            arrow.dataset.asc = "0";
            arrow.innerHTML = '&#xe8c3;';
            sort_burgeons_by("timestamp", 0);
        }
    }, false);

    document.getElementById('enum-name-header').addEventListener('click', function (e) {
        var header = document.getElementById('enum-name-header');
        var arrow = header.getElementsByClassName('arrow-sort')[0];

        if ( header != sort_spot ) {
            sort_spot.getElementsByClassName('arrow-sort')[0].style.display = "none";
            arrow.style.display = "inline-block";
            sort_spot = header; // Change current spot reference
        }

        // Switch asc/desc
        if ( arrow.dataset.asc == "0" ) { // Switch to desc
            arrow.dataset.asc = "1";
            arrow.innerHTML = '&#xe8c4;';
            sort_burgeons_by("name", 1);
        }
        else { // Switch to asc
            arrow.dataset.asc = "0";
            arrow.innerHTML = '&#xe8c3;';
            sort_burgeons_by("name", 0);
        }
    }, false);

    document.getElementById('enum-bandwidth-header').addEventListener('click', function (e) {
        var header = document.getElementById('enum-bandwidth-header');
        var arrow = header.getElementsByClassName('arrow-sort')[0];

        if ( header != sort_spot ) {
            sort_spot.getElementsByClassName('arrow-sort')[0].style.display = "none";
            arrow.style.display = "inline-block";
            sort_spot = header; // Change current spot reference
        }

        // Switch asc/desc
        if ( arrow.dataset.asc == "0" ) { // Switch to desc
            arrow.dataset.asc = "1";
            arrow.innerHTML = '&#xe8c4;';
            sort_burgeons_by("bandwidth", 1);
        }
        else { // Switch to asc
            arrow.dataset.asc = "0";
            arrow.innerHTML = '&#xe8c3;';
            sort_burgeons_by("bandwidth", 0);
        }
    }, false);

    document.getElementById("avatar-location").addEventListener("input", function (e) {
        var preview = document.getElementById("avatar-preview");
        preview.style.backgroundImage = "url('" + e.target.value + "')";
    }, false);

    document.getElementById("select-branch-management").addEventListener("change", function (e) {
        if ( e.target.value != '/' )
            document.getElementById("branch-selected").innerHTML = escapeHtml(e.target.value + '/') ;
        else
            document.getElementById("branch-selected").innerHTML = '/' ;
    }, false);

});

function swap_state(id) {
    var object = client.burgeons[id];

    switch ( object.state ) {
        case _STATE_BURGEON_:
            // Swap to start
            client.raiseBurgeon(object.id);
            break;

        case _STATE_RAISING_:
            // Swap to pause
            client.restBurgeon(object.id);
            break;

        case _STATE_REST_:
            // Swap to downloading
            client.raiseBurgeon(object.id);
            break;

        case _STATE_WOODSPRITE_:
            // Do nothing
            break;
    }
}

function share_burgeon(id) {
    var user_to_share = document.getElementById("share-to-input");
    client.shareBurgeon(id, user_to_share.value);
    close_burgeon_info();
}

function share_handshake(id, answer) {
    client.shareHandshake(id, answer);
}

function unshare_burgeon(id, unshared) {
    if ( confirm('Unshare  [' + client.burgeons[id].name + '] to ' + unshared + ' ?') ) {
        client.unshareBurgeon(id, unshared);
        close_burgeon_info();
    }
}

function relocate_burgeon(id) {
    var relocation = document.getElementById("select-relocation-branch");
    client.relocateBurgeon(id, relocation.value);
    close_burgeon_info();
}

function destruct_burgeon(id) {
    client.destructBurgeon(id);
    close_burgeon_info();

}

function release_burgeon(id) {
    client.releaseBurgeon(id);
    close_burgeon_info();
}

function create_branch() {
    var root_branch = document.getElementById("select-branch-management");
    var branch = document.getElementById("branch_name");
    client.createBranch(root_branch.value, branch.value);
    reset_inputs([root_branch, branch]);
    document.getElementById('branch-selected').innerHTML = '/';
    boop_close('branch', 'branch-container')
}

function destruct_branch() {
    var select = document.getElementById("select-branch-management");
    var input_name = document.getElementById('branch_name');
    client.destructBranch(select.selectedOptions[0].dataset.rootPath, select.selectedOptions[0].dataset.pureName);
    reset_inputs([select, input_name]);
    document.getElementById('branch-selected').innerHTML = '/';
    boop_close('branch', 'branch-container');
}

function change_avatar() {
    var avatar_location = document.getElementById('avatar-location');
    console.log("Querying change avatar to : " + avatar_location);
    client.changeAvatar(avatar_location.value);
    reset_inputs([avatar_location]);
    document.getElementById('avatar-preview').style.backgroundImage = '';
    boop_close('change-avatar-form', 'change-avatar-form-container');
}

function create_burgeon() {
    var file_location = document.getElementById("create-burgeon-file-location");
    var name = document.getElementById("burgeon_name");
    var save_location = document.getElementById("create-burgeon-branch");
    client.createBurgeon(file_location.value, save_location.value, name.value, 0);
    reset_inputs([file_location, name, save_location]);
    boop_close('create-burgeon', 'create-burgeon-container');
}

function send_login() {
    var user = document.getElementById("login-user");
    var pwd = document.getElementById("login-pwd");
    if ( user.value && pwd.value ) {
        client.Eywa(user.value, pwd.value);
        reset_inputs([user, pwd]);
    }
    else {
        console.log("Please specify both Username/Password.");
    }
}

function reset_inputs(inputs) {
    for ( var i=0; i < inputs.length; i++ ) {
        if ( inputs[i].type == 'text' || inputs[i].type == 'password' )
            inputs[i].value = '';
        else if ( inputs[i].type == 'select-one')
            inputs[i].selectedIndex = 0;
    }
}

function update_burgeon_info(id) {
    var ref = client.burgeons[id];
    if ( ref == undefined ) {
        console.log("+ open_download_info -> Unknown id. [" + id + "]");
        return false;
    }

    var txt_name = document.getElementById('burgeon-info-name'),
        txt_owner = document.getElementById('span-owner'),
        txt_branch = document.getElementById('span-branch'),
        txt_state = document.getElementById('span-state'),
        txt_date = document.getElementById('span-date'),
        txt_size = document.getElementById('span-file-size'),
        txt_remain = document.getElementById('span-file-remaining'),
        txt_protocol = document.getElementById('span-protocol'),
        txt_share_list = document.getElementById('share-list'),
        share_burgeon = document.getElementById('share-burgeon'),
        destruct_burgeon = document.getElementById('delete-burgeon'),
        release_burgeon = document.getElementById('release-burgeon'),
        relocate_burgeon = document.getElementById('relocate-burgeon');

    console.log("escape name")
    txt_name.innerHTML = escapeHtml(ref.name) + "<span>[ " + ref.file_location + " ]</span>";
    txt_owner.textContent = ref.owner;

    console.log("escape branch")
    txt_branch.innerHTML = escapeHtml(ref.branch);
    select_by_value("select-relocation-sub", ref.branch);

    switch ( ref.state ) {
        case _STATE_BURGEON_:
            txt_state.innerHTML = '<div class="state state_unactive" style="display: inline-block; margin-right: 7px;"></div> Awaiting for begin';
            break;

        case _STATE_RAISING_:
            txt_state.innerHTML = '<div class="state state_active" style="display: inline-block; margin-right: 7px;"></div> Active';
            break;

        case _STATE_REST_:
            txt_state.innerHTML = '<div class="state state_suspended" style="display: inline-block; margin-right: 7px;"></div> In pause';
            break;

        case _STATE_WOODSPRITE_:
            txt_state.innerHTML = '<div class="state state_done" style="display: inline-block; margin-right: 7px;"></div> Done';
            break
    }

    txt_date.textContent = ref.date;

    var tmp_size = format_bytes(ref.size);
    txt_size.textContent = tmp_size.val + " " + tmp_size.str;

    tmp_size = format_bytes(ref.left);
    txt_remain.textContent = tmp_size.val + " " + tmp_size.str;

    switch ( ref.protocol ) {
        case "http":
            txt_protocol.innerHTML = '<span style="color: #888"><i class="font-icon">&#xeb7a;</i> HTTP</span>';
            break;

        case "https":
            txt_protocol.innerHTML = '<span style="color: #63B645"><i class="font-icon">&#xe990;</i> HTTPS</span>';
            break;
    }

    txt_share_list.textContent = '';
    for ( var i=0; i < ref.sharing.length; i++ ) {
        var shared_user = ref.sharing[i].name;
        if  ( shared_user != ref.owner ) // Owner is also in shared user for easier technical maintenance, so we need to skip it
            txt_share_list.innerHTML += '<span onClick="unshare_burgeon(\'' + id + '\', \'' + shared_user + '\');">' + shared_user + '</span>, ';
    }
    if ( txt_share_list.textContent == '' ) // No user shared
        txt_share_list.textContent = "Nobody";

    share_burgeon.onclick = new Function('share_burgeon("' + id + '")');
    destruct_burgeon.onclick = new Function('destruct_burgeon("' + id + '")');
    release_burgeon.onclick = new Function('release_burgeon("' + id + '")');
    relocate_burgeon.onclick = new Function('relocate_burgeon("' + id + '")');

    return true;
}

function open_avatar_change() {
    var preview = document.getElementById("avatar-preview");
    var avatar = document.getElementById("account-avatar");
    preview.style.backgroundImage = "url('" + client.avatar + "')";
    boop_open('change-avatar-form', 'change-avatar-form-container');
}

function open_burgeon_info(id) {
    if ( ! update_burgeon_info(id) )
        return false;

    boop_open('burgeon-info', 'burgeon-info-container');

    c_info_burgeon = id;
}

function close_burgeon_info() {
    reset_inputs([document.getElementById("share-to-input")]);
    boop_close('burgeon-info', 'burgeon-info-container');
}

function remove_childs(node) {
    if ( typeof node == "string" )
        var node = document.getElementById(node);

    if ( node == undefined ) {
        console.log("+ remove_childs -> Unknown element.");
        return false;
    }

    while ( node.firstChild )
        node.removeChild(node.firstChild);
}

function start_retry() {
    document.getElementById('retry-logo').innerHTML = "<i class='font-icon animate-spin'>&#xe81a;</i>";
    document.getElementById('lost-connection-state').innerHTML = "We've lost connection.<br />Retrying...";
    document.getElementById('cancel-retry').textContent = "Cancel";
    document.getElementById('cancel-retry').onclick = cancel_retry;
    continue_retry = true;
}

function cancel_retry() {
    document.getElementById('retry-logo').innerHTML = "<i class='font-icon'>&#xe845;</i>";
    document.getElementById('lost-connection-state').innerHTML = "We've lost connection.";
    document.getElementById('cancel-retry').textContent = "Retry";
    document.getElementById('cancel-retry').onclick = start_retry;
    continue_retry = false;
}

function wss_onOpen () {
    is_retrying = false;

    console.log('~ Session opened :)');
    console.log("Websocket connection opened");

    document.getElementById("login").style.display = "flex";
    document.getElementById("lost-connection").style.display = "none";
    client.token = getCookie('client_token');
    client.username = getCookie('client_username');
    if ( client.token && client.username ) {
        console.log("Client token enabled");
        client.token_ready = 1;
    }

    if ( client.token_ready ) { // If client have an unexpired token in cookies
        client.token_login();
    }

    ping_intervalID = setInterval(function () {
        client.ping();
    }, 1000);
};

function wss_onClose() {
    console.log('~ Session closed.');

    if ( !is_retrying ) {
        is_retrying = true;

        // Clear computed data
        client.sub_tree = {};
        client.burgeons = {};
        update_select_branch(['select-branch-management', 'create-burgeon-branch', 'select-relocation-branch'], ['/']);
        remove_childs("body_enums");

        document.getElementById("empty-burgeons-list").style.display = "flex";

        document.getElementById("login").style.display = "none";
        document.getElementById("lost-connection").style.display = "flex";
    }

    // No connection anymore, clearInterval()
    clearInterval(ping_intervalID);
    document.getElementById("ping").textContent = "signal: no signal";
    console.log("Websocket connection closed");
    wss.close();

    if ( continue_retry )
        setTimeout(function() {
            console.log("No connection, retrying...");
            wss = new WebSocket('ws://' + document.domain + ':8000/server_ws/');
            wss.onopen = wss_onOpen;
            wss.onclose = wss_onClose;
            wss.onmessage = wss_onMessage;
        }, 3000);
};

// Server message interpreter
function wss_onMessage (e) {

    if ( e.data == _PONG_ ) {
        // Pong
        var pong_t = new Date().getTime();
        document.getElementById("ping").textContent = "signal: " + (pong_t - ping_t) + " ms";
        return 1;
    }

    packet = JSON.parse(e.data);

    // Debug print
    console.log("Packet log: ");
    for ( var k in packet )
        console.log("\t" + k + " : " + packet[k]);


    // Control packet

    switch ( packet.id ) {
        case _RAWMESSAGE_:
            // Raw message
            console.log(packet.message);
            console.log("Raw message received");
            break;

        case _EYWA_:
            // Authentification response
            if ( packet.status == 0x1 ) {
                if ( !packet.is_token ) {
                    console.log("Token received");
                    client.token = packet.token;
                    client.token_ready = 1;
                    document.cookie = "client_username=" + packet.username +"; expires=" + new Date(packet.expire).toUTCString();
                    document.cookie = "client_token=" + packet.token + "; expires=" + new Date(packet.expire).toUTCString();
                }

                client.username = packet.username;
                client.avatar = packet.avatar;
                console.log(packet.username + " authenticated")

                document.getElementById('login').style.display = 'none';
                document.getElementById("login-user").value = '';
                document.getElementById("login-pwd").value = '';

                document.getElementById("account-name").textContent = packet.username;
                document.getElementById("account-avatar").style.backgroundImage = "url('" + packet.avatar + "')";

                break;
            }
            else {
                if ( packet.is_token ) {
                    document.cookie = "client_username=; expires=Thu, 01 Jan 1970 00:00:00 UTC";
                    document.cookie = "client_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC";
                    client.username = '';
                    client.token = '';
                    client.token_ready = 0;
                    console.log("Invalid ip/token");
                }
                else {
                    console.log("Invalid login");
                    document.getElementById("login-pwd").value = '';
                }

                break;
            }

            case _EYWA_INFORMATIONS_:
                // Handle burgeons
                document.getElementById('body_enums').innerHTML = ''; // Reset body_enums

                if ( packet.burgeons.length > 0 )
                    document.getElementById("empty-burgeons-list").style.display = "none";

                for ( var i=0; i < packet.burgeons.length; i++ ) {
                    var id = packet.burgeons[i].id;
                    client.burgeons[id] = new Burgeon(packet.burgeons[i]);
                    client.burgeons[id].set();
                    if ( client.burgeons[id].state == _STATE_RAISING_ )
                        in_downloading++;
                }

                // Handle sub tree
                client.branches = packet.branches;
                console.log("Received branches: ");
                console.log(client.branches);
                var t_list = render_branches(0, client.branches, '/', []);
                console.log(t_list);
                update_select_branch(['select-branch-management', 'create-burgeon-branch', 'select-relocation-branch'], t_list);

                // Handle sharing queue notifications
                console.log("Handling sharing queue...");
                for ( var i=0; i < packet.sharing_queue.length; i++ )
                    notification_handler.sendIconAcceptNotification("Sharing queue has been updated by <b>" + packet.sharing_queue[i].by + "</b> for <b>" + packet.sharing_queue[i].name + "</b>", "&#xe87d;", burgeonNotificationAnswer, {"linkedBurgeon": packet.sharing_queue[i].burgeon_id});

                client.sharing_queue = packet.sharing_queue;
                break;

        case _CREATE_BURGEON_:
            if ( !packet.status ) { // Check if succeed
                notification_handler.sendBasicNotification("Unable to create the burgeon: " + packet.message, "&#xe888");
                break;
            }

            console.log("Burgeon appended");
            client.burgeons[packet.information.id] = new Burgeon(packet.information);
            client.burgeons[packet.information.id].set();

            if ( Object.keys(client.burgeons).length == 1 ) // There is the first burgeon in the list, so Empty text is visible
                document.getElementById('empty-burgeons-list').style.display = 'none';

            break;

        case _RAISE_BURGEON_:
            if ( !packet.status ) { // Check if succeed
                notification_handler.sendBasicNotification("Unable to raise the burgeon: " + packet.message, "&#xe888");
                break;
            }

            console.log("Burgeon raising...");
            client.burgeons[packet.information.id].state = _STATE_RAISING_;
            client.burgeons[packet.information.id].update(packet.information);

            in_downloading++;
            break;

        case _REST_BURGEON_:
            if ( !packet.status ) { // Check if succeed
                notification_handler.sendBasicNotification("Unable to rest the burgeon: " + packet.message, "&#xe888");
                break;
            }

            console.log("Download paused");
            client.burgeons[packet.information.id].state = _STATE_REST_;
            client.burgeons[packet.information.id].update(packet);

            in_downloading--;
            if ( in_downloading == 0 )
                document.getElementById("bandwidth-usage").textContent = "bandwidth usage: 0 b/s";
            break;

        case _DESTRUCT_BURGEON_:
            if ( !packet.status ) {// Check if succeed
                notification_handler.sendBasicNotification("Unable to destruct the burgeon: " + packet.message, "&#xe888");
                break;
            }

            notification_handler.sendBasicNotification("Burgeon successfully destructed.", "&#xe841");
            client.burgeons[packet.information.id].delete();

            if ( Object.keys(client.burgeons).length == 0 )
                    document.getElementById("empty-burgeons-list").style.display = "flex";

            break;

        case _RELEASE_BURGEON_:
            if ( !packet.status ) { // Check if succeed
                notification_handler.sendBasicNotification("Unable to release the burgeon: " + packet.message, "&#xe888");
                break;
            }

            notification_handler.sendBasicNotification("Burgeon successfully released.", "&#xe841");
            client.burgeons[packet.information.id].delete();

            if ( Object.keys(client.burgeons).length == 0 )
                    document.getElementById("empty-burgeons-list").style.display = "flex";

            break;

        case _UPDATE_BROADCAST_:
            console.log("List received:");
            console.log(packet.burgeons_list);

            var bwidth_usage = 0;
            for ( var i=0; i < packet.burgeons_list.length; i++ ) {
                var id = packet.burgeons_list[i].id;
                console.log("+ Burgeon broadcasted: " + id);
                if ( id == c_info_burgeon )
                    update_burgeon_info(id);

                bwidth_usage += client.burgeons[id].update(packet.burgeons_list[i]);
            }

            console.log("bandwidth usage in bytes: " + bwidth_usage + " bytes");
            bwidth_usage = format_bytes(bwidth_usage);
            document.getElementById("bandwidth-usage").textContent = "bandwidth usage: " + bwidth_usage.val + " " + bwidth_usage.str + "/s";
            break;


        case _UPDATE_WOODSPRITE_:
            console.log("Burgeon now turned in woodsprite, gg !");
            console.log(client.burgeons[packet.information.id])
            // A burgeon finished to grows
            client.burgeons[packet.information.id].state = _STATE_WOODSPRITE_;
            client.burgeons[packet.information.id].left = 0;
            client.burgeons[packet.information.id].update(packet.information);
            console.log(client.burgeons[packet.information.id])

            if ( packet.information.id == c_info_burgeon )
                update_burgeon_info(packet.information.id);

            in_downloading--;
            if ( in_downloading == 0 )
                document.getElementById("bandwidth-usage").textContent = "bandwidth usage: 0 b/s";

            break;

        case _CREATE_BRANCH_:
            // . . .
            if ( !packet.status ) {
                notification_handler.sendBasicNotification("Unable to create branch: " + packet.message, "&#xe888");
                break;
            }

            if ( packet.root_branch != '/' ) {
                // Extract root path
                var path = packet.root_branch.strip('/').split('/');
                console.log("Path to branch is ");
                console.log(path);

                var ref = client.branches;
                for ( var i = 0; i < path.length; i++ ) {
                    ref = ref[path[i]];
                    if ( ref == undefined ) {
                        console.log("+ Received branch path is invalid.");
                        return false;
                    }
                }
            }
            else
                ref = client.branches;

            ref[packet.branch_name] = {}; // Create new sub directory object entry

            var t_list = render_branches(0, client.branches, '/', []);
            update_select_branch(['select-branch-management', 'create-burgeon-branch', 'select-relocation-branch'], t_list);
            notification_handler.sendBasicNotification("<b>" + packet.branch_name + "</b> branch successfully created in <b>" + packet.root_branch + "</b>", "&#xe841");
            break;

            case _DESTRUCT_BRANCH_:
                if ( !packet.status ) {
                    if ( packet.blocks ) {
                        i_msg = "Unable to destruct branch one or more burgeon(s) are still on it.<br /><br /><code>";
                        for ( var i=0; i < packet.blocks.length; i++ )
                            i_msg += "=> " + packet.blocks[i].name + " in " + packet.blocks[i].in + '<br />';
                        i_msg += "</code><br />Please destruct burgeons or move them into another branch.<br />";
                        notification_handler.sendBasicNotification(i_msg, "&#xe888");
                    }
                    else if ( packet.io_error )
                        notification_handler.sendBasicNotification("Unable to destruct branch: " + packet.message, "&#xe888");
                    else
                        notification_handler.sendBasicNotification("Unable to destruct branch: " + packet.message, "&#xe888");
                    break;
                }

                console.log(packet.information)

                if ( packet.information.root != '/' ) {
                    s_list = packet.information.root_branch.strip('/').split('/');
                    parent = client.branches;
                    for ( var i=0; i < s_list.length; i++ ) {
                        parent = parent[s_list[i]];
                        if ( parent == undefined ) {
                            console.log("+ recv_destruct_branch -> Received destructed branch way unknown in branches.");
                            break;
                        }
                    }
                }
                else {
                    parent = client.branches
                }

                if ( ! delete parent[packet.information.branch_name] ) {
                    console.log("+ recv_destruct_branch -> Received destructed branch not found in last nest of branches.");
                    break;
                }

                var t_list = render_branches(0, client.branches, '/', []);
                update_select_branch(['select-branch-management', 'create-burgeon-branch', 'select-relocation-branch'], t_list);
                notification_handler.sendBasicNotification("<b>" + packet.information.branch_name + "</b> branch successfully destructed on <b>" + packet.information.root_branch + "</b>", "&#xe841");
                break;

            case _RELOCATE_BURGEON_:
                if ( !packet.status ) {
                    notification_handler.sendBasicNotification("Unable to relocate the burgeon: " + packet.message, "&#xe888");
                    console.log(packet.message);
                    break;
                }

                var id = packet.information.burgeon_id;
                client.burgeons[id].branch = packet.information.relocation;

                notification_handler.sendBasicNotification("<b>[" + client.burgeons[id].name + "]</b> successfully relocated on <b>" + packet.information.relocation + "</b>", "&#xe841");
                break;

            case _CHANGE_AVATAR_:
                if ( !packet.status ) {
                    notification_handler.sendBasicNotification("Unable to change avatar: " + packet.message, "&#xe888");
                    console.log(packet.message);
                    break;
                }

                var avatar = document.getElementById('account-avatar');
                avatar.style.backgroundImage = "url('" + packet.avatar + "')";
                client.avatar = packet.avatar;
                notification_handler.sendBasicNotification("Avatar updated !", "&#xe831");
                break;

            case _SHARE_BURGEON_:
                if ( !packet.status ) {
                    notification_handler.sendBasicNotification("<b>Share request error:</b> " + packet.message, "&#xe888");
                    console.log(packet.message);
                    break;
                }

                var id = packet.information.burgeon_id;
                var to = packet.information.to;

                var d_ref = client.burgeons[id];
                notification_handler.sendBasicNotification("Share request for <b>[" + d_ref.name + "]</b> been sent to <b>" + to + "</b>", "&#xe841");
                break;

            case _SHARE_BURGEON_REQ_:
                console.log("Sharing request received.");
                client.sharing_queue.push(packet.share);
                notification_handler.sendIconAcceptNotification("You received a sharing request by <b>" + packet.share.by + "</b> for <b>" + packet.share.name + "</b>", "&#xe87d;", burgeonNotificationAnswer, {"linkedBurgeon": packet.share.burgeon_id});
                break;

            case _SHARE_BURGEON_HANDSHAKE_:
                if ( !packet.status ) {
                    notification_handler.sendBasicNotification("Unable to handshake to this sharing: " + packet.message, "&#xe888");
                    console.log(packet.message);
                    break;
                }

                if ( packet.information.answer == _CONTINUE_HANSHAKE_ )
                    notification_handler.sendBasicNotification("You accepted the sharing request for <b>[" + packet.information.name + "]</b>", "&#xe841");
                else
                    notification_handler.sendBasicNotification("You declined the sharing request for <b>[" + packet.information.name + "]</b>", "&#xe841");
                break;

            case _SHARE_BURGEON_UPDATE_:
                var D_ref = client.burgeons[packet.burgeon_id];
                if ( D_ref == undefined ) {
                    console.log("+ update_share -> Unknow burgeon reference.");
                    break;
                }

                D_ref.sharing.push(packet.update)
                notification_handler.sendBasicNotification(packet.update.name + " has been shared to the Burgeon [" + D_ref.name + "] of " + D_ref.owner, "&#xe87d");
                break;

            case _SHARE_BURGEON_NEW_:
                var id = packet.share.id;
                var d_ref = new Burgeon(packet.share);
                client.burgeons[id] = d_ref;
                d_ref.set();
                if ( d_ref.state == _STATE_RAISING_ )
                    in_downloading++;

                notification_handler.sendBasicNotification("<b>[" + d_ref.name + "]</b> has been shared to your account by <b>" + d_ref.owner + "</b>", "&#xe885");
                break;

            case _UNSHARE_BURGEON_:
                if ( !packet.status ) {
                    notification_handler.sendBasicNotification("Unable to unshare the burgeon: " + packet.message, "&#xe888");
                    console.log(packet.message);
                    break;
                }

                var id = packet.information.burgeon_id;
                var d_ref = client.burgeons[id];
                var unshare_object = packet.information.update_unshared_object;

                var indexOfShare = indexOfObjectArray(d_ref.sharing, unshare_object._id, '_id');
                d_ref.sharing.splice(indexOfShare, 1);

                notification_handler.sendBasicNotification("<b>[" + d_ref.name + "]</b> has been unshared from <b>" + unshare_object.name + "</b>", "&#xe885");
                break;

            case _UNSHARE_BURGEON_UPDATE_:
                var id = packet.information.burgeon_id;

                var d_ref = client.burgeons[id];
                d_ref.delete();
                if ( d_ref.state == _STATE_RAISING_ )
                    in_downloading--;

                notification_handler.sendBasicNotification("<b>[" + d_ref.name + "]</b> has been unshared from your account by <b>" + d_ref.owner + "</b>", "&#xe885");
                delete client.burgeons[id];
                break;
    }

    return true;
};

function Notification(container) {
    this.container = container;
}

Notification.prototype.createNotification = function () {
    var _id = getNotfificationId();

    var notification = document.createElement('div');
    notification.className = "notification";
    notification.id = _id;

    return notification;
}

Notification.prototype.sendBasicNotification = function (message, icon, attributes) {
    var notification = this.createNotification();
    notification.__type__ = _NOTIFICATION_BASIC_;

    if ( attributes ) // Set additionnal attributes if defined
        setAttributes(notification, attributes);

    var template = document.getElementById('notification-template').innerHTML;
    template = template.replace(/{icon}/g, icon);
    template = template.replace(/{message}/g, message);
    notification.innerHTML = template;

    notification.addEventListener('mousedown', notificationHandleDragging, false);
    notification.addEventListener('mouseup', notificationHandleDrop, false);
    notification.addEventListener('animationend', notificationAnimationEnd, false);

    if ( notifications_count == 0 )
        document.getElementById('empty-notification').style.display = 'none';
    notifications_count++;

    this.container.insertBefore(notification, this.container.firstChild);
    void notification.offsetWidth;
    notification.classList.add("pop");
}

Notification.prototype.sendBasicAcceptNotification = function (message, answer_handler, attributes) {
    var notification = this.createNotification();
    notification.__type__ = _NOTIFICATION_ACCEPT_;

    if ( answer_handler )
        notification.answer_handler = answer_handler;

    if ( attributes ) // Set additionnal attributes if defined
        setAttributes(notification, attributes);

    var template = document.getElementById('basicconfirm-notification-template').innerHTML;
    template = template.replace(/{message}/g, message);

    notification.innerHTML = template;

    notification.addEventListener('mousedown', notificationHandleDragging, false);
    notification.addEventListener('mouseup', notificationHandleDrop, false);
    notification.addEventListener('animationend', notificationAnimationEnd, false);

    c0 = notification.getElementsByClassName('c0')[0];
    c0.n_container = notification;
    c0.answer = _ANSWER_ACCEPT_;
    c0.onclick = answer_handler;

    c1 = notification.getElementsByClassName('c1')[0];
    c1.n_container = notification;
    c1.answer = _ANSWER_DECLINE_;
    c1.onclick = answer_handler;

    if ( notifications_count == 0 )
        document.getElementById('empty-notification').style.display = 'none';
    notifications_count++;

    this.container.insertBefore(notification, this.container.firstChild);
    void notification.offsetWidth;
    notification.classList.add("pop");
}

Notification.prototype.sendIconAcceptNotification = function (message, icon, answer_handler, attributes) {
    var notification = this.createNotification();
    notification.__type__ = _NOTIFICATION_ACCEPT_;

    if ( answer_handler )
        notification.answer_handler = answer_handler;

    if ( attributes ) // Set additionnal attributes if defined
        setAttributes(notification, attributes);

    var template = document.getElementById('iconconfirm-notification-template').innerHTML;
    template = template.replace(/{icon}/g, icon);
    template = template.replace(/{message}/g, message);

    notification.innerHTML = template;

    notification.addEventListener('mousedown', notificationHandleDragging, false);
    notification.addEventListener('mouseup', notificationHandleDrop, false);
    notification.addEventListener('animationend', notificationAnimationEnd, false);

    c0 = notification.getElementsByClassName('c0')[0];
    c0.n_container = notification;
    c0.answer = _ANSWER_ACCEPT_;
    c0.onclick = notificationAnswer;

    c1 = notification.getElementsByClassName('c1')[0];
    c1.n_container = notification;
    c1.answer = _ANSWER_DECLINE_;
    c1.onclick = notificationAnswer;

    if ( notifications_count == 0 )
        document.getElementById('empty-notification').style.display = 'none';
    notifications_count++;

    this.container.insertBefore(notification, this.container.firstChild);
    void notification.offsetWidth;
    notification.classList.add("pop");
}

function burgeonNotificationAnswer(answer) {
    if ( answer == _ANSWER_ACCEPT_ )
        client.shareHandshake(notification_ctx.linkedBurgeon, _CONTINUE_HANSHAKE_);
    else
        client.shareHandshake(notification_ctx.linkedBurgeon, _FIN_HANDSHAKE_);
}

function notificationAnswer(ev) {
    var el = ev.currentTarget;
    if ( notification_ctx.answer_handler )
        notification_ctx.answer_handler(el.answer);

    console.log("+notification_answer delete_notification()");
    deleteNotification();
}

function deleteNotification () {
    notification_ctx.addEventListener('transitionend', notificationDeleteTransitionEnd, false);
    notification_ctx.style.transition = "transform 0.3s ease-in-out, opacity 0.2s ease-in-out";
    notification_ctx.style.opacity = "0";
    notification_ctx.style.transform = "scale(0.7)";
}

var getNotfificationId = function () {
    var timestamp = (new Date().getTime() / 1000 | 0).toString(16);
    return timestamp + 'xxxxxxxxxxxxxxxx'.replace(/[x]/g, function () {
        return (Math.random() * 16 | 0).toString(16);
    }).toLowerCase();
};

function notificationAnimationEnd(e) {
  e.target.classList.remove('pop');
  e.target.removeEventListener('animationend', notificationAnimationEnd, false);
}

function notificationDeleteTransitionEnd(e) {
    console.log("Notification delete transition ended.");
    e.target.style.display = "none";
    e.target.removeEventListener('transitionend', notificationDeleteTransitionEnd, false);
    e.target.outerHTML = '';
    notifications_count--;
    if ( notifications_count == 0 )
        document.getElementById('empty-notification').style.display = 'flex';
}

function notificationHandleDragging(e) {
    console.log(e.currentTarget);
    notification_ctx = e.currentTarget;
    console.log("+drag => notification_ctx updated");

    if ( has_class(e.target, 'drag-lock') )
        return false;

    /*if ( has_class(notification_ctx, 'notification') ) {
        drag = e.target;
    }
    else {
        var notification = get_parent_by_classname('notification', e.target);
        if ( notification )
            drag = notification;
        else {
            return false;
        }
    }*/

    console.log("Dragging...");
    notification_ctx.classList.add('notification-dragging');

    var cur_pos = mouseCoords(e);
    var coord = notification_ctx.getBoundingClientRect();

    initial_impact.x = (cur_pos.x - coord.left);
    initial_impact.y = (cur_pos.y - coord.top);

    notification_drag = true;
    notification_ctx.style.position = "absolute";

    document.onmousemove = mouseMove;
    document.onmousemove(e);
}

function notificationHandleDrop(e) {

    if ( notification_drag ) {
        console.log("Dropped.");
        notification_drag = false;

        initial_impact.x = 0;
        initial_impact.y = 0;
        var container = document.getElementById('notification-container');
        console.log("drag.offsetLeft: " + notification_ctx.offsetLeft);
        console.log("drag.offsetWidth: " + notification_ctx.offsetWidth);
        console.log("container.offsetLeft: " + container.offsetLeft);
        console.log("container.offsetWidth: " + container.offsetWidth);
        if ( notification_ctx.offsetLeft  > (container.offsetLeft + container.offsetWidth) ) {
            console.log("Dropped out of container.");
            if ( notification_ctx.__type__ == _NOTIFICATION_ACCEPT_ )
                client.shareAnswer(notification_ctx.linkedBurgeon, _SHARE_ANSWER_DECLINE_);

            console.log("+drop delete_notification()");
            deleteNotification();
        }
        else {
            console.log("Still in the container.");
            notification_ctx.classList.remove('notification-dragging');
            notification_ctx.style.position = '';
            notification_ctx.style.top = "";
            notification_ctx.style.left = "";
        }
        document.onmousemove = undefined;
    }
}

function mouseMove(ev){
  ev           = ev || window.event;
  var mousePos = mouseCoords(ev);
  notification_ctx.style.top = (mousePos.y - initial_impact.y) + "px";
  notification_ctx.style.left = (mousePos.x - initial_impact.x) + "px";
}

function mouseCoords(ev){
  if(ev.pageX || ev.pageY) {
    return {x:ev.pageX, y:ev.pageY};
  }
  return {
    x: ev.clientX + document.body.scrollLeft - document.body.clientLeft,
    y: ev.clientY + document.body.scrollTop  - document.body.clientTop
  };
}

function setAttributes(to, from) {
    var keys = Object.keys(from);
    for ( var i=0; i < keys.length; i++ )
        to[keys[i]] = from[keys[i]];
}

// Download Class.
function Burgeon(query_object) {
    // Attributs
    // state, timestamp, downloaded_amount, filesize, filename, url, id
    this.owner = query_object.owner;
    this.protocol = query_object.protocol;
    this.sharing = query_object.sharing;
    this.state = query_object.state;
    this.last_state = query_object.state;
    this.bandwidth = 0;

    var e = new Date(query_object.timestamp * 1000);
    this.date = e.getUTCDate() + "/" + (parseInt(e.getUTCMonth()) + 1) + "/" + e.getUTCFullYear();
    this.timestamp = query_object.timestamp;

    this.left = query_object.left;
    this.size = query_object.size;
    this.name = query_object.name;
    this.file_location = query_object.file_location;
    this.branch = query_object.branch;
    this.id = query_object.id;
    this.DOMreference = undefined;

    console.log("Informations: ")
    console.log(query_object);
    console.log("Burgeon object initialized.");
}

// Download class methods

Burgeon.prototype.set_status = function () {
    switch ( this.state ) {
        case _STATE_BURGEON_:
            this.DOMreference.getElementsByClassName("state")[0].className = "state state_unactive";
            break;

        case _STATE_RAISING_:
            this.DOMreference.getElementsByClassName("state")[0].className = "state state_active";
            break;

        case _STATE_REST_:
            this.DOMreference.getElementsByClassName("state")[0].className = "state state_suspended";
            break;

        case _STATE_WOODSPRITE_:
            this.DOMreference.getElementsByClassName("state")[0].className = "state state_done";
            break;
    }
}

Burgeon.prototype.set = function () {
    // This function will append the download in the DOM view.
    var template = document.getElementById("burgeon_template").innerHTML;
    template = template.replace(/{id}/g, this.id);
    template = template.replace(/{href}/g, escapeHtml(this.file_location));
    template = template.replace(/{filename}/g, escapeHtml(this.name));
    template = template.replace(/{date}/g, this.date);
    template = template.replace(/{percent}/g, 	Math.round( (this.size - this.left) / this.size * 100));

    var bandwidth = format_bytes(this.bandwidth);
    template = template.replace(/{bandwidth_value}/g, bandwidth.val);
    template = template.replace(/{bandwidth_str}/g, bandwidth.str + '/s');

    switch ( this.state ) {
        case _STATE_BURGEON_:
            /* Nothing, the bar is at 0% */
            break;

        case _STATE_RAISING_:
            template = template.replace(/{bg_color}/g, "#719ABD");
            break;

        case _STATE_REST_:
            template = template.replace(/{bg_color}/g, "#aaa");
            break;

        case _STATE_WOODSPRITE_:
            template = template.replace(/{bg_color}/g, "#7FBD72");
            break;
    }

    var c_element = document.createElement('div');
    c_element.innerHTML = template;

    var b_enums = document.getElementById("body_enums");
    document.getElementById("body_enums").insertBefore(c_element, b_enums.firstElementChild);
    this.DOMreference = c_element;

    console.log("this.id: " + this.id);
    this.DOMreference.getElementsByClassName('body_enum_lookup')[0].onclick = new Function('open_burgeon_info("' + this.id + '")');

    this.set_status();
    return true;
}

Burgeon.prototype.delete = function () {
    // This function will delete the download in the DOM view.
    document.getElementById("burgeon-" + this.id).outerHTML = '';
    delete client.burgeons[this.id];
    return true;
}

Burgeon.prototype.update = function (update_object) {
    // This function will update the download object and the DOM view according to the updated data.
    var bytesrate = 0;
    switch ( this.state ) {
        case _STATE_RAISING_:
            console.log("State raising, left: " + update_object.left);
            bytesrate = (this.left - update_object.left) / 2; // Get the difference between last and new downloaded amount divided by 2 ( update each 2s )
            this.left = update_object.left; // Update downloaded amount before for future purposes
            var time_left = Math.floor(this.left/this.bytesrate);
            var downloaded = this.size - this.left;

            var bandwidth = format_bytes(bytesrate);
            this.DOMreference.getElementsByClassName("turtle_value")[0].style.background = "#719ABD";
            this.DOMreference.getElementsByClassName("turtle_value")[0].style.width = Math.round((downloaded/this.size) * 100) + "%"; /* Update the percent bar */
            this.DOMreference.getElementsByClassName("body_enum_speed")[0].innerHTML = bandwidth.val + "<span class='bandwidth-format'>" + bandwidth.str + "/s</span>";
            break;

        case _STATE_REST_:
            this.DOMreference.getElementsByClassName("turtle_value")[0].style.background = "#aaa";
            this.DOMreference.getElementsByClassName("body_enum_speed")[0].innerHTML = '∞';
            break;

        case _STATE_WOODSPRITE_:
            document.getElementById("notification_audio").play();
            this.DOMreference.getElementsByClassName("turtle_value")[0].style.background = "#7FBD72"; // Green background
            this.DOMreference.getElementsByClassName("turtle_value")[0].style.width = "100%";
            this.DOMreference.getElementsByClassName("body_enum_speed")[0].innerHTML = '';
            break;
    }

    if ( this.last_state != this.state ) {
        this.set_status();
        this.last_state = this.state;
    }

    this.bandwidth = bytesrate;
    return bytesrate;
}

// ClientConstructor class
function ClientConstructor() {
    this.username       = undefined;
    this.password       = undefined;
    this.avatar         = undefined;
    this.token          = undefined;
    this.token_ready    = 0;
    this.sharing_queue  = [];
    this.branches       = {};
    this.burgeons       = {};
    this.notifications  = {};
}

// ClientConstructor methods
ClientConstructor.prototype.ping = function () {
    ping_t = new Date().getTime();
    wss.send(_PING_);
}

ClientConstructor.prototype.tokenEywa = function() {
    var token_login_req = JSON.stringify({'id': _EYWA_, 'username': this.username, 'login_token': this.token, 'is_token': 1});
    wss.send(token_login_req);
}

ClientConstructor.prototype.Eywa = function (username, password) {
    console.log("Debug ~ Try login with " + username + "||" + password);
    var login_req = JSON.stringify({'id': _EYWA_, 'username': username, 'pwd': password, 'is_token': 0});
    wss.send(login_req);
}

ClientConstructor.prototype.createBranch = function (root_branch, branch_name) {
    var createBranch_req = JSON.stringify({'id': _CREATE_BRANCH_, 'root_branch': root_branch, 'branch_name': branch_name});
    wss.send(createBranch_req);
}

ClientConstructor.prototype.destructBranch = function (root_branch, branch_name) {
    var destructBranch_req = JSON.stringify({'id': _DESTRUCT_BRANCH_, 'root_branch': root_branch, 'branch_name': branch_name});
    wss.send(destructBranch_req);
}

ClientConstructor.prototype.createBurgeon = function (file_location, branch, burgeon_name, raise) {
    var createBurgeon_req = JSON.stringify({'id': _CREATE_BURGEON_, 'file_location': file_location, 'branch': branch, 'burgeon_name': burgeon_name, 'raise': raise});
    wss.send(createBurgeon_req);
}

ClientConstructor.prototype.raiseBurgeon = function (id) {
    var raiseBurgeon_req = JSON.stringify({'id': _RAISE_BURGEON_, 'burgeon_id': id});
    wss.send(raiseBurgeon_req);
}

ClientConstructor.prototype.restBurgeon = function (id) {
    var restBurgeon_req = JSON.stringify({'id': _REST_BURGEON_, 'burgeon_id': id});
    wss.send(restBurgeon_req);
}

ClientConstructor.prototype.destructBurgeon = function (id) {
    var destructBurgeon_req = JSON.stringify({'id': _DESTRUCT_BURGEON_, 'burgeon_id': id});
    wss.send(destructBurgeon_req);
}

ClientConstructor.prototype.releaseBurgeon = function (id) {
    var releaseBurgeon_req = JSON.stringify({'id': _RELEASE_BURGEON_, 'burgeon_id': id});
    wss.send(releaseBurgeon_req);
}

ClientConstructor.prototype.relocateBurgeon = function (id, relocation) {
    var relocateBurgeon_req = JSON.stringify({'id': _RELOCATE_BURGEON_, 'burgeon_id': id, 'relocation': relocation});
    wss.send(relocateBurgeon_req);
}

ClientConstructor.prototype.changeAvatar = function (location) {
    var changeAvatar_req = JSON.stringify({'id': _CHANGE_AVATAR_, 'location': location});
    wss.send(changeAvatar_req);
}

ClientConstructor.prototype.shareBurgeon = function ( burgeon_id, share_user ) {
    var shareBurgeon_req = JSON.stringify({'id': _SHARE_BURGEON_, 'burgeon_id': burgeon_id, 'share_to': share_user});
    wss.send(shareBurgeon_req);
}

ClientConstructor.prototype.shareHandshake = function ( burgeon_id, answer ) {
    var shareHandshake_req = JSON.stringify({'id': _SHARE_BURGEON_HANDSHAKE_, 'burgeon_id': burgeon_id, 'answer': answer});
    wss.send(shareHandshake_req);
}

ClientConstructor.prototype.unshareBurgeon = function ( burgeon_id, unshare_user ) {
    var unshareBurgeon_req = JSON.stringify({'id': _UNSHARE_BURGEON_, 'burgeon_id': burgeon_id, 'unshare_to': unshare_user});
    wss.send(unshareBurgeon_req);
}

// Functions
if(typeof(String.prototype.trim) === "undefined")
{
    String.prototype.trim = function()
    {
        return String(this).replace(/^\s+|\s+$/g, '');
    };
}

function getCookie(arg_cookie_name) {
    var cookies = document.cookie.split(';');
    for ( var i=0; i < cookies.length; i++ )
        cookies[i] = cookies[i].split('=', 2);

    // Search cookie by name
    for ( i=0; i < cookies.length; i++ )
        if ( cookies[i][0].trim() == arg_cookie_name )
            return cookies[i][1];

    return 0;
}

function followRedirection() {
    window.open(waiting_redirection, "_blank");
}

function isInArray(value, array) {
    return array.indexOf(value) > -1;
}

function format_bytes(b) {
    var object = {"val": 0, "str": 'nothing'};
    if ( b < 1000 ) { // bytes
        object.val = b;
        object.str = "bytes";
    }
    else if ( b < 1000000) { // kB
        object.val = (b/1000).toFixed(2);
        object.str = "kB";
    }
    else { // MB
        object.val = (b/1000000).toFixed(2);
        object.str = "mB";
    }
    return object;
}

function extension(x) {
    var res = '';
    for ( var i= x.indexOf('.') == -1 ? 0 : x.indexOf('.') ; i < x.length; i++ )
        res += x[i];
    return res;
}

function draw_graph(arg_values) {
    var graph_offset = 0;
    var canvas_height = document.getElementById("graph").height;
    var high = 1000;
    var ratio = Math.floor(high / canvas_height);

    var canvas = document.getElementById("graph");
    console.log("canvas width: " + canvas.width + ", canvas clientHeight: " + canvas.clientWidth + "\ncanvas height: " + canvas.height + ", canvas clientHeight: " + canvas.clientHeight);
    canvas.width = canvas.clientWidth;
    canvas.height = canvas.clientHeight;
    var max_lines = Math.floor(canvas.width / 3);

    for ( var i=0; i < max_lines; i++ )
      arg_values.push(Math.floor(Math.random() * high));

    var ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    ctx.fillStyle = "#92AEDF";
    for ( var i=0; i < arg_values.length; i++ ) {
      rnd = Math.floor(arg_values[i] / ratio);
      ctx.fillRect(graph_offset, canvas_height - rnd, 2, rnd);
      graph_offset += 3;
    }
}

function boopCloseAnimationEnd(e) {
    console.log("boopCloseAnimationEnd");
    if ( has_class(e.target, 'bumpy-wrapper') ) {
        e.target.style.zIndex = "-1";
        e.target.removeEventListener('transitionend', boopCloseAnimationEnd, false);
    }
}

function boop_open(arg_wrapper, arg_container) {
    console.log('wrapper: ' + arg_wrapper + ', container: ' + arg_container);
    // Display
    var wrapper = document.getElementById(arg_wrapper);
    var container = document.getElementById(arg_container);

    wrapper.style.zIndex = "1000";
    wrapper.style.background = "rgba(0,0,0,0.3)";

    container.classList.remove('bumpy-close');
    void container.offsetWidth;
    container.classList.add('bumpy-open');
}

function boop_close(arg_wrapper, arg_container) {
    // Hide
    var wrapper = document.getElementById(arg_wrapper);
    var container = document.getElementById(arg_container);

    console.log(wrapper);
    wrapper.addEventListener('transitionend', boopCloseAnimationEnd, false);
    wrapper.style.background = "rgba(0,0,0,0.0)";

    container.classList.remove('bumpy-open');
    void container.offsetWidth;

    container.classList.add('bumpy-close');
}

function render_branches(nest, ref, path, render) {
    if ( nest > 255 ) {
        console.log('Maximum nest value reached.');
        return false;
    }

    if ( nest == 0 )
        render.push(path);

    for ( k_index in Object.keys(ref) ) {
        k_name = Object.keys(ref)[k_index];
        render.push('---- '.repeat(nest) + path + k_name);
        render_branches(nest + 1, ref[k_name], path + k_name + '/', render);
    }

    return render;
}

function update_select_branch(selects, tree_list) {
    var s_list = [];

    var get;
    for ( var i=0; i < selects.length; i++ ) {
        get = document.getElementById(selects[i]);
        if ( get == undefined )
            console.log('+ update_select_branch -> ' + selects[i] + ' is an invalid select id. Ignoring...');
        else {
            get.innerHTML = ''; // Reset
            s_list.push(get);
        }
    }

    var opt;
    for ( var i=0; i < tree_list.length; i++ ) {
        for ( var y=0; y < s_list.length; y++ ) {
            opt = document.createElement('option');
            var purePath = tree_list[i].strip(' -');

            if ( purePath != '/' ) {
                var split_path = purePath.strip('/').split('/');
                var pureName = split_path[split_path.length - 1];
                split_path.pop();
                var rootPath = '/' + split_path.join('/');

                opt.dataset.pureName = pureName;
                opt.dataset.rootPath = rootPath;
            }

            opt.value = purePath; // Remove ---- . . .
            opt.innerHTML = escapeHtml(tree_list[i]);
            s_list[y].appendChild(opt);
        }
    }
}

function select_by_value(select_id, needle) {
    var s = document.getElementById(select_id);
    if ( s == undefined ) {
        console.log("+ select_by_value -> Undefined select.");
        return false;
    }

    var opts = s.options;
    for ( var i=0; i < opts.length; i++ ) {
        if ( opts[i].value == needle ) {
            s.selectedIndex = i;
            return true;
        }
    }

    console.log("Unknown value in select. Function resume without changing selectedIndex.");
    return false;
}

function sort_burgeons_by(value, asc) {
    var ref_array = Object.keys(client.burgeons).map(function (key) { return client.burgeons[key]; });
    var sorted_ref_array;

    if ( asc ) {
        sorted_ref_array = ref_array.sort( new Function('a', 'b', "return (a." + value + " > b. " + value + ") ? 1 : ((b." + value + " > a." + value + ") ? -1 : 0);" ) );
    }
    else {
        sorted_ref_array = ref_array.sort( new Function('a', 'b', "return (a." + value + " > b." + value + ") ? -1 : ((b." + value + " > a." + value + ") ? 1 : 0); " ) );
    }

    console.log(sorted_ref_array);

    remove_childs("body_enums");
    for ( var i = 0; i < sorted_ref_array.length; i++ )
        client.burgeons[sorted_ref_array[i].id].set();
}

function indexOfObjectArray(array, needle, property) {
    return array.map( function (e) { return e[property]; } ).indexOf(needle);
}
