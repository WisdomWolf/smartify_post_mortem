NowPlaying = function(api, user, interval) {
    this.api = api;
    this.user = user;
    
    /* AutoUpdate frequency - Last.fm API rate limits at 1/sec */
    this.interval = interval || 5;
};
NowPlaying.prototype = {
    
    display: function(track)
    {        
        $('#artist').text(track.artist);
        $('#track').text(track.name);
        $('#track').attr('href', track.url);
        $('#img').attr('src', track.img);
        $('#playing').text(track.artist + ' - ' + track.name);
        $('#head').text(username + ' is listening to: ');
    },
    
    update: function()
    {
        this.api.getNowPlayingTrack(
            this.user,
            jQuery.proxy(this.handleResponse, this), 
            function(error) { console && console.log(error); }
        );
    },
    
    autoUpdate: function()
    {
        // Do an immediate update, don't wait an interval period
        this.update();
        
        // Try and avoid repainting the screen when the track hasn't changed
        setInterval(jQuery.proxy(this.update, this), this.interval * 1000);
    },
    
    handleResponse: function(response)
    {
        if (response) {
            var image;
            if (response.image[3]['#text']) {
                image = response.image[3]['#text'];
            }
            else if (response.image[2]['#text']) {
                image = response.image[2]['#text'];
            }
            else if (response.image[1]['#text']) {
                image = response.image[1]['#text'];
            }
            else {
                image = "http://upload.wikimedia.org/wikipedia/en/5/54/Public_image_ltd_album_cover.jpg";
            }
            this.display({
                // The API response can vary depending on the user, so be defensive
                artist: response.artist['#text'] || response.artist.name,
                name: response.name,
                url: response.url,
                img: image
            });
        }
        else {
            this.display({artist: ' ', name: '', url: '', img: ''});
        }
    }
};