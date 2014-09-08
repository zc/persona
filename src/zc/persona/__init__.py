import bobo
import itsdangerous
import json
import os
import requests
import webob

TOKEN = 'auth_token'

def factory(
    app,
    defauts,
    secret,
    audience='http://localhost:8080',
    prefix='/persona',
    ):

    serializer = itsdangerous.URLSafeTimedSerializer(secret)

    @bobo.subroute(prefix)
    def routes(request):
        return Routes(request, audience, prefix, serializer)

    persona_app = bobo.Application(bobo_resources = [routes])

    def run_app(env, start):
        request = webob.Request(env)

        token = request.cookies.get(TOKEN)
        old_email = email = None
        if token:
            try:
                email = serializer.loads(token)
            except itsdangerous.BadTimeSignature:
                pass # just don't log them in
            else:
                old_email = env.get('REMOTE_USER')
                env['REMOTE_USER'] = email

        try:
            if env['PATH_INFO'].startswith(prefix):
                return persona_app(env, start)
            else:
                needs_login = []
                def start_response(status, headers, exc_info=None):
                    if status.startswith("401 "):
                        needs_login.append(0)
                    else:
                        start(status, headers, exc_info)
                it = app(env, start_response)
                if needs_login:
                    return bobo.redirect(
                        prefix+'/login.html?came_from='+env['PATH_INFO']
                        )(env, start)
                else:
                    return it
        finally:
            if email:
                if old_email:
                    env['REMOTE_USER'] = old_email
                else:
                    del env['REMOTE_USER']

    return run_app

@bobo.get('/')
@bobo.get('/test')
def test(bobo_request):
    return 'hi '+bobo_request.environ.get('REMOTE_USER', 'wtf?  aaaa')


html = """<html><head><title>Log%(inout)s</title>
<script src="https://login.persona.org/include.js"></script>
<script src="//ajax.googleapis.com/ajax/libs/dojo/1.8.3/dojo/dojo.js"></script>
<script>
came_from = "%(came_from)s"
</script>
<script src="login.js"></script>
</head>
<body class="tundra">
<button type="button" id="sign%(inout)s">Log %(inout)s!</button>
</body></html>
"""

@bobo.scan_class
class Routes:

    def __init__(
        self,
        request,
        audience,
        prefix,
        serializer,
        ):
        self.request = request
        self.audience = audience
        self.prefix = prefix
        self.serializer = serializer

    @bobo.query('/login.html')
    def login_html(self, came_from='/'):
        return html % dict(came_from = came_from,
                           inout='in',
                           )

    @bobo.query('/logout.html')
    def logout_html(self, came_from='/'):
        return html % dict(came_from = came_from,
                           inout='out',
                           )

    @bobo.query('/login.js', content_type="application/javascript")
    def login_js(self):
        email = self.request.environ.get('REMOTE_USER', '')
        with open(os.path.join(os.path.dirname(__file__), 'login.js')) as f:
            return f.read() % dict(
                prefix=self.prefix,
                email = email
                )


    @bobo.post('/login')
    def login(self, assertion):
        # Send the assertion to Mozilla's verifier service.
        data = {'assertion': assertion, 'audience': self.audience}
        resp = requests.post(
            'https://verifier.login.persona.org/verify', data=data, verify=True)

        # Did the verifier respond?
        if resp.ok:
            # Parse the response
            verification_data = json.loads(resp.content)

            # Check if the assertion was valid
            if verification_data['status'] == 'okay':
                email = verification_data['email']
                response = webob.Response('Logged in')
                response.set_cookie(TOKEN, self.serializer.dumps(email))
                return response
            else:
                raise bobo.BoboException('403', verification_data['reason'])
        else:
            # Oops, something failed. Abort.
            raise ValueError("wtf")

    @bobo.post('/logout')
    def logout(self):
        response = webob.Response('bye')
        response.set_cookie(TOKEN, '')
        return response
