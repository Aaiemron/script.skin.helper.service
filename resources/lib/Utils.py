#!/usr/bin/python
# -*- coding: utf-8 -*-

import xbmcplugin
import xbmcaddon
import xbmcgui
import xbmc
import xbmcvfs
import os
import json
import re, urlparse
import requests
import sys
import urllib,urllib2,re
import base64
from traceback import print_exc
from datetime import datetime
import _strptime
import time
import unicodedata

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_ICON = ADDON.getAddonInfo('icon')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_PATH = ADDON.getAddonInfo('path').decode("utf-8")
ADDON_VERSION = ADDON.getAddonInfo('version')
ADDON_DATA_PATH = xbmc.translatePath("special://profile/addon_data/%s" % ADDON_ID).decode("utf-8")
KODI_VERSION  = int(xbmc.getInfoLabel( "System.BuildVersion" ).split(".")[0])
WINDOW = xbmcgui.Window(10000)
SETTING = ADDON.getSetting

fields_base = '"dateadded", "file", "lastplayed","plot", "title", "art", "playcount",'
fields_file = fields_base + '"streamdetails", "director", "resume", "runtime",'
fields_movies = fields_file + '"plotoutline", "sorttitle", "cast", "votes", "showlink", "top250", "trailer", "year", "country", "studio", "set", "genre", "mpaa", "setid", "rating", "tag", "tagline", "writer", "originaltitle", "imdbnumber"'
fields_tvshows = fields_base + '"sorttitle", "mpaa", "premiered", "year", "episode", "watchedepisodes", "votes", "rating", "studio", "season", "genre", "cast", "episodeguide", "tag", "originaltitle", "imdbnumber"'
fields_episodes = fields_file + '"cast", "productioncode", "rating", "votes", "episode", "showtitle", "tvshowid", "season", "firstaired", "writer", "originaltitle"'
fields_musicvideos = fields_file + '"genre", "artist", "tag", "album", "track", "studio", "year"'
fields_files = fields_file + fields_movies + ", " + fields_tvshows + ", " + fields_episodes
fields_songs = '"artist", "title", "rating", "fanart", "thumbnail", "duration", "playcount", "comment", "file", "album", "lastplayed"'
fields_albums = '"title", "fanart", "thumbnail", "genre", "displayartist", "artist", "genreid", "musicbrainzalbumartistid", "year", "rating", "artistid", "musicbrainzalbumid", "theme", "description", "type", "style", "playcount", "albumlabel", "mood"'
fields_pvrrecordings = '"art", "channel", "directory", "endtime", "file", "genre", "icon", "playcount", "plot", "plotoutline", "resume", "runtime", "starttime", "streamurl", "title"'

PVRartTypes = [ ("thumb","thumb.jpg"),("poster","poster.jpg"),("fanart","fanart.jpg"),("banner","banner.jpg"),("landscape","landscape.jpg"),("clearlogo","logo.png"),("clearart","clearart.png"),("channellogo","channellogo.png") ]

def logMsg(msg, level = 1):
    doDebugLog = False
    if doDebugLog or level == 0:
        if isinstance(msg, unicode):
            msg = msg.encode('utf-8')
        xbmc.log("Skin Helper Service --> " + msg)
        if "exception" in msg.lower() or "error" in msg.lower():
            print_exc()
            
def getContentPath(libPath):
    if "$INFO" in libPath and not "reload=" in libPath:
        libPath = libPath.replace("$INFO[Window(Home).Property(", "")
        libPath = libPath.replace(")]", "")
        libPath = WINDOW.getProperty(libPath)    
    if "Activate" in libPath:
        if "ActivateWindow(MusicLibrary," in libPath:
            libPath = libPath.replace("ActivateWindow(MusicLibrary," ,"musicdb://").lower()
            libPath = libPath.replace(",return","/")
            libPath = libPath.replace(", return","/")
        else:
            libPath = libPath.split(",",1)[1]
            libPath = libPath.replace(",return","")
            libPath = libPath.replace(", return","")
        
        libPath = libPath.replace(")","")
        libPath = libPath.replace("\"","")
        libPath = libPath.replace("musicdb://special://","special://")
        libPath = libPath.replace("videodb://special://","special://")
    if "&reload=" in libPath:
        libPath = libPath.split("&reload=")[0]
    return libPath

def getJSON(method,params):
    json_response = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method" : "%s", "params": %s, "id":1 }' %(method, try_encode(params)))
    jsonobject = json.loads(json_response.decode('utf-8','replace'))
   
    if(jsonobject.has_key('result')):
        jsonobject = jsonobject['result']
        if jsonobject.has_key('files'):
            return jsonobject['files']
        elif jsonobject.has_key('movies'):
            return jsonobject['movies']
        elif jsonobject.has_key('tvshows'):
            return jsonobject['tvshows']
        elif jsonobject.has_key('episodes'):
            return jsonobject['episodes']
        elif jsonobject.has_key('musicvideos'):
            return jsonobject['musicvideos']
        elif jsonobject.has_key('channels'):
            return jsonobject['channels']
        elif jsonobject.has_key('recordings'):
            return jsonobject['recordings']
        elif jsonobject.has_key('songs'):
            return jsonobject['songs']
        elif jsonobject.has_key('albums'):
            return jsonobject['albums']
        elif jsonobject.has_key('songdetails'):
            return jsonobject['songdetails']
        elif jsonobject.has_key('albumdetails'):
            return jsonobject['albumdetails']
        elif jsonobject.has_key('artistdetails'):
            return jsonobject['artistdetails']
        elif jsonobject.has_key('favourites'):
            if jsonobject['favourites']:
                return jsonobject['favourites']
            else:
                return {}
        elif jsonobject.has_key('tvshowdetails'):
            return jsonobject['tvshowdetails']
        elif jsonobject.has_key('episodedetails'):
            return jsonobject['episodedetails']
        elif jsonobject.has_key('moviedetails'):
            return jsonobject['moviedetails']
        elif jsonobject.has_key('setdetails'):
            return jsonobject['setdetails']
        elif jsonobject.has_key('sets'):
            return jsonobject['sets']
        elif jsonobject.has_key('video'):
            return jsonobject['video']
        elif jsonobject.has_key('artists'):
            return jsonobject['artists']
        elif jsonobject.has_key('sources'):
            if jsonobject['sources']:
                return jsonobject['sources']
            else:
                return {}
        elif jsonobject.has_key('addons'):
            return jsonobject['addons']
        else:
            logMsg("getJson - invalid result for Method %s - params: %s - response: %s" %(method,params, str(jsonobject))) 
            return {}
    else:
        logMsg("getJson - empty result for Method %s - params: %s - response: %s" %(method,params, str(jsonobject))) 
        return {}

def setAddonsettings():
    #get the addonsettings and store them in memory
    WINDOW.setProperty("pvrthumbspath",SETTING("pvrthumbspath"))
    xbmc.executebuiltin("Skin.SetString(pvrthumbspath,%s)" %SETTING("pvrthumbspath"))
    WINDOW.setProperty("cacheRecordings",SETTING("cacheRecordings"))
    WINDOW.setProperty("cacheGuideEntries",SETTING("cacheGuideEntries"))
    WINDOW.setProperty("customRecordingsPath",SETTING("customRecordingsPath"))
    WINDOW.setProperty("useTMDBLookups",SETTING("useTMDBLookups"))
    WINDOW.setProperty("useGoogleLookups",SETTING("useGoogleLookups"))
    WINDOW.setProperty("useYoutubeLookups",SETTING("useYoutubeLookups"))
    WINDOW.setProperty("useLocalLibraryLookups",SETTING("useLocalLibraryLookups"))
    WINDOW.setProperty("customlookuppath",SETTING("customlookuppath"))
    WINDOW.setProperty("useFanArtTv",SETTING("useFanArtTv"))

def try_encode(text, encoding="utf-8"):
    try:
        return text.encode(encoding,"ignore")
    except:
        return text       

def try_decode(text, encoding="utf-8"):
    try:
        return text.decode(encoding,"ignore")
    except:
        return text       
         
def setSkinVersion():
    skin = xbmc.getSkinDir()
    skinLabel = xbmcaddon.Addon(id=skin).getAddonInfo('name')
    skinVersion = xbmcaddon.Addon(id=skin).getAddonInfo('version')
    WINDOW.setProperty("SkinHelper.skinTitle",skinLabel + " - " + xbmc.getLocalizedString(19114) + ": " + skinVersion)
    WINDOW.setProperty("SkinHelper.skinVersion",xbmc.getLocalizedString(19114) + ": " + skinVersion)
    WINDOW.setProperty("SkinHelper.Version",ADDON_VERSION.replace(".",""))
    
def createListItem(item):

    itemtype = "Video"
    if "type" in item:
        if "artist" in item["type"] or "song" in item["type"] or "album" in item["type"]:
            itemtype = "Music"

    liz = xbmcgui.ListItem(item['title'])
    liz.setInfo( type=itemtype, infoLabels={ "Title": item['title'] })
    liz.setProperty('IsPlayable', 'true')
    season = None
    episode = None
    
    if "duration" in item:
        liz.setInfo( type=itemtype, infoLabels={ "duration": item['duration'] })
    
    if "file" in item:
        liz.setPath(item['file'])
        liz.setProperty("path", item['file'])
    
    if "episode" in item:
        episode = "%.2d" % float(item['episode'])
        liz.setInfo( type=itemtype, infoLabels={ "Episode": item['episode'] })
    
    if "season" in item:
        season = "%.2d" % float(item['season'])
        liz.setInfo( type=itemtype, infoLabels={ "Season": item['season'] })
        
    if season and episode:
        episodeno = "s%se%s" %(season,episode)
        liz.setProperty("episodeno", episodeno)
    
    if "episodeid" in item:
        liz.setProperty("DBID", str(item['episodeid']))
        liz.setInfo( type=itemtype, infoLabels={ "DBID": str(item['episodeid']) })
        liz.setIconImage('DefaultTVShows.png')
        
    if "songid" in item:
        liz.setProperty("DBID", str(item['songid']))
        liz.setIconImage('DefaultAudio.png')
        
    if "movieid" in item:
        liz.setProperty("DBID", str(item['movieid']))
        liz.setInfo( type=itemtype, infoLabels={ "DBID": str(item['movieid']) })
        liz.setIconImage('DefaultMovies.png')
    
    if "musicvideoid" in item:
        liz.setProperty("DBID", str(item['musicvideoid']))
        liz.setIconImage('DefaultMusicVideos.png')
    
    if "type" in item:
        liz.setProperty("type", item['type'])
    
    if "plot" in item:
        liz.setInfo( type=itemtype, infoLabels={ "Plot": item['plot'] })
    
    if "album_description" in item:
        liz.setProperty("Album_Description",item['album_description'])
    
    if "artist" in item:
        if itemtype == "Music":
            liz.setInfo( type=itemtype, infoLabels={ "Artist": " / ".join(item['artist']) })
        else:
            liz.setInfo( type=itemtype, infoLabels={ "Artist": item['artist'] })
        
    if "votes" in item:
        liz.setInfo( type=itemtype, infoLabels={ "votes": item['votes'] })
    
    if "trailer" in item:
        liz.setInfo( type=itemtype, infoLabels={ "trailer": item['trailer'] })
        liz.setProperty("trailer", item['trailer'])
        
    if "dateadded" in item:
        liz.setInfo( type=itemtype, infoLabels={ "dateadded": item['dateadded'] })
        
    if "album" in item:
        liz.setInfo( type=itemtype, infoLabels={ "album": item['album'] })
        
    if "plotoutline" in item:
        liz.setInfo( type=itemtype, infoLabels={ "plotoutline ": item['plotoutline'] })
        
    if "studio" in item:
        liz.setInfo( type=itemtype, infoLabels={ "studio": " / ".join(item['studio']) })
        
    if "playcount" in item:
        liz.setInfo( type=itemtype, infoLabels={ "playcount": item['playcount'] })
        
    if "mpaa" in item:
        liz.setInfo( type=itemtype, infoLabels={ "mpaa": item['mpaa'] })
        
    if "tagline" in item:
        liz.setInfo( type=itemtype, infoLabels={ "tagline": item['tagline'] })
    
    if "showtitle" in item:
        liz.setInfo( type=itemtype, infoLabels={ "TVshowTitle": item['showtitle'] })
    
    if "rating" in item:
        liz.setInfo( type=itemtype, infoLabels={ "Rating": str(round(float(item['rating']),1)) })
    
    if "playcount" in item:
        liz.setInfo( type=itemtype, infoLabels={ "Playcount": item['playcount'] })
    
    if "director" in item:
        director = item['director']
        if isinstance(director, list): director = " / ".join(director)
        liz.setInfo( type=itemtype, infoLabels={ "Director": director })
    
    if "writer" in item:
        writer = item['writer']
        if isinstance(writer, list): writer = " / ".join(writer)
        liz.setInfo( type=itemtype, infoLabels={ "Writer": writer })
    
    if "genre" in item:
        genre = item['genre']
        if isinstance(genre, list): genre = " / ".join(genre)
        liz.setInfo( type=itemtype, infoLabels={ "genre": genre })
        
    if "year" in item:
        liz.setInfo( type=itemtype, infoLabels={ "year": item['year'] })
    
    if "firstaired" in item:
        liz.setInfo( type=itemtype, infoLabels={ "premiered": item['firstaired'] })

    if "premiered" in item:
        liz.setInfo( type=itemtype, infoLabels={ "premiered": item['premiered'] })
        
    if "cast" in item:
        if item["cast"]:
            listCast = []
            listCastAndRole = []
            for castmember in item["cast"]:
                listCast.append( castmember["name"] )
                listCastAndRole.append( (castmember["name"], castmember["role"]) ) 
            cast = [listCast, listCastAndRole]
            liz.setInfo( type=itemtype, infoLabels={ "Cast": cast[0] })
            liz.setInfo( type=itemtype, infoLabels={ "CastAndRole": cast[1] })
    
    if "resume" in item:
        liz.setProperty("resumetime", str(item['resume']['position']))
        liz.setProperty("totaltime", str(item['resume']['total']))
    
    if "art" in item:
        art = item['art']
        if art and not art.get("fanart") and art.get("tvshow.fanart"):
            art["fanart"] = art.get("tvshow.fanart")
        if art and not art.get("poster") and art.get("tvshow.poster"):
            art["poster"] = art.get("tvshow.poster")
        if art and not art.get("clearlogo") and art.get("tvshow.clearlogo"):
            art["clearlogo"] = art.get("tvshow.clearlogo")
        if art and not art.get("landscape") and art.get("tvshow.landscape"):
            art["landscape"] = art.get("tvshow.landscape")
        thumb = None
        if item['art'].get('thumb',''): thumb = item['art'].get('thumb','')
        elif item.get('icon',''): thumb = item.get('icon','')
        elif item['art'].get('poster',''): thumb = item['art'].get('poster','')
        liz.setThumbnailImage(thumb)
    else:
        art = []
        if "fanart" in item:
            art.append(("fanart",item["fanart"]))
        if "thumbnail" in item:
            art.append(("thumb",item["thumbnail"]))
            liz.setThumbnailImage(item["thumbnail"])
        elif "icon" in item:
            art.append(("thumb",item["icon"]))
            liz.setIconImage(item["icon"])
    liz.setArt(art)
    
    hasVideoStream = False
    if "streamdetails" in item:
        for key, value in item['streamdetails'].iteritems():
            for stream in value:
                if 'video' in key: hasVideoStream = True
                liz.addStreamInfo(key, stream)

    if not hasVideoStream and "runtime" in item:
        stream = {'duration': item['runtime']}
        liz.addStreamInfo("video", stream)
    
    #pvr properties
    if "progresspercentage" in item:
        liz.setInfo( type=itemtype, infoLabels={ "Progress": item['progresspercentage'] })
    if "starttime" in item:
        starttime = getLocalDateTimeFromUtc(item['starttime'])
        liz.setProperty("StartTime", starttime[1])
        liz.setProperty("StartDate", starttime[0])
        endtime = getLocalDateTimeFromUtc(item['endtime'])
        liz.setProperty("EndTime", endtime[1])
        liz.setProperty("EndDate", endtime[0])
        fulldate = starttime[0] + " " + starttime[1] + "-" + endtime[1]
        liz.setProperty("Date",fulldate )
    if "channelicon" in item:
        liz.setProperty("ChannelIcon", item['channelicon'])
    if "episodename" in item:
        liz.setProperty("EpisodeName", item['episodename'])
        liz.setInfo( type=itemtype, infoLabels={ "EpisodeName": item['episodename'] })
    if "channel" in item:
        liz.setInfo( type=itemtype, infoLabels={ "Channel": item['channel'] })
        liz.setInfo( type=itemtype, infoLabels={ "ChannelName": item['channel'] })
        liz.setProperty("ChannelName", item['channel'])
        liz.setProperty("Channel", item['channel'])
        liz.setLabel2(item['channel'])
        
    return liz
    
def detectPluginContent(plugin,skipscan=False):
    #based on the properties in the listitem we try to detect the content
    image = None
    contentType = None
    #load from cache first
    cache = WINDOW.getProperty("skinhelper-widgetcontenttype")
    if cache:
        cache = eval(cache)
        if cache and cache.has_key(plugin):
            contentType = cache[plugin][0]
            image = cache[plugin][1]
            return (contentType, image)
    else: cache = {}
        
    #probe path to determine content
    if not contentType:
        #safety check: check if no library windows are active to prevent any addons setting the view
        curWindow = xbmc.getInfoLabel("$INFO[Window.Property(xmlfile)]")
        if curWindow.endswith("Nav.xml") or curWindow == "AddonBrowser.xml" or curWindow.startswith("MyPVR"):
            return None, None
        
        if not skipscan:
            media_array = getJSON('Files.GetDirectory','{ "directory": "%s", "media": "files", "properties": ["title", "file", "thumbnail", "episode", "showtitle", "season", "album", "artist", "imdbnumber", "firstaired", "mpaa", "trailer", "studio", "art"], "limits": {"end":1} }' %plugin)
            if not media_array: contentType="empty"
            for item in media_array:
                if item.has_key("art") and not image:
                    if item["art"].has_key("fanart") and not image:
                        image = item["art"]["fanart"]
                    elif item["art"].has_key("tvshow.fanart") and not image:
                        image = item["art"]["tvshow.fanart"]
                    elif item["art"].has_key("thumb") and not image:
                        image = item["art"]["thumb"]
                    elif item.has_key("fanart_image") and not image:
                        image = item["fanart_image"]
                    elif item.has_key("thumbnail") and not image:
                        image = item["thumbnail"]
                if not item.has_key("showtitle") and not item.has_key("artist"):
                    #these properties are only returned in the json response if we're looking at actual file content...
                    # if it's missing it means this is a main directory listing and no need to scan the underlying listitems.
                    contentType = "files"
                    break
                if not item.has_key("showtitle") and item.has_key("artist"):
                    ##### AUDIO ITEMS ####
                    if item["type"] == "artist" or item["artist"][0] == item["title"]:
                        contentType = "artists"
                        break
                    elif item["type"] == "album" or item["album"] == item["title"]:
                        contentType = "albums"
                        break
                    elif (item["type"] == "song" and not "play_album" in item["file"]) or (item["artist"] and item["album"]):
                        contentType = "songs"
                        break
                else:    
                    ##### VIDEO ITEMS ####
                    if (item["showtitle"] and not item["artist"]):
                        #this is a tvshow, episode or season...
                        if item["type"] == "season" or (item["season"] > -1 and item["episode"] == -1):
                            contentType = "seasons"
                            break
                        elif item["type"] == "episode" or item["season"] > -1 and item["episode"] > -1:
                            contentType = "episodes"
                            break
                        else:
                            contentType = "tvshows"
                            break
                    elif (item["artist"]):
                        #this is a musicvideo!
                        contentType = "musicvideos"
                        break
                    elif item["type"] == "movie" or item["imdbnumber"] or item["mpaa"] or item["trailer"] or item["studio"]:
                        contentType = "movies"
                        break
    
    #last resort or skipscan chosen - detect content based on the path
    if not contentType:
        if "movie" in plugin or "box" in plugin or "dvd" in plugin or "rentals" in plugin:
            contentType = "movies"
        elif "album" in plugin:
            contentType = "albums"
        elif "show" in plugin:
            contentType = "tvshows"
        elif "song" in plugin:
            contentType = "songs"
        elif "musicvideo" in plugin:
            contentType = "musicvideos"
        else:
            contentType = "unknown"
        
    #save to cache
    cache[plugin] = (contentType,image)
    cache = repr(cache)
    if contentType != "empty": WINDOW.setProperty("skinhelper-widgetcontenttype-persistant",cache)
    WINDOW.setProperty("skinhelper-widgetcontenttype",cache)
    
    #return the values
    return (contentType, getCleanImage(image))

def getLocalDateTimeFromUtc(timestring):
    try:
        systemtime = xbmc.getInfoLabel("System.Time")
        utc = datetime.fromtimestamp(time.mktime(time.strptime(timestring, '%Y-%m-%d %H:%M:%S')))
        epoch = time.mktime(utc.timetuple())
        offset = datetime.fromtimestamp (epoch) - datetime.utcfromtimestamp(epoch)
        correcttime = utc + offset
        if "AM" in systemtime or "PM" in systemtime:
            return (correcttime.strftime("%Y-%m-%d"),correcttime.strftime("%I:%M %p"))
        else:
            return (correcttime.strftime("%d-%m-%Y"),correcttime.strftime("%H:%M"))
    except:
        logMsg("ERROR in getLocalDateTimeFromUtc --> " + timestring, 0)
        
        return (timestring,timestring)

def getfanartTVimages(type,id):
    #gets fanart.tv images for given tmdb id
    api_key = "639191cb0774661597f28a47e7e2bad5"
    artwork = {}
    
    logMsg("get fanart.tv images for type: %s - id: %s" %(type,id))
    
    if type == "movie":
        url = 'http://webservice.fanart.tv/v3/movies/%s?api_key=%s' %(id,api_key)
    else:
        url = 'http://webservice.fanart.tv/v3/tv/%s?api_key=%s' %(id,api_key)
    response = requests.get(url)
    data = json.loads(response.content.decode('utf-8','replace'))
    if data:
        if data.has_key("movielogo") and len(data["movielogo"]) > 0:
            artwork["clearlogo"] = data["movielogo"][0].get("url")
        if data.has_key("hdmovielogo") and len(data["hdmovielogo"]) > 0:
            artwork["clearlogo"] = data["hdmovielogo"][0].get("url")
        if data.has_key("moviedisc") and len(data["moviedisc"]) > 0:
            artwork["discart"] = data["moviedisc"][0].get("url")  
        if data.has_key("movieclearart") and len(data["movieclearart"]) > 0:
            artwork["clearart"] = data["movieclearart"][0].get("url")
        if data.has_key("hdmovieclearart") and len(data["hdmovieclearart"]) > 0:
            artwork["clearart"] = data["hdmovieclearart"][0].get("url")
        if data.has_key("moviebanner") and len(data["moviebanner"]) > 0:
            artwork["banner"] = data["moviebanner"][0].get("url")
        if data.has_key("moviethumb") and len(data["moviethumb"]) > 0:
            artwork["landscape"] = data["moviethumb"][0].get("url")           
        if data.has_key("clearart") and len(data["clearart"]) > 0:
            artwork["clearart"] = data["clearart"][0].get("url")
        if data.has_key("hdclearart") and len(data["hdclearart"]) > 0:
            artwork["clearart"] = data["hdclearart"][0].get("url")
        if data.has_key("clearlogo") and len(data["clearlogo"]) > 0:
            artwork["clearlogo"] = data["clearlogo"][0].get("url")
        if data.has_key("tvthumb") and len(data["tvthumb"]) > 0:
            artwork["landscape"] = data["tvthumb"][0].get("url")
        if data.has_key("tvbanner") and len(data["tvbanner"]) > 0:
            artwork["banner"] = data["tvbanner"][0].get("url")
        if data.has_key("showbackground") and len(data["showbackground"]) > 0:
            artwork["fanart"] = data["showbackground"][0].get("url")
        if data.has_key("moviebackground") and len(data["moviebackground"]) > 0:
            artwork["fanart"] = data["moviebackground"][0].get("url")
        if data.has_key("tvposter") and len(data["tvposter"]) > 0:
            artwork["poster"] = data["tvposter"][0].get("url")
        if data.has_key("movieposter") and len(data["movieposter"]) > 0:
            artwork["poster"] = data["movieposter"][0].get("url")
    return artwork

def getOfficialArtWork(title,includeAllArtwork=True):
    #perform search on TMDB and return artwork
    apiKey = base64.b64decode("NDc2N2I0YjJiYjk0YjEwNGZhNTUxNWM1ZmY0ZTFmZWM=")
    artwork = {}
    coverUrl = ""
    fanartUrl = ""
    matchFound = False
    media_id = None
    media_type = None
    try: 
        url = 'http://api.themoviedb.org/3/search/multi?api_key=%s&language=en&query=%s' %(apiKey,try_encode(title))
        response = requests.get(url)
        data = json.loads(response.content.decode('utf-8','replace'))
        if data and data.get("results",None):
            for item in data["results"]:
                name = item.get("name")
                if not name: name = item.get("title")
                if name:
                    original_name = item.get("original_name","")
                    id = item.get("id","")
                    media_type = item.get("media_type","")
                    title_alt = title.lower().replace(" ","").replace("-","").replace(":","").replace("&","").replace(",","")
                    name_alt = name.lower().replace(" ","").replace("-","").replace(":","").replace("&","").replace(",","")
                    org_name_alt = original_name.lower().replace(" ","").replace("-","").replace(":","").replace("&","").replace(",","")
                    
                    original_name = item.get("original_name")
                    if title in name == title or original_name == title:
                        matchFound = True
                    elif name.split(" (")[0] == title or title_alt == name_alt or title_alt == org_name_alt:
                        matchFound = True    
                    if matchFound:
                        coverUrl = item.get("poster_path","")
                        fanartUrl = item.get("backdrop_path","")
                        logMsg("getTMDBimage - TMDB match found for %s !" %title)
                        #lookup external tmdb_id and perform artwork lookup on fanart.tv
                        if WINDOW.getProperty("useFanArtTv") == "true" and id:
                            if media_type == "movie":
                                url = 'http://api.themoviedb.org/3/movie/%s?api_key=%s' %(id,apiKey)
                                idparam = "imdb_id"
                            else:
                                url = 'http://api.themoviedb.org/3/tv/%s/external_ids?api_key=%s' %(id,apiKey)
                                idparam = "tvdb_id"
                            response = requests.get(url)
                            data = json.loads(response.content.decode('utf-8','replace'))
                            if data: 
                                media_id = data.get(idparam) 
                        break
        
        #lookup artwork on fanart.tv
        if media_id and media_type:
            artwork = getfanartTVimages(media_type,media_id)
        
        #use tmdb art as fallback when no fanart.tv art
        if coverUrl and not artwork.get("poster"):
            artwork["poster"] = "http://image.tmdb.org/t/p/original"+coverUrl  
        if fanartUrl and not artwork.get("fanart"):
            artwork["fanart"] = "http://image.tmdb.org/t/p/original"+fanartUrl

        return artwork
    
    except Exception as e:
        if "getaddrinfo failed" in str(e):
            #no internet access - disable lookups for now
            WINDOW.setProperty("SkinHelper.DisableInternetLookups","disable")
            logMsg("getOfficialArtWork - no internet access, disabling internet lookups for now")
        else:
            logMsg("getOfficialArtWork - Error in getOfficialArtWork --> " + str(e),0)
    
def downloadImage(imageUrl,foldername, filename):
    try:
        PVRthumbsPath = WINDOW.getProperty("pvrthumbspath").decode("utf-8")
        if not xbmcvfs.exists(PVRthumbsPath):
            xbmcvfs.mkdir(PVRthumbsPath)
        thumbsPath = os.path.join(PVRthumbsPath,normalize_string(foldername)) + os.sep
        if not xbmcvfs.exists(thumbsPath):
            xbmcvfs.mkdir(thumbsPath)
        newFile = os.path.join(thumbsPath,filename)
        xbmcvfs.copy(imageUrl,newFile)
        return newFile
    except: return imageUrl
    
def double_urlencode(text):
   """double URL-encode a given 'text'.  Do not return the 'variablename=' portion."""

   text = single_urlencode(text)
   text = single_urlencode(text)

   return text

def single_urlencode(text):
   """single URL-encode a given 'text'.  Do not return the 'variablename=' portion."""

   blah = urllib.urlencode({'blahblahblah':text})

   #we know the length of the 'blahblahblah=' is equal to 13.  This lets us avoid any messy string matches
   blah = blah[13:]

   return blah

def getPVRThumbs(title,channel,downloadLocal=False):
    dbID = title + channel
    cacheFound = False
    artwork = {}
    
    logMsg("getPVRThumb for %s %s--> "%(title,channel))
        
    #get the items from cache first
    cache = WINDOW.getProperty("SkinHelper.PVR.Artwork").decode('utf-8')
    if cache:
        cache = eval(cache)
        if cache.has_key(dbID): 
            artwork = cache[dbID]
            cacheFound = True
    else: cache = {}
    
    if not artwork:
        logMsg("getPVRThumb no cache found for dbID--> " + dbID)
        
        #lookup existing artwork in pvrthumbs paths
        paths = []
        paths.append(WINDOW.getProperty("pvrthumbspath").decode("utf-8"))
        if WINDOW.getProperty("customlookuppath"): 
            paths.append( WINDOW.getProperty("customlookuppath").decode("utf-8") )
        for path in paths:
            thumbspath = os.path.join(path,normalize_string(title)) + os.sep
            if xbmcvfs.exists(thumbspath) and not cacheFound:
                logMsg("thumbspath found on disk for " + title)
                #entry exists in pvr thumbs folder on disk
                for artType in PVRartTypes:
                    artpath = os.path.join(thumbspath,artType[1])
                    if xbmcvfs.exists(artpath): 
                        artwork[artType[0]] = artpath
                        cacheFound = True
                        logMsg("%s found on disk for %s" %(artType[0],title))
        
        #also locate thumb in root files of custom directory for non-grouped recordings
        if WINDOW.getProperty("customlookuppath") and not artwork.get("thumb"):
            dirs, files = xbmcvfs.listdir(WINDOW.getProperty("customlookuppath").decode("utf-8"))
            for file in files:
                file = file.decode("utf-8")
                if title in file and ".jpg" in file:
                    artwork["thumb"] = os.path.join(WINDOW.getProperty("customlookuppath").decode("utf-8"),file)
                    break
        
        #lookup local library
        if not artwork and WINDOW.getProperty("useLocalLibraryLookups") == "true":
            item = None
            json_result = getJSON('VideoLibrary.GetTvShows','{ "filter": {"operator":"is", "field":"title", "value":"%s"}, "properties": [ %s ] }' %(title,fields_tvshows))
            if len(json_result) > 0:
                item = json_result[0]
            else:
                json_result = getJSON('VideoLibrary.GetMovies','{ "filter": {"operator":"is", "field":"title", "value":"%s"}, "properties": [ %s ] }' %(title,fields_movies))
                if len(json_result) > 0:
                    item = json_result[0]
            if item and item.has_key("art"): 
                artwork = item["art"]
                cacheFound = True
                logMsg("getPVRThumb artwork found in local library for dbID--> " + dbID)
                
        #if nothing in library or persistant cache, perform the internet scraping
        if not artwork and not WINDOW.getProperty("SkinHelper.DisableInternetLookups"):
            
            #get logo if none found
            if not artwork.has_key("channellogo") and channel:
                artwork["channellogo"] = searchChannelLogo(channel)
            
            #grab artwork from tmdb/fanart.tv
            if WINDOW.getProperty("useTMDBLookups") == "true":
                artwork = getOfficialArtWork(title)
            
            #lookup actual recordings (for grouped recordings and actual icons provided by pvr)
            if not artwork.get("thumb") and WINDOW.getProperty("usePVRAddonthumb") == "true":
                try:
                    json_query = getJSON('PVR.GetRecordings', '{ "properties": [ %s ]}' %( fields_pvrrecordings))
                    for item in json_query:
                        if title in item['title'] or title in item["file"]:
                            if not channel: 
                                channel = item["channel"]
                            artwork["thumb"] = item['icon']
                            logMsg("getPVRThumbs - title matches an existing recording: " + title)
                            break
                except Exception as e:
                    logMsg("ERROR in getPVRThumbs - get thumb from recordings ! --> " + str(e))
                
            #lookup thumb on google as fallback
            if not artwork.get("thumb") and channel and WINDOW.getProperty("useGoogleLookups") == "true":
                artwork["thumb"] = searchGoogleImage(title + " " + channel)
            
            #lookup thumb on youtube as fallback
            if not artwork.get("thumb") and channel and WINDOW.getProperty("useYoutubeLookups") == "true":
                artwork["thumb"] = searchYoutubeImage(title + " " + channel)
            
            if downloadLocal:
                #download images if we want them local
                for artType in PVRartTypes:
                    if artwork.has_key(artType[0]) and artType[0] != "channellogo": artwork[artType[0]] = downloadImage(artwork[artType[0]],title,artType[1])
                
            #store in cache for quick access later
            if not artwork: artwork["cache"] = "None"
            cache[dbID] = artwork
            WINDOW.setProperty("SkinHelper.PVR.ArtWork",repr(cache).encode('utf-8'))
    else:
        logMsg("getPVRThumb cache found for dbID--> " + dbID)
        
    #use kodi texture cache only if item exists in cache and the path is not local
    for artType in PVRartTypes:
        if artwork.has_key(artType[0]) and cacheFound and artwork[artType[0]].startswith("http"): artwork[artType[0]] = "image://" + single_urlencode(artwork[artType[0]]) + "/"

    
    return artwork

def createSmartShortcutSubmenu(windowProp,iconimage):
    try:
        if xbmcvfs.exists("special://skin/shortcuts/"):
            shortcutFile = xbmc.translatePath("special://home/addons/script.skinshortcuts/resources/shortcuts/info-window-home-property-%s-title.DATA.xml" %windowProp.replace(".","-")).decode("utf-8")
            templatefile = os.path.join(ADDON_PATH,"resources","smartshortcuts","smartshortcuts-submenu-template.xml")
            if not xbmcvfs.exists(shortcutFile):
                with open(templatefile, 'r') as f:
                    data = f.read()
                data = data.replace("WINDOWPROP",windowProp)
                data = data.replace("ICONIMAGE",iconimage)
                with open(shortcutFile, 'w') as f:
                    f.write(data)
    except Exception as e:
        logMsg("ERROR in createSmartShortcutSubmenu ! --> " + str(e), 0)

def getCurrentContentType():
    contenttype=""
    if xbmc.getCondVisibility("Container.Content(episodes)"):
        contenttype = "episodes"
    elif xbmc.getCondVisibility("Container.Content(movies) + !substring(Container.FolderPath,setid=)"):
        contenttype = "movies"  
    elif xbmc.getCondVisibility("[Container.Content(sets) | StringCompare(Container.Folderpath,videodb://movies/sets/)] + !substring(Container.FolderPath,setid=)"):
        contenttype = "sets"
    elif xbmc.getCondVisibility("substring(Container.FolderPath,?setid=)"):
        contenttype = "setmovies" 
    elif xbmc.getCondVisibility("Container.Content(tvshows)"):
        contenttype = "tvshows"
    elif xbmc.getCondVisibility("Container.Content(seasons)"):
        contenttype = "seasons"
    elif xbmc.getCondVisibility("Container.Content(musicvideos)"):
        contenttype = "musicvideos"
    elif xbmc.getCondVisibility("Container.Content(songs) | Container.Content(singles) | SubString(Container.ListItem(1).FolderPath,.mp3,right) | SubString(Container.ListItem(1).FolderPath,.flac,right)"):
        contenttype = "songs"
    elif xbmc.getCondVisibility("[Container.Content(artists) | SubString(Container.FolderPath,musicdb://artists)] + !SubString(Container.FolderPath,?)"):
        contenttype = "artists"
    elif xbmc.getCondVisibility("Container.Content(albums) | SubString(Container.FolderPath,musicdb://albums) | SubString(Container.FolderPath,artistid=)"):
        contenttype = "albums"
    elif xbmc.getCondVisibility("Window.IsActive(tvchannels) | Window.IsActive(radiochannels)"):
        contenttype = "tvchannels"
    elif xbmc.getCondVisibility("Window.IsActive(tvrecordings) | Window.IsActive(radiorecordings)"):
        contenttype = "tvrecordings"
    elif xbmc.getCondVisibility("Window.IsActive(tvguide) | Window.IsActive(radioguide)"):
        contenttype = "tvguide"
    elif xbmc.getCondVisibility("Window.IsActive(tvtimers) | Window.IsActive(radiotimers)"):
        contenttype = "tvtimers"
    elif xbmc.getCondVisibility("Window.IsActive(tvsearch) | Window.IsActive(radiosearch)"):
        contenttype = "tvsearch"
    elif xbmc.getCondVisibility("Window.IsActive(programs) | Window.IsActive(addonbrowser)"):
        contenttype = "programs"
    elif xbmc.getCondVisibility("Window.IsActive(pictures)"):
        contenttype = "pictures"
    elif xbmc.getCondVisibility("Container.Content(files)"):
        contenttype = "files"
    WINDOW.setProperty("contenttype",contenttype)
    return contenttype
        
def searchChannelLogo(searchphrase):
    #get's a thumb image for the given search phrase
    image = ""
    
    cache = WINDOW.getProperty(searchphrase.encode('utf-8') + "SkinHelper.PVR.ChannelLogo")
    if cache: return cache
    else:
    
        try:
            #lookup in channel list
            # Perform a JSON query to get all channels
            json_query = getJSON('PVR.GetChannels', '{"channelgroupid": "alltv", "properties": [ "thumbnail", "channeltype", "hidden", "locked", "channel", "lastplayed", "broadcastnow" ]}' )
            for item in json_query:
                channelname = item["label"]
                channelicon = item['thumbnail']
                if channelname == searchphrase:
                    image = getCleanImage(channelicon)
                    break

            #lookup with thelogodb
            if not image:
                url = 'http://www.thelogodb.com/api/json/v1/1/tvchannel.php?s=%s' %try_encode(searchphrase)
                response = requests.get(url)
                data = json.loads(response.content.decode('utf-8','replace'))
                if data and data.has_key('channels'):
                    results = data['channels']
                    if results:
                        for i in results: 
                            rest = i['strLogoWide']
                            if rest:
                                if ".jpg" in rest or ".png" in rest:
                                    image = rest
                                    break
                
            if not image:
                search_alt = searchphrase.replace(" HD","")
                url = 'http://www.thelogodb.com/api/json/v1/1/tvchannel.php?s=%s' %try_encode(search_alt)
                response = requests.get(url)
                data = json.loads(response.content.decode('utf-8','replace'))
                if data and data.has_key('channels'):
                    results = data['channels']
                    if results:
                        for i in results: 
                            rest = i['strLogoWide']
                            if rest:
                                if ".jpg" in rest or ".png" in rest:
                                    image = rest
                                    break
        except Exception as e:
            if "getaddrinfo failed" in str(e):
                #no internet access - disable lookups for now
                WINDOW.setProperty("SkinHelper.DisableInternetLookups","disable")
                logMsg("searchChannelLogo - no internet access, disabling internet lookups for now")
            else:
                logMsg("ERROR in searchChannelLogo ! --> " + str(e), 0)

        if image:
            if ".jpg/" in image:
                image = image.split(".jpg/")[0] + ".jpg"
        
        WINDOW.setProperty(searchphrase.encode('utf-8') + "SkinHelper.PVR.ChannelLogo",image)
        return image

def searchGoogleImage(searchphrase):
    image = ""
   
    try:
        ip_address = xbmc.getInfoLabel("Network.IPAddress")
        url = 'http://ajax.googleapis.com/ajax/services/search/images'
        params = {'v' : '1.0', 'safe': 'off', 'userip': ip_address, 'q': searchphrase, 'imgsz': 'medium|large|xlarge'}
        response = requests.get(url, params=params)
        data = json.loads(response.content.decode('utf-8','replace'))
        if data and data.get("responseData"):
            if data['responseData'].get("results"):
                results = data['responseData']['results']
                for i in results: 
                    image = i['unescapedUrl']
                    if image:
                        if ".jpg" in image or ".png" in image:
                            logMsg("getTMDBimage - GOOGLE match found for %s !" %searchphrase)
                            return image
    except Exception as e:
        if "getaddrinfo failed" in str(e):
            #no internet access - disable lookups for now
            WINDOW.setProperty("SkinHelper.DisableInternetLookups","disable")
            logMsg("searchGoogleImage - no internet access, disabling internet lookups for now")
        else:
            logMsg("getTMDBimage - ERROR in searchGoogleImage ! --> " + str(e))
    
    logMsg("getTMDBimage - GOOGLE match NOT found for %s" %searchphrase)
    return image
 
def searchYoutubeImage(searchphrase):
    image = ""
    matchFound = False
    #safety check: prevent multiple youtube searches at once...
    waitForYouTubeCount = 0
    if WINDOW.getProperty("youtubescanrunning") == "running":
        xbmc.sleep(100)
        return "skip"
    
    WINDOW.setProperty("youtubescanrunning","running")
    libPath = "plugin://plugin.video.youtube/kodion/search/query/?q=%s" %searchphrase
    media_array = getJSON('Files.GetDirectory','{ "properties": ["title","art"], "directory": "' + libPath + '", "media": "files" }')
    for media in media_array:
        if not media["filetype"] == "directory":
            if media.has_key('art'):
                if media['art'].has_key('thumb'):
                    image = getCleanImage(media['art']['thumb'])
                    matchFound = True
                    break
    if matchFound:
        logMsg("searchYoutubeImage - YOUTUBE match found for %s" %searchphrase)
    else:
        logMsg("searchYoutubeImage - YOUTUBE match NOT found for %s" %searchphrase)
    
    WINDOW.clearProperty("youtubescanrunning")
    return image
 
def searchThumb(searchphrase, searchphrase2=""):
    #get's a thumb image for the given search phrase
    
    #is this item already in the cache?
    image = WINDOW.getProperty(searchphrase + searchphrase2 + "SkinHelper.PVR.Thumb")
    if not image and not WINDOW.getProperty("SkinHelper.DisableInternetLookups"):
        if searchphrase2:
            searchphrase = searchphrase + " " + searchphrase2
            
        WINDOW.setProperty("getthumbbusy","busy")
                  
        #lookup with Google images
        if not image:
            image = searchGoogleImage(searchphrase)
        
        # Do lookup with youtube addon as last resort
        if not image:
            searchYoutubeImage(searchphrase)
                
        if image:
            if ".jpg/" in image:
                image = image.split(".jpg/")[0] + ".jpg"
        WINDOW.clearProperty("getthumbbusy")
    return image
    
def getCleanImage(image):
    if image and "image://" in image:
        image = image.replace("image://","")
        image=urllib.unquote(image.encode("utf-8"))
        if image.endswith("/"):
            image = image[:-1]
    return image

def normalize_string(text):
    text = text.replace(":", "")
    text = text.replace("/", "-")
    text = text.replace("\\", "-")
    text = text.replace("<", "")
    text = text.replace(">", "")
    text = text.replace("*", "")
    text = text.replace("?", "")
    text = text.replace('|', "")
    text = text.replace('(', "")
    text = text.replace(')', "")
    text = text.strip()
    text = text.rstrip('.')
    text = unicodedata.normalize('NFKD', try_decode(text))
    return text
    
def getMusicArtByDbId(dbid,itemtype):
    cdArt = None
    LogoArt = None
    BannerArt = None
    extraFanArt = None
    Info = None
    path = None
    TrackList = ""
    if itemtype == "songs":
        json_response = getJSON('AudioLibrary.GetSongDetails', '{ "songid": %s, "properties": [ "file","artistid","albumid","comment"] }'%int(dbid))  
    elif itemtype == "artists":
        json_response = getJSON('AudioLibrary.GetSongs', '{ "filter":{"artistid": %s}, "properties": [ "file","artistid","track","title","albumid" ] }'%int(dbid))
    elif itemtype == "albums":
        json_response = getJSON('AudioLibrary.GetSongs', '{ "filter":{"albumid": %s}, "properties": [ "file","artistid","track","title","albumid" ] }'%int(dbid))
    
    if json_response:
        song = {}
        if type(json_response) is list:
            #get track listing
            for item in json_response:
                if not song:
                    song = item
                    path = item["file"]
                if item["track"]:
                    TrackList += "%s - %s[CR]" %(str(item["track"]), item["title"])
                else:
                    TrackList += "%s[CR]" %(item["title"])      
        else:
            song = json_response
        path = song["file"]
        if not Info:
            json_response2 = getJSON('AudioLibrary.GetAlbumDetails','{ "albumid": %s, "properties": [ "musicbrainzalbumid","description" ] }'%song["albumid"])
            if json_response2.get("description",None):
                Info = json_response2["description"]
        if not Info and song:
            if song.has_key("artistid"):
                json_response2 = getJSON('AudioLibrary.GetArtistDetails', '{ "artistid": %s, "properties": [ "musicbrainzartistid","description" ] }'%song["artistid"][0])
                if json_response2.get("description",None):
                    Info = json_response2["description"]

    if path:
        if "\\" in path:
            delim = "\\"
        else:
            delim = "/"
                
        path = path.replace(path.split(delim)[-1],"")
                              
        #extrafanart
        imgPath = os.path.join(path,"extrafanart" + delim)
        if xbmcvfs.exists(imgPath):
            extraFanArt = imgPath
        else:
            imgPath = os.path.join(path.replace(path.split(delim)[-2]+delim,""),"extrafanart" + delim)
            if xbmcvfs.exists(imgPath):
                extraFanArt = imgPath
        
        #cdart
        if xbmcvfs.exists(os.path.join(path,"cdart.png")):
            cdArt = os.path.join(path,"cdart.png")
        else:
            imgPath = os.path.join(path.replace(path.split(delim)[-2]+delim,""),"cdart.png")
            if xbmcvfs.exists(imgPath):
                cdArt = imgPath
        
        #banner
        if xbmcvfs.exists(os.path.join(path,"banner.jpg")):
            BannerArt = os.path.join(path,"banner.jpg")
        else:
            imgPath = os.path.join(path.replace(path.split(delim)[-2]+delim,""),"banner.jpg")
            if xbmcvfs.exists(imgPath):
                BannerArt = imgPath
                
        #logo
        imgPath = os.path.join(path,"logo.png")
        if xbmcvfs.exists(imgPath):
            LogoArt = imgPath
        else:
            imgPath = os.path.join(path.replace(path.split(delim)[-2]+delim,""),"logo.png")
            if xbmcvfs.exists(imgPath):
                LogoArt = imgPath
                
    return (cdArt, LogoArt, BannerArt, extraFanArt, Info, TrackList)