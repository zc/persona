import bobo
import itsdangerous
import json
import logging
import os
import requests
import webob

logging.basicConfig(level='INFO')

login_html = """<html><head><title>Login</title>
<script src="https://login.persona.org/include.js"></script>
<script src="//ajax.googleapis.com/ajax/libs/dojo/1.8.3/dojo/dojo.js"></script>
<script src="login.js"></script>
</head>
<body class="tundra">

<button type="button" id="signin">Log in!</button>

</body></html>
"""

TOKEN = 'auth_token'

def factory(
    app,
    defauts,
    secret,
    url='http://localhost:8080',
    prefix='/persona',
    ):

    serializer = itsdangerous.URLSafeTimedSerializer(secret)

    @bobo.subroute(prefix)
    def routes(request):
        return Routes(request, url, prefix, serializer)

    persona_app = bobo.Application(bobo_resources = [routes])

    def run_app(env, start):
        request = webob.Request(env)
        token = request.cookies.get(TOKEN)
        old_email = email = None
        if token:
            email = serializer.loads(token)

            old_email = env.get('REMOTE_USER')
            env['REMOTE_USER'] = email

        try:
            return (persona_app if env['PATH_INFO'].startswith(prefix)
                    else app)(env, start)
        finally:
            if email:
                if old_user:
                    env['REMOTE_USER'] = old_user
                else:
                    del env['REMOTE_USER']

    return run_app

@bobo.get('/')
def test(bobo_request):
    return 'hi '+bobo_request.environ.get('REMOTE_USER', 'wtf?')

@bobo.scan_class
class Routes:

    def __init__(
        self,
        request,
        url,
        prefix,
        serializer,
        ):
        self.request = request
        self.url = url
        self.prefix = prefix
        self.serializer = serializer

    @bobo.query('/login.html')
    def login_html(self):
        return login_html

    @bobo.query('/login.js', content_type="application/javascript")
    def login_js(self):
        email = self.request.environ.get('REMOTE_USER')
        with open(os.path.join(os.path.dirname(__file__), 'login.js')) as f:
            return f.read() % dict(
                url=self.url,
                prefix=self.prefix,
                email = repr(str(email)) if email else 'null'
                )


    @bobo.post('/login')
    def login(self, assertion):

        # Send the assertion to Mozilla's verifier service.
        data = {'assertion': assertion, 'audience': self.url}
        resp = requests.post(
            'https://verifier.login.persona.org/verify', data=data, verify=True)

        # Did the verifier respond?
        if resp.ok:
            # Parse the response
            verification_data = json.loads(resp.content)

            # Check if the assertion was valid
            if verification_data['status'] == 'okay':
                email = verification_data['email']
                response = bobo.redirect(self.url)
                response.set_cookie(TOKEN, self.serializer.dumps(email))
                return response
            else:
                raise bobo.BoboException('403', verification_data['reason'])
        else:
            # Oops, something failed. Abort.
            raise ValueError("wtf")

    @bobo.post('/logout')
    def logout(self):
        response = bobo.redirect(self.url)
        response.set_cookie(TOKEN, '')
        return response
