require(
    ["dojo/domReady!"],
    function() {
        var signinLink = document.getElementById('signin');
        if (signinLink) {
            signinLink.onclick = function() { navigator.id.request(); };
        }
        var signoutLink = document.getElementById('signout');
        if (signoutLink) {
            signoutLink.onclick = function() { navigator.id.logout(); };
        }
        var email = "%(email)s";
        navigator.id.watch(
            {
                loggedInUser: email.length > 0 ? email : null,
                onlogin: function(assertion) {
                    dojo.xhr.post(
                        {
                            url: "%(prefix)s/login",
                            content: { assertion: assertion },
                            load: function () {
                                window.location = came_from;
                            },
                            error: function(err) {
                                navigator.id.logout();
                                alert("Login failure: " + err.response.data);
                            }
                        });
                },
                onlogout: function() {
                    dojo.xhr.post(
                        {
                            url: '%(prefix)s/logout',
                            load: function () {
                                window.location = came_from;
                            },
                            error: function(err) {
                                alert("Logout failure: " + err); }
                        });
                }
            });
    });
