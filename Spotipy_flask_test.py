__author__ = 'WisdomWolf'
import os
from flask import (
    Flask,
    redirect,
    url_for,
    session,
    request,
    jsonify,
    render_template
)
from flask_oauthlib.client import OAuth, OAuthException
from configparser import ConfigParser
import pylast

config = ConfigParser()
config.read('settings.ini')

# PyLast
LASTFM_API_KEY = os.environ['LASTFM_API_KEY']
LASTFM_API_SECRET = os.environ['LASTFM_API_SECRET']

lastfm_username = os.environ['LASTFM_DEFAULT_USERNAME']
password_hash = os.environ['LASTFM_DEFAULT_PWHASH']

network = pylast.LastFMNetwork(api_key=LASTFM_API_KEY, api_secret=LASTFM_API_SECRET,
                               username=lastfm_username,
                               password_hash=password_hash)

# Spotify
SPOTIFY_APP_ID = os.environ['SPOTIPY_CLIENT_ID']
SPOTIFY_APP_SECRET = os.environ['SPOTIPY_CLIENT_SECRET']

DEFAULT_ALBUM_ART = "http://upload.wikimedia.org/wikipedia/en/5/54/Public_image_ltd_album_cover.jpg"

app = Flask(__name__)
app.debug = True
app.secret_key = 'development'
oauth = OAuth(app)

spotify = oauth.remote_app(
    'spotify',
    consumer_key=SPOTIFY_APP_ID,
    consumer_secret=SPOTIFY_APP_SECRET,
    # Change the scope to match whatever it us you need
    # list of scopes can be found in the url below
    # https://developer.spotify.com/web-api/using-scopes/
    request_token_params={'scope': 'user-library-read'},
    base_url='https://accounts.spotify.com',
    request_token_url=None,
    access_token_url='/api/token',
    authorize_url='https://accounts.spotify.com/authorize'
)


@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/now-playing')
def now_playing():
    user = pylast.User(lastfm_username, network)
    return '{0} | {1}'.format(user.get_now_playing().artist, user.get_now_playing().title)

@app.route('/currently-playing/')
@app.route('/currently-playing/<username>')
def currently_playing(username=None):
    username = username or 'wisdomwolf'
    playing = pylast.User(username, network).get_now_playing()
    image = get_cover_art(playing)
    # print('{0} | {1}'.format(playing.artist, playing.title))
    return render_template('currently-playing.html',
        artist=playing.artist, track=playing.title, image=image)

def get_cover_art(playing):
    try:
        album = playing.get_album()
        if not album:
            return DEFAULT_ALBUM_ART
        else:
            return album.get_cover_image()
    except AttributeError:
        return DEFAULT_ALBUM_ART

@app.route('/update_now_playing')
def update_now_playing():
    username = request.args.get('username', '', type=str)
    try:
        playing = pylast.User(username, network).get_now_playing()
        image = get_cover_art(playing)
        return jsonify(track=playing.title,
                       artist=playing.artist.get_name(),
                       image=image,
                       track_url=playing.get_url())
    except AttributeError:
        return jsonify(track='track',
                       artist='artist',
                       image=DEFAULT_ALBUM_ART,
                       track_url='#')


@app.route('/recent-tracks')
def recent_tracks():
    user = pylast.User(lastfm_username, network)
    track_list = []
    print('{0} tracks found.'.format(len(user.get_recent_tracks())))
    for played_track in user.get_recent_tracks():
        track_list.append('{0} | {1}'.format(played_track.track.artist, played_track.track.title))

    return '<br/>'.join(track_list)

@app.route('/login')
def login():
    callback = url_for(
        'spotify_authorized',
        next=request.args.get('next') or request.referrer or None,
        _external=True
    )
    return spotify.authorize(callback=callback)


@app.route('/login/authorized')
def spotify_authorized():
    resp = spotify.authorized_response()
    if resp is None:
        return 'Access denied: reason={0} error={1}'.format(
            request.args['error_reason'],
            request.args['error_description']
        )
    if isinstance(resp, OAuthException):
        return 'Access denied: {0}'.format(resp.message)

    session['oauth_token'] = (resp['access_token'], '')
    me = spotify.get('https://api.spotify.com/v1/me')
    return 'Logged in as id={0} name={1} redirect={2}'.format(
        me.data['id'],
        me.data['display_name'],
        request.args.get('next')
    )


@spotify.tokengetter
def get_spotify_oauth_token():
    return session.get('oauth_token')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
