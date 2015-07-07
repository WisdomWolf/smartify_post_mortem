__author__ = 'WisdomWolf'
from configparser import ConfigParser
import datetime
import itertools
import os
import pdb
import pylast
import spotipy
import spotipy.util as util
import sys
import time

config = ConfigParser()
config.read('settings.ini')

# PyLast
API_KEY = config['Last-FM API']['lastfm_api_key']
API_SECRET = config['Last-FM API']['lastfm_api_secret']

lastfm_username = config['LastFM']['Username']
password_hash = config['LastFM']['Password Hash']

network = pylast.LastFMNetwork(api_key=API_KEY, api_secret=API_SECRET,
                               username=lastfm_username,
                               password_hash=password_hash)

# SpotiPy
scope = 'playlist-modify-public'
os.environ['SPOTIPY_CLIENT_ID'] = config['Spotify API']['spotipy_client_id']
os.environ['SPOTIPY_CLIENT_SECRET'] = config['Spotify API']['spotipy_client_secret']
os.environ['SPOTIPY_REDIRECT_URI'] = config['Spotify API']['spotipy_callback_url']
heard_songs = []
track_total = 0


def show_tracks(tracks, page=0):
    for i, item in enumerate(tracks['items'], start=1):
        track = item['track']
        title = track['name']
        artist = track['artists'][0]['name']
        index = i + page + (page * 99)
        count = get_user_play_count_in_track_info(artist, title)
        info = '{0:<3}{1:>50} {2:<50}     {3}'.format(index, artist, title, count)
        print(info)
        csv_info = '{0},"{1}","{2}",{3}\n'.format(index, artist, title, count)
        # with open('playlist_counts.csv', 'a+') as playcount_file:
        #     print(index)
        #     playcount_file.write(csv_info)

def parse_tracks(tracks, page=0):
    for i, item in enumerate(tracks['items'], start=1):
        track = item['track']
        artist = track['artists'][0]['name']
        name = track['name']
        track_id = track['id']
        index = i + page + (page * 99)
        play_count = get_user_play_count_in_track_info(artist, name)
        if play_count > 0:
            heard_songs.append(track_id)
        update_progress(int(index / track_total * 100))
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

def display_playlists(playlists):
    for playlist in playlists['items']:
        if playlist['owner']['id'] == username:
            print()
            print(playlist['name'], '-', playlist['id'])
            track_total = playlist['tracks']['total']
            print('  total tracks', track_total)

def split_seq(iterable, size):
    it = iter(iterable)
    item = list(itertools.islice(it, size))
    while item:
        yield item
        item = list(itertools.islice(it, size))

def update_progress(progress):
    sys.stdout.write('\r[{0}] {1}%'.format('#'*int(progress/10), progress))


if __name__ == '__main__':
    if len(sys.argv) > 1:
        username = sys.argv[1]
    else:
        try:
            username = config['Spotify']['Username']
            print('reading username from ini file')
        except:
            print("Usage: %s username" % (sys.argv[0],))
            sys.exit()

    username = username.lower()
    token = util.prompt_for_user_token(username, scope)

    if token:
        sp = spotipy.Spotify(auth=token)
        start_time = round(time.time())
        playlists = sp.user_playlists(username)
        playlist_id = '7N1WdCoTTSql2mN8OuaYfD'
        playlist = sp.user_playlist(username, playlist_id)
        track_total = playlist['tracks']['total']
        print('Are you sure you want to filter {0}({1})'.format(
            playlist['name'], track_total))
        choice = input('-> ')
        if choice.casefold() == 'yes' or choice.casefold() == 'y':
            print(datetime.datetime.now())
            print('Preparing to parse playlist...')
        else:
            print('Exiting...')
            time.sleep(3)
            sys.exit()

        results = sp.user_playlist(username, playlist['id'], fields="tracks,next")
        tracks = results['tracks']
        parse_tracks(tracks)
        page = 0
        while tracks['next']:
            page += 1
            tracks = sp.next(tracks)
            parse_tracks(tracks, page)

        print('\nParsed {0} tracks.\nPreparing to remove {1} songs.'.format(
            str(track_total), len(heard_songs)
        ))

        if heard_songs:
            split_lists = list(split_seq(heard_songs, 99))
            for l in split_lists:
                sp.user_playlist_remove_all_occurrences_of_tracks(username,
                                                                  playlist_id, l)
        end_time = round(time.time())
        print('Completed. Duration: {0} Process Time: {1}'.format(
            datetime.timedelta(seconds=(end_time - start_time)), time.process_time()))

        pdb.set_trace()

                # results = sp.user_playlist(username, playlist['id'], fields="tracks,next")
                # tracks = results['tracks']
                # show_tracks(tracks)
                # page = 0
                # while tracks['next']:
                #     page += 1
                #     tracks = sp.next(tracks)
                #     show_tracks(tracks, page)
                # print('end of playlist:{0}'.format(playlist['name']))
    else:
        print("Can't get token for", username)
