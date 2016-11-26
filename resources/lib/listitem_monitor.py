#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    script.skin.helper.service
    listitem_monitor.py
    monitor the kodi listitems and providing additional information
'''

import threading
import thread
from utils import log_msg, log_exception, get_current_content_type, kodi_json, prepare_win_props
from artutils import extend_dict
import xbmc
from simplecache import use_cache


class ListItemMonitor(threading.Thread):
    '''Our main class monitoring the kodi listitems and providing additional information'''
    event = None
    exit = False
    delayed_task_interval = 1795
    listitem_details = {}
    all_window_props = []
    cur_listitem = ""
    last_folder = ""
    last_listitem = ""
    foldercontent = {}
    screensaver_setting = None
    screensaver_disabled = False
    lookup_busy = {}
    enable_extendedart = False
    enable_musicart = False
    enable_animatedart = False
    enable_extrafanart = False
    enable_pvrart = False

    def __init__(self, *args, **kwargs):
        self.cache = kwargs.get("cache")
        self.artutils = kwargs.get("artutils")
        self.win = kwargs.get("win")
        self.kodimonitor = kwargs.get("monitor")
        self.event = threading.Event()
        threading.Thread.__init__(self, *args)

    def stop(self):
        '''called when the thread has to stop working'''
        log_msg("ListItemMonitor - stop called")
        self.exit = True
        self.event.set()

    def run(self):
        '''our main loop monitoring the listitem and folderpath changes'''
        log_msg("ListItemMonitor - started")
        while not self.exit:

            # check screensaver and OSD
            self.check_screensaver()
            self.check_osd()

            # do some background stuff every 30 minutes
            if (self.delayed_task_interval >= 1800) and not self.exit:
                thread.start_new_thread(self.do_background_work, ())
                self.delayed_task_interval = 0

            # skip if any of the artwork context menus is opened
            if self.win.getProperty("SkinHelper.Artwork.ManualLookup"):
                self.reset_win_props()
                self.last_listitem = ""
                self.listitem_details = {}
                self.kodimonitor.waitForAbort(3)
                self.delayed_task_interval += 3

            # skip when modal dialogs are opened (e.g. textviewer in musicinfo dialog)
            elif xbmc.getCondVisibility(
                    "System.HasModalDialog | Window.IsActive(progressdialog) | Window.IsActive(busydialog)"):
                self.kodimonitor.waitForAbort(2)
                self.delayed_task_interval += 2
                self.last_listitem = ""

            # media window is opened or widgetcontainer set - start listitem monitoring!
            elif xbmc.getCondVisibility("Window.IsMedia | "
                                        "!IsEmpty(Window(Home).Property(SkinHelper.WidgetContainer))"):
                self.monitor_listitem()
                self.kodimonitor.waitForAbort(0.15)
                self.delayed_task_interval += 0.15

            # flush any remaining window properties
            elif self.all_window_props:
                self.reset_win_props()
                self.win.clearProperty("SkinHelper.ContentHeader")
                self.win.clearProperty("contenttype")
                self.win.clearProperty("curlistitem")
                self.last_listitem = ""

            # other window active - do nothing
            else:
                self.kodimonitor.waitForAbort(1)
                self.delayed_task_interval += 1

    def get_settings(self):
        '''collect our skin settings that control the monitoring'''
        self.enable_extendedart = xbmc.getCondVisibility("Skin.HasSetting(SkinHelper.EnableExtendedArt)") == 1
        self.enable_musicart = xbmc.getCondVisibility("Skin.HasSetting(SkinHelper.EnableMusicArt)") == 1
        self.enable_animatedart = xbmc.getCondVisibility("Skin.HasSetting(SkinHelper.EnableAnimatedPosters)") == 1
        self.enable_extrafanart = xbmc.getCondVisibility("Skin.HasSetting(SkinHelper.EnableExtraFanart)") == 1
        self.enable_pvrart = xbmc.getCondVisibility(
            "Skin.HasSetting(SkinHelper.EnablePVRThumbs) + PVR.HasTVChannels") == 1
        studiologos_path = xbmc.getInfoLabel("Skin.String(SkinHelper.StudioLogos.Path)").decode("utf-8")
        if studiologos_path != self.artutils.studiologos_path:
            self.listitem_details = {}
            self.artutils.studiologos_path = studiologos_path

    def monitor_listitem(self):
        '''Monitor listitem details'''

        cur_folder, cont_prefix = self.get_folderandprefix()
        li_label = xbmc.getInfoLabel("%sListItem.Label" % cont_prefix).decode('utf-8')

        # perform actions if the container path has changed
        if cur_folder != self.last_folder:
            self.reset_win_props()
            self.get_settings()
            self.last_folder = cur_folder
            content_type = self.get_content_type(cur_folder, li_label, cont_prefix)
            # additional actions to perform when we have a valid contenttype and no widget container
            if not cont_prefix and content_type:
                self.set_forcedview(content_type)
                self.set_content_header(content_type)
        else:
            content_type = self.get_content_type(cur_folder, li_label, cont_prefix)

        if self.exit:
            return

        # only perform actions when the listitem has actually changed
        li_title = xbmc.getInfoLabel("%sListItem.Title" % cont_prefix).decode('utf-8')
        cur_listitem = "%s--%s--%s--%s" % (cur_folder, li_label, li_title, content_type)

        if cur_listitem and content_type and cur_listitem != self.last_listitem:
            self.last_listitem = cur_listitem
            # clear all window props first
            self.reset_win_props()
            self.set_win_prop(("curlistitem", cur_listitem))
            if not li_label == "..":
                # set listitem details in background thread
                thread.start_new_thread(
                    self.set_listitem_details, (cur_listitem, content_type, cont_prefix))

    def get_folderandprefix(self):
        '''get the current folder and prefix'''
        cur_folder = ""
        cont_prefix = ""
        try:
            widget_container = self.win.getProperty("SkinHelper.WidgetContainer").decode('utf-8')
            if xbmc.getCondVisibility("Window.IsActive(movieinformation)"):
                cont_prefix = ""
                cur_folder = xbmc.getInfoLabel(
                    "movieinfo-$INFO[Container.FolderPath]"
                    "$INFO[Container.NumItems]"
                    "$INFO[Container.Content]").decode('utf-8')
            elif widget_container:
                cont_prefix = "Container(%s)." % widget_container
                cur_folder = xbmc.getInfoLabel(
                    "widget-%s-$INFO[Container(%s).NumItems]-$INFO[Container(%s).ListItemAbsolute(1).Label]" %
                    (widget_container, widget_container, widget_container)).decode('utf-8')
            else:
                cont_prefix = ""
                cur_folder = xbmc.getInfoLabel(
                    "$INFO[Container.FolderPath]$INFO[Container.NumItems]$INFO[Container.Content]").decode(
                    'utf-8')
        except Exception as exc:
            log_exception(__name__, exc)
            cur_folder = ""
            cont_prefix = ""
        return (cur_folder, cont_prefix)

    def get_content_type(self, cur_folder, li_label, cont_prefix):
        '''get contenttype for current folder'''
        content_type = ""
        if cur_folder in self.foldercontent:
            content_type = self.foldercontent[cur_folder]
        elif cur_folder and li_label:
            # always wait for the content_type because some listings can be slow
            for i in range(20):
                content_type = get_current_content_type(cont_prefix)
                if self.exit:
                    return ""
                if content_type:
                    break
                else:
                    xbmc.sleep(250)
            self.foldercontent[cur_folder] = content_type
            self.win.setProperty("contenttype", content_type)
        return content_type

    def check_screensaver(self):
        '''Allow user to disable screensaver on fullscreen music playback'''
        if xbmc.getCondVisibility(
                "Window.IsActive(visualisation) + Skin.HasSetting(SkinHelper.DisableScreenSaverOnFullScreenMusic)"):
            if not self.screensaver_disabled:
                # disable screensaver when fullscreen music active
                self.screensaver_setting = kodi_json('Settings.GetSettingValue', '{"setting":"screensaver.mode"}')
                kodi_json('Settings.SetSettingValue', {"setting": "screensaver.mode", "value": None})
                self.screensaver_disabled = True
                log_msg(
                    "Disabled screensaver while fullscreen music playback - previous setting: %s" %
                    self.screensaver_setting)
        elif self.screensaver_setting and self.screensaver_disabled:
            # enable screensaver again after fullscreen music playback was ended
            kodi_json('Settings.SetSettingValue', {"setting": "screensaver.mode", "value": self.screensaver_setting})
            self.screensaver_disabled = False
            log_msg("fullscreen music playback ended - restoring screensaver: %s" % self.screensaver_setting)

    @staticmethod
    def check_osd():
        '''Allow user to set a default close timeout for the OSD panels'''
        if xbmc.getCondVisibility("[Window.IsActive(videoosd) + Skin.String(SkinHelper.AutoCloseVideoOSD)] | "
                                  "[Window.IsActive(musicosd) + Skin.String(SkinHelper.AutoCloseMusicOSD)]"):
            if xbmc.getCondVisibility("Window.IsActive(videoosd)"):
                seconds = xbmc.getInfoLabel("Skin.String(SkinHelper.AutoCloseVideoOSD)")
                window = "videoosd"
            elif xbmc.getCondVisibility("Window.IsActive(musicosd)"):
                seconds = xbmc.getInfoLabel("Skin.String(SkinHelper.AutoCloseMusicOSD)")
                window = "musicosd"
            else:
                seconds = ""
            if seconds and seconds != "0":
                while xbmc.getCondVisibility("Window.IsActive(%s)" % window):
                    if xbmc.getCondVisibility("System.IdleTime(%s)" % seconds):
                        if xbmc.getCondVisibility("Window.IsActive(%s)" % window):
                            xbmc.executebuiltin("w.Close(%s)" % window)
                    else:
                        xbmc.sleep(500)

    def set_listitem_details(self, cur_listitem, content_type, prefix):
        '''set the window properties based on the current listitem'''
        try:
            if cur_listitem in self.listitem_details:
                # data already in memory
                all_props = self.listitem_details[cur_listitem]
            else:
                # collect all details from listitem
                listitem = self.get_listitem_details(content_type, prefix)

                if prefix and cur_listitem == self.last_listitem:
                    # for widgets we immediately set all normal properties as window prop
                    self.set_win_props(prepare_win_props(listitem))

                # if another lookup for the same listitem already in progress... wait for it to complete
                while self.lookup_busy.get(cur_listitem):
                    xbmc.sleep(250)
                    if self.exit:
                        return
                self.lookup_busy[cur_listitem] = True

                # music content
                if content_type in ["albums", "artists", "songs"] and self.enable_musicart:
                    artist = listitem["albumartist"]
                    if not artist:
                        artist = listitem["artist"]
                    listitem = extend_dict(listitem,
                                           self.artutils.get_music_artwork(
                                               artist, listitem["album"], listitem["title"], listitem["discnumber"]))

                # moviesets
                elif listitem["path"].startswith("videodb://movies/sets/") and listitem["dbid"]:
                    listitem = extend_dict(listitem, self.artutils.get_moviesetdetails(listitem["dbid"]))

                # video content
                elif content_type in ["movies", "setmovies", "tvshows", "seasons", "episodes", "musicvideos"]:

                    # get imdb_id
                    listitem["imdbnumber"], tvdbid = self.get_imdb_id(listitem, content_type)

                    # generic video properties (studio, streamdetails, omdb, top250)
                    listitem = extend_dict(listitem, self.get_directors(listitem["director"]))
                    listitem = extend_dict(listitem, self.get_extrafanart(listitem["path"], content_type))
                    listitem = extend_dict(listitem, self.get_genres(listitem["genre"]))
                    listitem = extend_dict(listitem, self.artutils.get_duration(listitem["duration"]))
                    listitem = extend_dict(listitem, self.artutils.get_studio_logo(listitem["studio"]))
                    listitem = extend_dict(listitem, self.artutils.get_omdb_info(listitem["imdbnumber"]))
                    listitem = extend_dict(
                        listitem, self.get_streamdetails(
                            listitem["dbid"], listitem["path"], content_type))
                    if self.exit:
                        return
                    listitem = extend_dict(listitem, self.artutils.get_top250_rating(listitem["imdbnumber"]))
                    if self.enable_extendedart:
                        if not (listitem["art"]["clearlogo"] or listitem["art"]["landscape"]):
                            listitem = extend_dict(listitem, self.artutils.get_extended_artwork(
                                listitem["imdbnumber"], tvdbid, content_type))

                    if self.exit:
                        return

                    # tvshows-only properties (tvdb)
                    if content_type in ["tvshows", "seasons", "episodes"]:
                        listitem = extend_dict(listitem,
                                               self.artutils.get_tvdb_details(listitem["imdbnumber"], tvdbid))

                    # movies-only properties (tmdb, animated art)
                    if content_type in ["movies", "setmovies"]:
                        listitem = extend_dict(listitem, self.artutils.get_tmdb_details(listitem["imdbnumber"]))
                        if listitem["imdbnumber"] and self.enable_animatedart:
                            listitem = extend_dict(listitem, self.artutils.get_animated_artwork(listitem["imdbnumber"]))

                if self.exit:
                    return

                # monitor listitem props when PVR is active
                elif content_type in ["tvchannels", "tvrecordings", "channels", "recordings", "timers", "tvtimers"]:
                    listitem = self.get_pvr_artwork(listitem, prefix)

                # process all properties
                all_props = prepare_win_props(listitem)
                if content_type not in ["weathers", "systeminfos"]:
                    self.listitem_details[cur_listitem] = all_props

                self.lookup_busy.pop(cur_listitem, None)

            if cur_listitem == self.last_listitem:
                self.set_win_props(all_props)
        except Exception as exc:
            log_exception(__name__, exc)

    def do_background_work(self):
        '''stuff that's processed in the background'''
        try:
            if self.exit:
                return
            log_msg("Started Background worker...")
            self.set_generic_props()
            self.listitem_details = {}
            self.cache.check_cleanup()
            log_msg("Ended Background worker...")
        except Exception as exc:
            log_exception(__name__, exc)

    def set_generic_props(self):
        '''set some genric window props with item counts'''
        # GET TOTAL ADDONS COUNT
        addons_count = len(kodi_json('Addons.GetAddons'))
        self.win.setProperty("SkinHelper.TotalAddons", "%s" % addons_count)

        addontypes = []
        addontypes.append(["executable", "SkinHelper.TotalProgramAddons", 0])
        addontypes.append(["video", "SkinHelper.TotalVideoAddons", 0])
        addontypes.append(["audio", "SkinHelper.TotalAudioAddons", 0])
        addontypes.append(["image", "SkinHelper.TotalPicturesAddons", 0])
        for addontype in addontypes:
            media_array = kodi_json('Addons.GetAddons', {"content": addontype[0]})
            for item in media_array:
                addontype[2] += 1
            self.win.setProperty(addontype[1], str(addontype[2]))

        # GET FAVOURITES COUNT
        favs = kodi_json('Favourites.GetFavourites')
        if favs:
            self.win.setProperty("SkinHelper.TotalFavourites", "%s" % len(favs))

        # GET TV CHANNELS COUNT
        if xbmc.getCondVisibility("Pvr.HasTVChannels"):
            tv_channels = kodi_json('PVR.GetChannels', {"channelgroupid": "alltv"})
            self.win.setProperty("SkinHelper.TotalTVChannels", "%s" % len(tv_channels))

        # GET MOVIE SETS COUNT
        movieset_movies_count = 0
        moviesets = kodi_json('VideoLibrary.GetMovieSets')
        for item in moviesets:
            for item in kodi_json('VideoLibrary.GetMovieSetDetails', {"setid": item["setid"]}):
                movieset_movies_count += 1
        self.win.setProperty("SkinHelper.TotalMovieSets", "%s" % len(moviesets))
        self.win.setProperty("SkinHelper.TotalMoviesInSets", "%s" % movieset_movies_count)

        # GET RADIO CHANNELS COUNT
        if xbmc.getCondVisibility("Pvr.HasRadioChannels"):
            radio_channels = kodi_json('PVR.GetChannels', {"channelgroupid": "allradio"})
            self.win.setProperty("SkinHelper.TotalRadioChannels", "%s" % len(radio_channels))

    def reset_win_props(self):
        '''reset all window props set by the script...'''
        for prop in self.all_window_props:
            self.win.clearProperty(prop)
        self.all_window_props = []

    @use_cache(14)
    def get_imdb_id(self, listitem, content_type):
        '''try to figure out the imdbnumber because that's what we use for all lookup actions'''
        tvdbid = ""
        imdbid = listitem["imdbnumber"]
        if content_type in ["seasons", "episodes"]:
            listitem["title"] = listitem["tvshowtitle"]
            content_type = "tvshows"
        if imdbid and not imdbid.startswith("tt"):
            if content_type in ["tvshows", "seasons", "episodes"]:
                tvdbid = imdbid
                imdbid = ""
        if not imdbid and listitem["year"]:
            imdbid = self.artutils.get_omdb_info(
                "", listitem["title"], listitem["year"], content_type).get("imdbnumber", "")
        if not imdbid:
            # repeat without year
            imdbid = self.artutils.get_omdb_info("", listitem["title"], "", content_type).get("imdbnumber", "")
        # return results
        return (imdbid, tvdbid)

    def set_win_prop(self, prop_tuple):
        '''sets a window property based on the given tuple of key-value'''
        if prop_tuple[1] and not prop_tuple[0] in self.all_window_props:
            self.all_window_props.append(prop_tuple[0])
            self.win.setProperty(prop_tuple[0], prop_tuple[1])

    def set_win_props(self, prop_tuples):
        '''set multiple window properties from list of tuples'''
        for prop_tuple in prop_tuples:
            self.set_win_prop(prop_tuple)

    def set_content_header(self, content_type):
        '''sets a window propery which can be used as headertitle'''
        self.win.clearProperty("SkinHelper.ContentHeader")
        itemscount = xbmc.getInfoLabel("Container.NumItems")
        if itemscount:
            if xbmc.getInfoLabel("Container.ListItemNoWrap(0).Label").startswith(
                    "*") or xbmc.getInfoLabel("Container.ListItemNoWrap(1).Label").startswith("*"):
                itemscount = int(itemscount) - 1

            headerprefix = ""
            if content_type == "movies":
                headerprefix = xbmc.getLocalizedString(36901)
            elif content_type == "tvshows":
                headerprefix = xbmc.getLocalizedString(36903)
            elif content_type == "seasons":
                headerprefix = xbmc.getLocalizedString(36905)
            elif content_type == "episodes":
                headerprefix = xbmc.getLocalizedString(36907)
            elif content_type == "sets":
                headerprefix = xbmc.getLocalizedString(36911)
            elif content_type == "albums":
                headerprefix = xbmc.getLocalizedString(36919)
            elif content_type == "songs":
                headerprefix = xbmc.getLocalizedString(36921)
            elif content_type == "artists":
                headerprefix = xbmc.getLocalizedString(36917)

            if headerprefix:
                self.win.setProperty("SkinHelper.ContentHeader", "%s %s" % (itemscount, headerprefix))

    @staticmethod
    def get_genres(li_genre):
        '''get formatted genre string from actual genre'''
        details = {}
        genres = li_genre.split(" / ")
        details['genres'] = "[CR]".join(genres)
        for count, genre in enumerate(genres):
            details["genre.%s" % count] = genre
        return details

    @staticmethod
    def get_directors(director):
        '''get a formatted string with directors from the actual directors string'''
        directors = director.split(" / ")
        return {'Directors': "[CR]".join(directors)}

    @staticmethod
    def get_listitem_details(content_type, prefix):
        '''collect all listitem properties/values we need'''

        # collect all the infolabels we need
        listitem_details = {"art": {}}
        props = ["label", "title", "filenameandpath", "year", "genre", "path", "folderpath",
                 "art(fanart)", "art(poster)", "art(clearlogo)", "art(clearart)", "art(landscape)",
                 "fileextension", "duration", "plot", "plotoutline", "icon", "thumb", "label2",
                 "dbtype", "dbid", "art(thumb)", "art(banner)"
                 ]
        if content_type in ["movies", "tvshows", "seasons", "episodes", "musicvideos", "setmovies"]:
            props += ["art(characterart)", "studio", "tvshowtitle", "premiered", "director", "writer",
                      "firstaired", "videoresolution", "audiocodec", "audiochannels", "videocodec", "videoaspect",
                      "subtitlelanguage", "audiolanguage", "mpaa", "isstereoscopic", "video3dformat",
                      "tagline", "rating", "imdbnumber"]
            if content_type in ["episodes"]:
                props += ["season", "episode", "art(tvshow.landscape)", "art(tvshow.clearlogo)",
                          "art(tvshow.poster)"]
        elif content_type in ["musicvideos", "artists", "albums", "songs"]:
            props += ["artist", "album", "rating", "albumartist", "discnumber"]
        elif content_type in ["tvchannels", "tvrecordings", "channels", "recordings", "timers", "tvtimers"]:
            props += ["channel", "startdatetime", "datetime", "date", "channelname",
                      "starttime", "startdate", "endtime", "enddate"]
        for prop in props:
            propvalue = xbmc.getInfoLabel('%sListItem.%s' % (prefix, prop)).decode('utf-8')
            if not propvalue or propvalue == "-1":
                propvalue = xbmc.getInfoLabel('%sListItem.Property(%s)' % (prefix, prop)).decode('utf-8')
            if "art(" in prop:
                prop = prop.replace("art(", "").replace(")", "")
                listitem_details["art"][prop] = propvalue
            else:
                listitem_details[prop] = propvalue

        # fix for folderpath
        if not listitem_details.get("path"):
            listitem_details["path"] = listitem_details["folderpath"]

        return listitem_details

    def get_streamdetails(self, li_dbid, li_path, content_type):
        '''get the streamdetails for the current video'''
        details = {}
        if li_dbid and content_type in ["movies", "episodes",
                                        "musicvideos"] and not li_path.startswith("videodb://movies/sets/"):
            details = self.artutils.get_streamdetails(li_dbid, content_type)
        return details

    def set_forcedview(self, content_type):
        '''helper to force the view in certain conditions'''
        cur_forced_view = xbmc.getInfoLabel("Skin.String(SkinHelper.ForcedViews.%s)" % content_type)
        if xbmc.getCondVisibility("Control.IsVisible(%s) | IsEmpty(Container.Viewmode)" % cur_forced_view):
            # skip if the view is already visible or if we're not in an actual media window
            return
        if (content_type and cur_forced_view and cur_forced_view != "None" and xbmc.getCondVisibility(
                "Skin.HasSetting(SkinHelper.ForcedViews.Enabled)") and not
                xbmc.getCondVisibility("Window.IsActive(MyPvrGuide.xml)")):
            self.win.setProperty("SkinHelper.ForcedView", cur_forced_view)
            xbmc.executebuiltin("Container.SetViewMode(%s)" % cur_forced_view)
            if not xbmc.getCondVisibility("Control.HasFocus(%s)" % cur_forced_view):
                xbmc.sleep(100)
                xbmc.executebuiltin("Container.SetViewMode(%s)" % cur_forced_view)
                xbmc.executebuiltin("SetFocus(%s)" % cur_forced_view)
        else:
            self.win.clearProperty("SkinHelper.ForcedView")

    def get_extrafanart(self, li_dbid, content_type):
        '''get the extrafanart path for the actual video item'''
        details = {}
        if self.enable_extrafanart:
            if li_dbid and content_type in ["movies", "seasons", "episodes", "tvshows", "setmovies", "moviesets"]:
                details = self.artutils.get_extrafanart(li_dbid, content_type)
        return details

    def get_pvr_artwork(self, listitem, prefix):
        '''get pvr artwork from artwork module'''
        if self.enable_pvrart:
            if xbmc.getCondVisibility("%sListItem.IsFolder" % prefix) and not listitem[
                    "channelname"] and not listitem["title"]:
                listitem["title"] = listitem["label"]
            listitem = extend_dict(
                listitem, self.artutils.get_pvr_artwork(
                    listitem["title"],
                    listitem["channelname"],
                    listitem["genre"]), ["title", "genre", "genres", "thumb"])
        # pvr channellogo
        listitem["ChannelLogo"] = self.artutils.get_channellogo(listitem["channelname"])
        return listitem
