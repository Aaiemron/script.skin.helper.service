#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys, traceback
import xbmc
import xbmcplugin
import xbmcaddon
import xbmcgui
import threading
import xbmcvfs
import random
import xml.etree.ElementTree as etree
import base64
import json
from datetime import datetime
from Utils import *

class LibraryMonitor(threading.Thread):
    
    event = None
    exit = False
    liPath = None
    liPathLast = None
    unwatched = 1
    lastEpPath = ""
    lastMusicDbId = None
    lastpvrDbId = None
    allStudioLogos = {}
    allStudioLogosColor = {}
    LastCustomStudioImagesPath = None
    delayedTaskInterval = 1800
    moviesetCache = {}
    extraFanartcache = {}
    musicArtCache = {}
    pvrArtCache = {}
    
    def __init__(self, *args):
        
        logMsg("LibraryMonitor - started")
        self.cachePath = os.path.join(ADDON_DATA_PATH,"librarycache.json")
        self.event =  threading.Event()
        threading.Thread.__init__(self, *args)    
    
    def stop(self):
        logMsg("LibraryMonitor - stop called",0)
        self.saveCacheToFile()
        self.exit = True
        self.event.set()

    def saveCacheToFile(self):
        #safety check: does the config directory exist?
        if not xbmcvfs.exists(ADDON_DATA_PATH + os.sep):
            xbmcvfs.mkdir(ADDON_DATA_PATH)
        
        libraryCache = {}
        libraryCache["moviesetCache"] = self.moviesetCache
        libraryCache["extraFanartcache"] = self.extraFanartcache
        libraryCache["musicArtCache"] = self.musicArtCache
        libraryCache["pvrArtCache"] = self.pvrArtCache
        #cache file for all backgrounds
        json.dump(libraryCache, open(self.cachePath,'w'))
    
    def getCacheFromFile(self):
        #TODO --> clear the cache in some conditions
        if xbmcvfs.exists(self.cachePath):
            with open(self.cachePath) as data_file:    
                data = json.load(data_file)
                self.moviesetCache = data["moviesetCache"]
                self.extraFanartcache = data["extraFanartcache"]
                self.musicArtCache = data["musicArtCache"]
                self.pvrArtCache = data["pvrArtCache"]
    
    def run(self):

        lastListItemLabel = None
        KodiMonitor = xbmc.Monitor()
        self.getCacheFromFile()

        while (self.exit != True):
            
            #do some background stuff every 30 minutes
            if (xbmc.getCondVisibility("!Window.IsActive(videolibrary) + !Window.IsActive(musiclibrary) + !Window.IsActive(fullscreenvideo)")):
                if (self.delayedTaskInterval >= 1800):
                    self.getStudioLogos()
                    self.delayedTaskInterval = 0                   
            
            #flush cache if videolibrary has changed
            if WINDOW.getProperty("widgetrefresh") == "refresh":
                self.moviesetCache = {}
            
            # monitor listitem props when musiclibrary is active
            elif (xbmc.getCondVisibility("[Window.IsActive(musiclibrary) | Window.IsActive(MyMusicSongs.xml)] + !Container.Scrolling")):
                if WINDOW.getProperty("resetMusicArtCache") == "reset":
                    self.lastMusicDbId = None
                    self.musicArtCache = {}
                    WINDOW.clearProperty("resetMusicArtCache")
                try:
                    self.checkMusicArt()
                except Exception as e:
                    logMsg("ERROR in checkMusicArt ! --> " + str(e), 0)
                    traceback.print_exc()
            
            # monitor listitem props when PVR is active
            elif (xbmc.getCondVisibility("SubString(Window.Property(xmlfile),MyPVR,left)")):
                
                self.liPath = xbmc.getInfoLabel("ListItem.Path")
                liLabel = xbmc.getInfoLabel("ListItem.Label")
                if ((liLabel != lastListItemLabel) and xbmc.getCondVisibility("!Container.Scrolling")):
                    
                    self.liPathLast = self.liPath
                    lastListItemLabel = liLabel
                    
                    # update the listitem stuff
                    try:
                        self.setDuration()
                        self.setPVRThumbs()
                        self.setGenre()
                    except Exception as e:
                        logMsg("ERROR in LibraryMonitor ! --> " + str(e), 0)
                        traceback.print_exc()

            
            #monitor home widget
            elif xbmc.getCondVisibility("Window.IsActive(home)") and WINDOW.getProperty("SkinHelper.WidgetContainer"):
                widgetContainer = WINDOW.getProperty("SkinHelper.WidgetContainer")
                self.liPath = xbmc.getInfoLabel("Container(%s).ListItem.Path" %widgetContainer)
                liLabel = xbmc.getInfoLabel("Container(%s).ListItem.Label"%widgetContainer)
                if ((liLabel != lastListItemLabel) and xbmc.getCondVisibility("!Container(%s).Scrolling" %widgetContainer)):
                    self.liPathLast = self.liPath
                    lastListItemLabel = liLabel
                    try:
                        self.setDuration(xbmc.getInfoLabel("Container(%s).ListItem.Duration" %widgetContainer))
                        self.setStudioLogo(xbmc.getInfoLabel("Container(%s).ListItem.Studio" %widgetContainer))
                    except Exception as e:
                        logMsg("ERROR in LibraryMonitor widgets ! --> " + str(e), 0)
                        traceback.print_exc()
            
            # monitor listitem props when videolibrary is active
            elif (xbmc.getCondVisibility("[Window.IsActive(videolibrary) | Window.IsActive(movieinformation)] + !Window.IsActive(fullscreenvideo)")):
                
                self.liPath = xbmc.getInfoLabel("ListItem.Path")
                liLabel = xbmc.getInfoLabel("ListItem.Label")
                if ((liLabel != lastListItemLabel) and xbmc.getCondVisibility("!Container.Scrolling")):
                    
                    self.liPathLast = self.liPath
                    lastListItemLabel = liLabel
                    
                    # update the listitem stuff
                    try:
                        self.setDuration()
                        self.setStudioLogo()
                        self.setGenre()
                        self.focusEpisode()
                        self.checkExtraFanArt()
                        self.setMovieSetDetails()
                        self.setAddonName()
                    except Exception as e:
                        logMsg("ERROR in LibraryMonitor ! --> " + str(e), 0)
                        traceback.print_exc()
  
            else:
                #reset window props
                WINDOW.clearProperty("SkinHelper.ListItemStudioLogo")
                WINDOW.clearProperty('SkinHelper.ListItemDuration')
                WINDOW.setProperty("SkinHelper.ExtraFanArtPath","") 
                WINDOW.clearProperty("SkinHelper.Music.BannerArt") 
                WINDOW.clearProperty("SkinHelper.Music.LogoArt") 
                WINDOW.clearProperty("SkinHelper.Music.DiscArt")
                WINDOW.clearProperty("SkinHelper.Music.Info")
                
            xbmc.sleep(150)
            self.delayedTaskInterval += 0.15
                    
    def setMovieSetDetails(self):
        #get movie set details -- thanks to phil65 - used this idea from his skin info script
        
        WINDOW.clearProperty('SkinHelper.MovieSet.Title')
        WINDOW.clearProperty('SkinHelper.MovieSet.Runtime')
        WINDOW.clearProperty('SkinHelper.MovieSet.Duration')
        WINDOW.clearProperty('SkinHelper.MovieSet.Duration.Hours')
        WINDOW.clearProperty('SkinHelper.MovieSet.Duration.Minutes')
        WINDOW.clearProperty('SkinHelper.MovieSet.Writer')
        WINDOW.clearProperty('SkinHelper.MovieSet.Director')
        WINDOW.clearProperty('SkinHelper.MovieSet.Genre')
        WINDOW.clearProperty('SkinHelper.MovieSet.Country')
        WINDOW.clearProperty('SkinHelper.MovieSet.Studio')
        WINDOW.clearProperty('SkinHelper.MovieSet.Years')
        WINDOW.clearProperty('SkinHelper.MovieSet.Year')
        WINDOW.clearProperty('SkinHelper.MovieSet.Count')
        WINDOW.clearProperty('SkinHelper.MovieSet.Plot')
        totalNodes = 50
        for i in range(totalNodes):
            if not WINDOW.getProperty('SkinHelper.MovieSet.' + str(i) + '.Title'):
                break
            WINDOW.clearProperty('SkinHelper.MovieSet.' + str(i) + '.Title')
            WINDOW.clearProperty('SkinHelper.MovieSet.' + str(i) + '.FanArt')
            WINDOW.clearProperty('SkinHelper.MovieSet.' + str(i) + '.Landscape')
            WINDOW.clearProperty('SkinHelper.MovieSet.' + str(i) + '.DiscArt')
            WINDOW.clearProperty('SkinHelper.MovieSet.' + str(i) + '.ClearLogo')
            WINDOW.clearProperty('SkinHelper.MovieSet.' + str(i) + '.ClearArt')
            WINDOW.clearProperty('SkinHelper.MovieSet.' + str(i) + '.Banner')
            WINDOW.clearProperty('SkinHelper.MovieSet.' + str(i) + '.Rating')
            WINDOW.clearProperty('SkinHelper.MovieSet.' + str(i) + '.Resolution')
            WINDOW.clearProperty('SkinHelper.MovieSet.' + str(i) + '.AspectRatio')
            WINDOW.clearProperty('SkinHelper.MovieSet.' + str(i) + '.Codec')
        
            
        if xbmc.getCondVisibility("SubString(ListItem.Path,videodb://movies/sets/,left)"):
            
            dbId = xbmc.getInfoLabel("ListItem.DBID")
                    
            if dbId:
                
                #try to get from cache first
                if self.moviesetCache.has_key(dbId):
                    json_response = self.moviesetCache[dbId]
                else:
                    json_response = getJSON('VideoLibrary.GetMovieSetDetails', '{"setid": %s, "properties": [ "thumbnail" ], "movies": { "properties":  [ "rating", "art", "file", "year", "director", "writer", "playcount", "genre" , "thumbnail", "runtime", "studio", "plotoutline", "plot", "country", "streamdetails"], "sort": { "order": "ascending",  "method": "year" }} }' % dbId)
                
                #save to cache
                self.moviesetCache[dbId] = json_response
                if "setdetails" in json_response:
                    
                    count = 0
                    unwatchedcount = 0
                    watchedcount = 0
                    runtime = 0
                    runtime_mins = 0
                    writer = []
                    director = []
                    genre = []
                    country = []
                    studio = []
                    years = []
                    plot = ""
                    title_list = ""
                    title_header = "[B]" + str(json_response['setdetails']['limits']['total']) + " " + xbmc.getLocalizedString(20342) + "[/B][CR]"
                    set_fanart = []
                    for item in json_response['setdetails']['movies']:
                        
                        if item["playcount"] == 0:
                            unwatchedcount += 1
                        else:
                            watchedcount += 1
                        
                        art = item['art']
                        set_fanart.append(art.get('fanart', ''))
                        WINDOW.setProperty('SkinHelper.MovieSet.' + str(count) + '.Title',item['label'])
                        WINDOW.setProperty('SkinHelper.MovieSet.' + str(count) + '.Poster',art.get('poster', ''))
                        WINDOW.setProperty('SkinHelper.MovieSet.' + str(count) + '.FanArt',art.get('fanart', ''))
                        WINDOW.setProperty('SkinHelper.MovieSet.' + str(count) + '.Landscape',art.get('landscape', ''))
                        WINDOW.setProperty('SkinHelper.MovieSet.' + str(count) + '.DiscArt',art.get('discart', ''))
                        WINDOW.setProperty('SkinHelper.MovieSet.' + str(count) + '.ClearLogo',art.get('clearlogo', ''))
                        WINDOW.setProperty('SkinHelper.MovieSet.' + str(count) + '.ClearArt',art.get('clearart', ''))
                        WINDOW.setProperty('SkinHelper.MovieSet.' + str(count) + '.Banner',art.get('banner', ''))
                        WINDOW.setProperty('SkinHelper.MovieSet.' + str(count) + '.Rating',str(item.get('rating', '')))
                        if "streamdetails" in item:
                            for key, value in item['streamdetails'].iteritems():
                                for stream in value:
                                    if stream.get("height",""):
                                        WINDOW.setProperty('SkinHelper.MovieSet.' + str(count) + '.Resolution',str(stream["height"]))
                                    if stream.get("codec",""):
                                        WINDOW.setProperty('SkinHelper.MovieSet.' + str(count) + '.Codec',str(stream["codec"]))    
                                    if stream.get("aspect",""):
                                        WINDOW.setProperty('SkinHelper.MovieSet.' + str(count) + '.AspectRatio',str(round(stream["aspect"], 2)))

                        title_list += item['label'] + " (" + str(item['year']) + ")[CR]"
                        if item['plotoutline']:
                            plot += "[B]" + item['label'] + " (" + str(item['year']) + ")[/B][CR]" + item['plotoutline'] + "[CR][CR]"
                        else:
                            plot += "[B]" + item['label'] + " (" + str(item['year']) + ")[/B][CR]" + item['plot'] + "[CR][CR]"
                        runtime += item['runtime']
                        count += 1
                        if item.get("writer"):
                            writer += [w for w in item["writer"] if w and w not in writer]
                        if item.get("director"):
                            director += [d for d in item["director"] if d and d not in director]
                        if item.get("genre"):
                            genre += [g for g in item["genre"] if g and g not in genre]
                        if item.get("country"):
                            country += [c for c in item["country"] if c and c not in country]
                        if item.get("studio"):
                            studio += [s for s in item["studio"] if s and s not in studio]
                        years.append(str(item['year']))
                    WINDOW.setProperty('SkinHelper.MovieSet.Plot', plot)
                    if json_response['setdetails']['limits']['total'] > 1:
                        WINDOW.setProperty('SkinHelper.MovieSet.ExtendedPlot', title_header + title_list + "[CR]" + plot)
                    else:
                        WINDOW.setProperty('SkinHelper.MovieSet.ExtendedPlot', plot)
                    WINDOW.setProperty('SkinHelper.MovieSet.Title', title_list)
                    WINDOW.setProperty('SkinHelper.MovieSet.Runtime', str(runtime / 60))
                    self.setDuration(str(runtime / 60))
                    durationString = self.getDurationString(runtime / 60)
                    if durationString:
                        WINDOW.setProperty('SkinHelper.MovieSet.Duration', durationString[2])
                        WINDOW.setProperty('SkinHelper.MovieSet.Duration.Hours', durationString[0])
                        WINDOW.setProperty('SkinHelper.MovieSet.Duration.Minutes', durationString[1])
                    WINDOW.setProperty('SkinHelper.MovieSet.Writer', " / ".join(writer))
                    WINDOW.setProperty('SkinHelper.MovieSet.Director', " / ".join(director))
                    WINDOW.setProperty('SkinHelper.MovieSet.Genre', " / ".join(genre))
                    self.setGenre(" / ".join(genre))
                    WINDOW.setProperty('SkinHelper.MovieSet.Country', " / ".join(country))
                    studioString = " / ".join(studio)
                    WINDOW.setProperty('SkinHelper.MovieSet.Studio', studioString)
                    self.setStudioLogo(studioString)
                   
                    WINDOW.setProperty('SkinHelper.MovieSet.Years', " / ".join(years))
                    WINDOW.setProperty('SkinHelper.MovieSet.Year', years[0] + " - " + years[-1])
                    WINDOW.setProperty('SkinHelper.MovieSet.Count', str(json_response['setdetails']['limits']['total']))
                    WINDOW.setProperty('SkinHelper.MovieSet.WatchedCount', str(watchedcount))
                    WINDOW.setProperty('SkinHelper.MovieSet.UnWatchedCount', str(unwatchedcount))
                    
                    #rotate fanart from movies in set while listitem is in focus
                    if xbmc.getCondVisibility("Skin.HasSetting(SkinHelper.EnableExtraFanart)"):
                        fanartcount = 5
                        delaycount = 5
                        backgroundDelayStr = xbmc.getInfoLabel("skin.string(extrafanartdelay)")
                        if backgroundDelayStr:
                            fanartcount = int(backgroundDelayStr)
                            delaycount = int(backgroundDelayStr)
                        while dbId == xbmc.getInfoLabel("ListItem.DBID") and set_fanart != []:
                            
                            if fanartcount == delaycount:
                                random.shuffle(set_fanart)
                                WINDOW.setProperty('SkinHelper.ExtraFanArtPath', set_fanart[0])
                                fanartcount = 0
                            else:
                                xbmc.sleep(1000)
                                fanartcount += 1

    def setAddonName(self):
        # set addon name as property
        if not xbmc.Player().isPlayingAudio():
            if (xbmc.getCondVisibility("Container.Content(plugins) | !IsEmpty(Container.PluginName)")):
                AddonName = xbmc.getInfoLabel('Container.PluginName')
                AddonName = xbmcaddon.Addon(AddonName).getAddonInfo('name')
                WINDOW.setProperty("SkinHelper.Player.AddonName", AddonName)
            else:
                WINDOW.clearProperty("SkinHelper.Player.AddonName")
    
    def setGenre(self, genre=None):
        if not genre:
            genre = xbmc.getInfoLabel('ListItem.Genre')
        
        genres = []
        if "/" in genre:
            genres = genre.split(" / ")
        else:
            genres.append(genre)
        
        WINDOW.setProperty('SkinHelper.ListItemGenres', "[CR]".join(genres))
        
    def setPVRThumbs(self):
        title = xbmc.getInfoLabel("ListItem.Title")
        channel = xbmc.getInfoLabel("ListItem.ChannelName")
        dbID = title + channel
        cacheFound = False

        if self.lastMusicDbId == dbID:
            return
            
        logMsg("setPVRThumb dbID--> " + dbID)
        
        WINDOW.clearProperty("SkinHelper.PVR.Thumb") 
        WINDOW.clearProperty("SkinHelper.PVR.FanArt") 
        WINDOW.clearProperty("SkinHelper.PVR.ChannelLogo")
        WINDOW.clearProperty("SkinHelper.PVR.Poster")
        
        if xbmc.getInfoLabel("ListItem.Label") == "..":
            return
            
        #get the items from cache first
        if self.pvrArtCache.has_key(dbID + "SkinHelper.PVR.Thumb"):
            cacheFound = True
            if self.pvrArtCache[dbID + "SkinHelper.PVR.Thumb"] == "None":
                WINDOW.clearProperty("SkinHelper.PVR.Thumb")   
            else:
                WINDOW.setProperty("SkinHelper.PVR.Thumb",self.pvrArtCache[dbID + "SkinHelper.PVR.Thumb"])

        if self.pvrArtCache.has_key(dbID + "SkinHelper.PVR.FanArt"):
            cacheFound = True
            if self.pvrArtCache[dbID + "SkinHelper.PVR.FanArt"] == "None":
                WINDOW.clearProperty("SkinHelper.PVR.FanArt")   
            else:
                WINDOW.setProperty("SkinHelper.PVR.FanArt",self.pvrArtCache[dbID + "SkinHelper.PVR.FanArt"])
        
        if self.pvrArtCache.has_key(dbID + "SkinHelper.PVR.Poster"):
            cacheFound = True
            if self.pvrArtCache[dbID + "SkinHelper.PVR.Poster"] == "None":
                WINDOW.clearProperty("SkinHelper.PVR.Poster")   
            else:
                WINDOW.setProperty("SkinHelper.PVR.Poster",self.pvrArtCache[dbID + "SkinHelper.PVR.Poster"])
        
        if self.pvrArtCache.has_key(dbID + "SkinHelper.PVR.ChannelLogo"):
            cacheFound = True
            if self.pvrArtCache[dbID + "SkinHelper.PVR.ChannelLogo"] == "None":
                WINDOW.clearProperty("SkinHelper.PVR.ChannelLogo")   
            else:
                WINDOW.setProperty("SkinHelper.PVR.ChannelLogo",self.pvrArtCache[dbID + "SkinHelper.PVR.ChannelLogo"])
        
        if not cacheFound:
            logMsg("setPVRThumb no cache found for dbID--> " + dbID)
            thumb = None
            fanart = None
            logo = None
            poster = None
            
            poster, fanart = getTMDBimage(title)
            thumb = searchGoogleImage(title + " " + channel)
            if channel == xbmc.getInfoLabel("$INFO[ListItem.Label]"):
                logo = xbmc.getInfoLabel("$INFO[ListItem.Icon]")
            
            #get logo from studio logos
            if not logo:
                logo = self.setStudioLogo(channel)
            if not logo:
                #fallback to channelDB
                logo = searchChannelLogo(channel)
            
            if thumb:
                WINDOW.setProperty("SkinHelper.PVR.Thumb",thumb)
                self.pvrArtCache[dbID + "SkinHelper.PVR.Thumb"] = thumb
            else:
                WINDOW.setProperty("SkinHelper.PVR.Thumb","")
                self.pvrArtCache[dbID + "SkinHelper.PVR.Thumb"] = "None"
            
            if fanart:
                WINDOW.setProperty("SkinHelper.PVR.FanArt",fanart)
                self.pvrArtCache[dbID + "SkinHelper.PVR.FanArt"] = fanart
            else:
                WINDOW.setProperty("SkinHelper.PVR.FanArt","")
                self.pvrArtCache[dbID + "SkinHelper.PVR.FanArt"] = "None"
            if poster:
                WINDOW.setProperty("SkinHelper.PVR.Poster",poster)
                self.pvrArtCache[dbID + "SkinHelper.PVR.Poster"] = poster
            else:
                WINDOW.setProperty("SkinHelper.PVR.Poster","")
                self.pvrArtCache[dbID + "SkinHelper.PVR.Poster"] = "None"
            if logo:
                WINDOW.setProperty("SkinHelper.PVR.ChannelLogo",logo)
                self.pvrArtCache[dbID + "SkinHelper.PVR.ChannelLogo"] = logo
            else:
                WINDOW.setProperty("SkinHelper.PVR.ChannelLogo","")
                self.pvrArtCache[dbID + "SkinHelper.PVR.ChannelLogo"] = "None"
            
    def setStudioLogo(self, studio=None):
        if not studio:
            studio = xbmc.getInfoLabel('ListItem.Studio')
        studiologo = None
        studiologoColor = None
        
        studios = []
        if "/" in studio:
            studios = studio.split(" / ")
            WINDOW.setProperty("SkinHelper.ListItemStudio", studios[0])
        else:
            studios.append(studio)
            WINDOW.setProperty("SkinHelper.ListItemStudio", studio)
        
        for studio in studios:
            studio = studio.lower()
            #find logo normal
            if self.allStudioLogos.has_key(studio):
                studiologo = self.allStudioLogos[studio]
            if self.allStudioLogosColor.has_key(studio):
                studiologoColor = self.allStudioLogosColor[studio]    
            
            if not studiologo and not studiologoColor:
                #find logo by substituting characters
                if " (" in studio:
                    studio = studio.split(" (")[-1]
                    if self.allStudioLogos.has_key(studio):
                        studiologo = self.allStudioLogos[studio]
                    if self.allStudioLogosColor.has_key(studio):
                        studiologoColor = self.allStudioLogosColor[studio]
            
            if not studiologo and not studiologoColor:
                #find logo by substituting characters for pvr channels
                if " HD" in studio:
                    studio = studio.replace(" HD","")
                elif " " in studio:
                    studio = studio.replace(" ","")
                if self.allStudioLogos.has_key(studio):
                    studiologo = self.allStudioLogos[studio]
                if self.allStudioLogosColor.has_key(studio):
                    studiologoColor = self.allStudioLogosColor[studio]  
        
        if studiologo:
            WINDOW.setProperty("SkinHelper.ListItemStudioLogo", studiologo)
        else:
            WINDOW.clearProperty("SkinHelper.ListItemStudioLogo")
        
        if studiologoColor:
            WINDOW.setProperty("SkinHelper.ListItemStudioLogoColor", studiologo)
        else:
            WINDOW.clearProperty("SkinHelper.ListItemStudioLogoColor")
        
        #set formatted studio logo
        WINDOW.setProperty('SkinHelper.ListItemStudios', "[CR]".join(studios))
        return studiologo
                
    def getStudioLogos(self):
        #fill list with all studio logos
        allLogos = {}
        allLogosColor = {}
        allPaths = []
        allPathsColor = []

        CustomStudioImagesPath = xbmc.getInfoLabel("Skin.String(SkinHelper.CustomStudioImagesPath)")
        if CustomStudioImagesPath + xbmc.getSkinDir() != self.LastCustomStudioImagesPath:
            #only proceed if the custom path or skin has changed...
            self.LastCustomStudioImagesPath = CustomStudioImagesPath + xbmc.getSkinDir()
            
            #add the custom path to the list
            if CustomStudioImagesPath:
                path = CustomStudioImagesPath
                if not (CustomStudioImagesPath.endswith("/") or CustomStudioImagesPath.endswith("\\")):
                    CustomStudioImagesPath = CustomStudioImagesPath + os.sep()
                    allPaths.append(CustomStudioImagesPath)
            
            #add skin provided paths
            allPaths.append("special://skin/extras/flags/studios/")
            allPathsColor.append("special://skin/extras/flags/studioscolor/")
            
            #add images provided by the image resource addons
            allPaths.append("resource://resource.images.studios.white/")
            allPathsColor.append("resource://resource.images.studios.coloured/")
            allPaths.append("special://home/addons/resource.images.studios.white/")
            allPathsColor.append("special://home/addons/resource.images.studios.coloured/")
            
            #check all white logos
            for path in allPaths:               
                if xbmcvfs.exists(path):
                    dirs, files = xbmcvfs.listdir(path)
                    for file in files:
                        name = file.split(".")[0].lower()
                        if not allLogos.has_key(name):
                            allLogos[name] = path + file
                    for dir in dirs:
                        dirs2, files2 = xbmcvfs.listdir(os.path.join(path,dir))
                        for file in files2:
                            name = dir + "/" + file.split(".")[0].lower()
                            if not allLogos.has_key(name):
                                if "/" in path:
                                    sep = "/"
                                else:
                                    sep = "\\"
                                allLogos[name] = path + dir + sep + file
                    
            #check all color logos
            for path in allPathsColor:
                if xbmcvfs.exists(path):
                    dirs, files = xbmcvfs.listdir(path)
                    for file in files:
                        name = file.split(".")[0].lower()
                        if not allLogos.has_key(name):
                            allLogos[name] = path + file
                    for dir in dirs:
                        dirs2, files2 = xbmcvfs.listdir(os.path.join(path,dir))
                        for file in files2:
                            name = dir + "/" + file.split(".")[0].lower()
                            if not allLogos.has_key(name):
                                if "/" in path:
                                    sep = "/"
                                else:
                                    sep = "\\"
                                allLogos[name] = path + dir + sep + file
            
            #assign all found logos in the list
            self.allStudioLogos = allLogos
            self.allStudioLogosColor = allLogosColor
    
    def focusEpisode(self):
        # monitor episodes for auto focus first unwatched
        if xbmc.getCondVisibility("Skin.HasSetting(AutoFocusUnwatchedEpisode)"):
            
            #store unwatched episodes
            if ((xbmc.getCondVisibility("Container.Content(seasons) | Container.Content(tvshows)")) and xbmc.getCondVisibility("!IsEmpty(ListItem.Property(UnWatchedEpisodes))")):
                try:
                    self.unwatched = int(xbmc.getInfoLabel("ListItem.Property(UnWatchedEpisodes)"))
                except: pass
            
            if (xbmc.getCondVisibility("Container.Content(episodes) | Container.Content(seasons)")):
                
                if (xbmc.getInfoLabel("Container.FolderPath") != self.lastEpPath and self.unwatched != 0):
                    totalItems = 0
                    curView = xbmc.getInfoLabel("Container.Viewmode") 
                    viewId = int(self.getViewId(curView))
                    
                    wid = xbmcgui.getCurrentWindowId()
                    window = xbmcgui.Window( wid )        
                    control = window.getControl(int(viewId))
                    totalItems = int(xbmc.getInfoLabel("Container.NumItems"))
                    
                    #only do a focus if we're on top of the list, else skip to prevent bouncing of the list
                    if not int(xbmc.getInfoLabel("Container.Position")) > 1:
                        if (xbmc.getCondVisibility("Container.SortDirection(ascending)")):
                            curItem = 0
                            control.selectItem(0)
                            xbmc.sleep(250)
                            while ((xbmc.getCondVisibility("Container.Content(episodes) | Container.Content(seasons)")) and totalItems >= curItem):
                                if (xbmc.getInfoLabel("Container.ListItem(" + str(curItem) + ").Overlay") != "OverlayWatched.png" and xbmc.getInfoLabel("Container.ListItem(" + str(curItem) + ").Label") != ".." and not xbmc.getInfoLabel("Container.ListItem(" + str(curItem) + ").Label").startswith("*")):
                                    if curItem != 0:
                                        control.selectItem(curItem)
                                    break
                                else:
                                    curItem += 1
                        
                        elif (xbmc.getCondVisibility("Container.SortDirection(descending)")):
                            curItem = totalItems
                            control.selectItem(totalItems)
                            xbmc.sleep(250)
                            while ((xbmc.getCondVisibility("Container.Content(episodes) | Container.Content(seasons)")) and curItem != 0):
                                
                                if (xbmc.getInfoLabel("Container.ListItem(" + str(curItem) + ").Overlay") != "OverlayWatched.png"):
                                    control.selectItem(curItem-1)
                                    break
                                else:    
                                    curItem -= 1
                                        
            self.lastEpPath = xbmc.getInfoLabel("Container.FolderPath")
        
    def setDuration(self,currentDuration=None):
        if not currentDuration:
            currentDuration = xbmc.getInfoLabel("ListItem.Duration")
        
        if ":" in currentDuration:
            durLst = currentDuration.split(":")
            if len(durLst) == 1:
                currentDuration = "0"
            elif len(durLst) == 2:
                currentDuration = durLst[0]
            elif len(durLst) == 3:
                currentDuration = str((int(durLst[0])*60) + int(durLst[1]))
                
        # monitor listitem to set duration
        if currentDuration:
            durationString = self.getDurationString(currentDuration)
            if durationString:
                WINDOW.setProperty('SkinHelper.ListItemDuration', durationString[2])
                WINDOW.setProperty('SkinHelper.ListItemDuration.Hours', durationString[0])
                WINDOW.setProperty('SkinHelper.ListItemDuration.Minutes', durationString[1])
            else:
                WINDOW.clearProperty('SkinHelper.ListItemDuration')
                WINDOW.clearProperty('SkinHelper.ListItemDuration.Hours')
                WINDOW.clearProperty('SkinHelper.ListItemDuration.Minutes')
        else:
            WINDOW.clearProperty('SkinHelper.ListItemDuration')
            WINDOW.clearProperty('SkinHelper.ListItemDuration.Hours')
            WINDOW.clearProperty('SkinHelper.ListItemDuration.Minutes')
        
    def getDurationString(self, duration):
        if duration == None or duration == 0:
            return None
        try:
            full_minutes = int(duration)
            minutes = str(full_minutes % 60)
            minutes = str(minutes).zfill(2)
            hours   = str(full_minutes // 60)
            durationString = hours + ':' + minutes
        except Exception as e:
            logMsg("ERROR in getDurationString ! --> " + str(e), 0)
            return None
        return ( hours, minutes, durationString )
            
    def getViewId(self, viewString):
        # get all views from views-file
        viewId = None
        skin_view_file = os.path.join(xbmc.translatePath('special://skin/extras'), "views.xml")
        tree = etree.parse(skin_view_file)
        root = tree.getroot()
        for view in root.findall('view'):
            if viewString == xbmc.getLocalizedString(int(view.attrib['languageid'])):
                viewId=view.attrib['value']
        
        return viewId    
    
    def checkMusicArt(self):
        
        dbID = xbmc.getInfoLabel("ListItem.Artist") + xbmc.getInfoLabel("ListItem.Album")
        cacheFound = False

        if self.lastMusicDbId == dbID:
            return
        
        logMsg("checkMusicArt dbID--> " + dbID)

        self.lastMusicDbId = dbID
        
        if xbmc.getInfoLabel("ListItem.Label") == ".." or not xbmc.getInfoLabel("ListItem.FolderPath").startswith("musicdb"):
            WINDOW.setProperty("SkinHelper.ExtraFanArtPath","") 
            WINDOW.clearProperty("SkinHelper.Music.BannerArt") 
            WINDOW.clearProperty("SkinHelper.Music.LogoArt") 
            WINDOW.clearProperty("SkinHelper.Music.DiscArt")
            WINDOW.clearProperty("SkinHelper.Music.Info")
            WINDOW.clearProperty("SkinHelper.Music.TrackList")
            return
        
        #get the items from cache first
        if self.musicArtCache.has_key(dbID + "SkinHelper.Music.DiscArt"):
            cacheFound = True
            if self.musicArtCache[dbID + "SkinHelper.Music.DiscArt"] == "None":
                WINDOW.clearProperty("SkinHelper.Music.DiscArt")   
            else:
                WINDOW.setProperty("SkinHelper.Music.DiscArt",self.musicArtCache[dbID + "SkinHelper.Music.DiscArt"])

        if self.musicArtCache.has_key(dbID + "SkinHelper.Music.LogoArt"):
            cacheFound = True
            if self.musicArtCache[dbID + "SkinHelper.Music.LogoArt"] == "None":
                WINDOW.clearProperty("SkinHelper.Music.LogoArt")   
            else:
                WINDOW.setProperty("SkinHelper.Music.LogoArt",self.musicArtCache[dbID + "SkinHelper.Music.LogoArt"])
                
        if self.musicArtCache.has_key(dbID + "SkinHelper.Music.BannerArt"):
            cacheFound = True
            if self.musicArtCache[dbID + "SkinHelper.Music.BannerArt"] == "None":
                WINDOW.clearProperty("SkinHelper.Music.BannerArt")   
            else:
                WINDOW.setProperty("SkinHelper.Music.BannerArt",self.musicArtCache[dbID + "SkinHelper.Music.BannerArt"])
        
        if self.musicArtCache.has_key(dbID + "extraFanArt"):
            cacheFound = True
            if self.musicArtCache[dbID + "extraFanArt"] == "None":
                WINDOW.setProperty("SkinHelper.ExtraFanArtPath","")   
            else:
                WINDOW.setProperty("SkinHelper.ExtraFanArtPath",self.musicArtCache[dbID + "extraFanArt"])
                
        if self.musicArtCache.has_key(dbID + "SkinHelper.Music.Info"):
            cacheFound = True
            if self.musicArtCache[dbID + "SkinHelper.Music.Info"] == "None":
                WINDOW.setProperty("SkinHelper.Music.Info","")   
            else:
                WINDOW.setProperty("SkinHelper.Music.Info",self.musicArtCache[dbID + "SkinHelper.Music.Info"])
        
        if self.musicArtCache.has_key(dbID + "SkinHelper.Music.TrackList"):
            cacheFound = True
            if self.musicArtCache[dbID + "SkinHelper.Music.TrackList"] == "None":
                WINDOW.setProperty("SkinHelper.Music.TrackList","")   
            else:
                WINDOW.setProperty("SkinHelper.Music.TrackList",self.musicArtCache[dbID + "SkinHelper.Music.TrackList"])

        if not cacheFound:
            logMsg("checkMusicArt no cache found for dbID--> " + dbID,0)
            path = None
            json_response = None
            cdArt = None
            LogoArt = None
            BannerArt = None
            extraFanArt = None
            Info = None
            TrackList = ""
            folderPath = xbmc.getInfoLabel("ListItem.FolderPath")
            dbid = xbmc.getInfoLabel("ListItem.DBID")
            if xbmc.getCondVisibility("Container.Content(songs) | Container.Content(singles) | SubString(ListItem.FolderPath,.)"):
                logMsg("checkMusicArt - container content is songs or singles",0)
                if dbid:
                    json_response = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetSongDetails", "params": { "songid": %s, "properties": [ "file","artistid","albumid","comment" ] }, "id": "libSongs"}'%int(dbid))
                
            elif xbmc.getCondVisibility("[Container.Content(artists) | SubString(ListItem.FolderPath,musicdb://artists)] + !SubString(ListItem.FolderPath,artistid=)"):
                logMsg("checkMusicArt - container content is artists",0)
                if dbid:    
                    json_response = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetSongs", "params": { "filter":{"artistid": %s}, "properties": [ "file","artistid","track","title" ] }, "id": "libSongs"}'%int(dbid))
            
            elif xbmc.getCondVisibility("Container.Content(albums) | SubString(ListItem.FolderPath,musicdb://albums) | SubString(ListItem.FolderPath,artistid=)"):
                logMsg("checkMusicArt - container content is albums",0)
                if dbid:
                    json_response = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetSongs", "params": { "filter":{"albumid": %s}, "properties": [ "file","artistid","track","title" ] }, "id": "libSongs"}'%int(dbid))
            
            if json_response:
                song = None
                json_response = json.loads(json_response)
                if json_response.has_key("result"):
                    result = json_response["result"]
                    if result.has_key("songs"):
                        songs = result["songs"]
                        if len(songs) > 0:
                            song = songs[0]
                            path = song["file"]
                        #get track listing
                        for song in songs:
                            if song["track"]:
                                TrackList += "%s - %s[CR]" %(str(song["track"]), song["title"])
                            else:
                                TrackList += "%s[CR]" %(song["title"])
                            
                    elif result.has_key("songdetails"):
                        song = result["songdetails"]
                        path = song["file"]
                        if not Info:
                            json_response2 = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetAlbumDetails", "params": { "albumid": %s, "properties": [ "musicbrainzalbumid","description" ] }, "id": "1"}'%song["albumid"])
                            json_response2 = json.loads(json_response2)
                            if json_response2.has_key("result"):
                                result = json_response2["result"]
                                if result.has_key("albumdetails"):
                                    albumdetails = result["albumdetails"]
                                    if albumdetails["description"]:
                                        Info = albumdetails["description"]
                    if not Info and song:
                        json_response2 = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetArtistDetails", "params": { "artistid": %s, "properties": [ "musicbrainzartistid","description" ] }, "id": "1"}'%song["artistid"][0])
                        json_response2 = json.loads(json_response2)
                        if json_response2.has_key("result"):
                            result = json_response2["result"]
                            if result.has_key("artistdetails"):
                                artistdetails = result["artistdetails"]
                                if artistdetails["description"]:
                                    Info = artistdetails["description"]

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
   
            if extraFanArt:
                WINDOW.setProperty("SkinHelper.ExtraFanArtPath",extraFanArt)
                self.musicArtCache[dbID + "extraFanArt"] = extraFanArt
            else:
                WINDOW.setProperty("SkinHelper.ExtraFanArtPath","")
                self.musicArtCache[dbID + "extraFanArt"] = "None"
                    
            if cdArt:
                WINDOW.setProperty("SkinHelper.Music.DiscArt",cdArt)
                self.musicArtCache[dbID + "SkinHelper.Music.DiscArt"] = cdArt
            else:
                WINDOW.setProperty("SkinHelper.Music.DiscArt","")
                self.musicArtCache[dbID + "SkinHelper.Music.DiscArt"] = "None"
                
            if BannerArt:
                WINDOW.setProperty("SkinHelper.Music.BannerArt",BannerArt)
                self.musicArtCache[dbID + "SkinHelper.Music.BannerArt"] = BannerArt
            else:
                WINDOW.clearProperty("SkinHelper.Music.BannerArt")
                self.musicArtCache[dbID + "SkinHelper.Music.BannerArt"] = "None"

            if LogoArt:
                WINDOW.setProperty("SkinHelper.Music.LogoArt",LogoArt)
                self.musicArtCache[dbID + "SkinHelper.Music.LogoArt"] = LogoArt
            else:
                WINDOW.clearProperty("SkinHelper.Music.LogoArt")
                self.musicArtCache[dbID + "SkinHelper.Music.LogoArt"] = "None"

            if TrackList:
                WINDOW.setProperty("SkinHelper.Music.TrackList",TrackList)
                self.musicArtCache[dbID + "SkinHelper.Music.TrackList"] = TrackList
            else:
                WINDOW.clearProperty("SkinHelper.Music.TrackList")
                self.musicArtCache[dbID + "SkinHelper.Music.TrackList"] = "None"
                
            if Info:
                WINDOW.setProperty("SkinHelper.Music.Info",Info)
                self.musicArtCache[dbID + "SkinHelper.Music.Info"] = Info
            else:
                WINDOW.clearProperty("SkinHelper.Music.Info")
                self.musicArtCache[dbID + "SkinHelper.Music.Info"] = "None"
                
    def checkExtraFanArt(self):
        
        lastPath = None
        efaPath = None
        efaFound = False
        liArt = None
        containerPath = xbmc.getInfoLabel("Container.FolderPath")
        
        if xbmc.getCondVisibility("Window.IsActive(movieinformation)"):
            return
        
        #always clear the individual fanart items first
        totalNodes = 50
        for i in range(totalNodes):
            if not WINDOW.getProperty('SkinHelper.ExtraFanArt.' + str(i)):
                break
            WINDOW.clearProperty('SkinHelper.ExtraFanArt.' + str(i))
        
        #get the item from cache first
        if self.extraFanartcache.has_key(self.liPath):
            if self.extraFanartcache[self.liPath][0] == "None":
                WINDOW.setProperty("SkinHelper.ExtraFanArtPath","")
                return
            else:
                WINDOW.setProperty("SkinHelper.ExtraFanArtPath",self.extraFanartcache[self.liPath][0])
                count = 0
                for file in self.extraFanartcache[self.liPath][1]:
                    WINDOW.setProperty("SkinHelper.ExtraFanArt." + str(count),file)
                    count +=1  
                return
        
        if not xbmc.getCondVisibility("Skin.HasSetting(SkinHelper.EnableExtraFanart) + [Window.IsActive(videolibrary) | Window.IsActive(movieinformation)] + !Container.Scrolling"):
            WINDOW.setProperty("SkinHelper.ExtraFanArtPath","")
            return
        
        if (self.liPath != None and (xbmc.getCondVisibility("Container.Content(movies) | Container.Content(seasons) | Container.Content(episodes) | Container.Content(tvshows)")) and not "videodb:" in self.liPath):
                           
            if xbmc.getCondVisibility("Container.Content(episodes)"):
                liArt = xbmc.getInfoLabel("ListItem.Art(tvshow.fanart)")
            
            # do not set extra fanart for virtuals
            if (("plugin://" in self.liPath) or ("addon://" in self.liPath) or ("sources" in self.liPath) or ("plugin://" in containerPath) or ("sources://" in containerPath) or ("plugin://" in containerPath)):
                WINDOW.setProperty("SkinHelper.ExtraFanArtPath","")
                self.extraFanartcache[self.liPath] = "None"
                lastPath = None
            else:

                if xbmcvfs.exists(self.liPath + "extrafanart/"):
                    efaPath = self.liPath + "extrafanart/"
                else:
                    pPath = self.liPath.rpartition("/")[0]
                    pPath = pPath.rpartition("/")[0]
                    if xbmcvfs.exists(pPath + "/extrafanart/"):
                        efaPath = pPath + "/extrafanart/"
                        
                if xbmcvfs.exists(efaPath):
                    dirs, files = xbmcvfs.listdir(efaPath)
                    count = 0
                    extraFanArtfiles = []
                    for file in files:
                        if file.lower().endswith(".jpg"):
                            efaFound = True
                            WINDOW.setProperty("SkinHelper.ExtraFanArt." + str(count),efaPath+file)
                            extraFanArtfiles.append(efaPath+file)
                            count +=1  
       
                if (efaPath != None and efaFound == True):
                    if lastPath != efaPath:
                        WINDOW.setProperty("SkinHelper.ExtraFanArtPath",efaPath)
                        self.extraFanartcache[self.liPath] = [efaPath, extraFanArtfiles]
                        lastPath = efaPath       
                else:
                    WINDOW.setProperty("SkinHelper.ExtraFanArtPath","")
                    self.extraFanartcache[self.liPath] = ["None",[]]
                    lastPath = None
        else:
            WINDOW.setProperty("SkinHelper.ExtraFanArtPath","")
            lastPath = None

class Kodi_Monitor(xbmc.Monitor):
    
    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)
    
    def onDatabaseUpdated(self, database):
        #update widgets when library has changed
        WINDOW = xbmcgui.Window(10000)
        WINDOW.setProperty("widgetreload", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        #refresh some widgets when library has changed
        WINDOW.setProperty("widgetrefresh","refresh")
        xbmc.sleep(500)
        WINDOW.clearProperty("widgetrefresh")

    def onNotification(self,sender,method,data):
        if method == "VideoLibrary.OnUpdate":
            #update nextup list when library has changed
            WINDOW.setProperty("widgetreload", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            #refresh some widgets when library has changed
            WINDOW.setProperty("widgetrefresh","refresh")
            xbmc.sleep(500)
            WINDOW.clearProperty("widgetrefresh")
        
        if method == "Player.OnPlay":
            
            try:
                secondsToDisplay = int(xbmc.getInfoLabel("Skin.String(SkinHelper.ShowInfoAtPlaybackStart)"))
            except:
                secondsToDisplay = 0
            
            logMsg("onNotification - ShowInfoAtPlaybackStart - number of seconds: " + str(secondsToDisplay),0)
            
            #Show the OSD info panel on playback start
            if secondsToDisplay != 0:
                tryCount = 0
                if WINDOW.getProperty("VideoScreensaverRunning") != "true":
                    while tryCount !=50 and xbmc.getCondVisibility("!Window.IsActive(fullscreeninfo)"):
                        xbmc.sleep(100)
                        if xbmc.getCondVisibility("!Window.IsActive(fullscreeninfo) + Window.IsActive(fullscreenvideo)"):
                            xbmc.executebuiltin('Action(info)')
                        tryCount += 1
                    
                    # close info again
                    xbmc.sleep(secondsToDisplay*1000)
                    if xbmc.getCondVisibility("Window.IsActive(fullscreeninfo)"):
                        xbmc.executebuiltin('Action(info)')

                                           