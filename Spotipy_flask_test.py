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
import spotipy
import pdb

if os.path.exists('settings.ini'):
    config = ConfigParser()
    config.read('settings.ini')

    env = config['Environment Vars']
    for k, v in env.items():
        os.environ[k] = v

# PyLast
LASTFM_API_KEY = os.environ['LASTFM_API_KEY']
LASTFM_API_SECRET = os.environ['LASTFM_API_SECRET']

lastfm_username = os.environ['LASTFM_DEFAULT_USERNAME']
password_hash = os.environ['LASTFM_DEFAULT_PWHASH']
spotify_username = os.environ['SPOTIFY_DEFAULT_USERNAME']
sp = None

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
    request_token_params={'scope': 'playlist-modify-public'},
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
    try:
        image = get_cover_art(playing)
        print('{0} {1}'.format(playing.artist, playing.title))
        return render_template('currently-playing.html',
            artist=playing.artist, track=playing.title, image=image)
    except AttributeError:
        print('Nothing playing')
        return render_template('currently-playing.html',
                               artist='artist', track='title', image=DEFAULT_ALBUM_ART)

def get_cover_art(playing):
    try:
        album = playing.get_album()
        if not album:
            sp = spotipy.Spotify()
            search_str = '{0} {1}'.format(playing.artist, playing.title)
            track = sp.search(search_str)['tracks']['items']
            if track:
                print('returning art from Spotify')
                return track[0]['album']['images'][0]['url']
            else:
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
        print('{0} {1}'.format(playing.artist, playing.title))
        image = get_cover_art(playing)
        return jsonify(track=playing.title,
                       artist=playing.artist.get_name(),
                       image=image,
                       track_url=playing.get_url())
    except AttributeError:
        print('No data to update')
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
    global sp, spotify_username
    resp = spotify.authorized_response()
    if resp is None:
        return 'Access denied: reason={0} error={1}'.format(
            request.args['error_reason'],
            request.args['error_description']
        )
    if isinstance(resp, OAuthException):
        return 'Access denied: {0}'.format(resp.message)

    session['oauth_token'] = (resp['access_token'], '')
    token = session['oauth_token'][0]
    me = spotify.get('https://api.spotify.com/v1/me')
    spotify_username = me.data['id']
    sp = spotipy.Spotify(auth=token)
    playlists = sp.user_playlists(spotify_username)
    return display_playlists(playlists)
    # return 'Logged in as id={0} name={1} redirect={2}'.format(
    #     me.data['id'],
    #     me.data['display_name'],
    #     request.args.get('next')
    # )

def display_playlists(playlists):
    result = []
    for playlist in playlists['items']:
        result.append('<a href={2}>{0} | total tracks: {1}</a>'.format(
            playlist['name'], playlist['tracks']['total'],
            url_for('display_tracks', playlist_id=playlist['id'])))

    return '<br/>'.join(result)

@app.route('/list_tracks/<playlist_id>')
def display_tracks(playlist_id):
    global sp
    results = []
    playlist = sp.user_playlist(spotify_username, playlist_id)
    tracks = playlist['tracks']
    results += parse_tracks(tracks)
    page = 0
    while tracks['next']:
        page += 1
        tracks = sp.next(tracks)
        results += parse_tracks(tracks, page)

    return '<br/>'.join(results)

def parse_tracks(tracks, page=0):
    results = []
    for i, item in enumerate(tracks['items'], start=1):
        track = item['track']
        artist = track['artists'][0]['name']
        title = track['name']
        index = i + page + (page * 99)
        # play_count = get_user_play_count_in_track_info(artist, title)
        play_count = 0
        info = '{0}. {1}/{2} | {3}'.format(
            index, artist, title, play_count)
        results.append(info)

    return results
        # print(name, '-', artist, '|', track_id, '|', play_count)

def get_user_play_count_in_track_info(artist, title):
    # Arrange
    track = pylast.Track(
        artist=artist, title=title,
        network=network, username=lastfm_username)

    # Act
    try:
        count = track.get_userplaycount()
    except WSError:
        print('Unable to locate {0} - {1}'.format(artist, title))
    return count

@spotify.tokengetter
def get_spotify_oauth_token():
    return session.get('oauth_token')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
