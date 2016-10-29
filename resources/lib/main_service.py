#!/usr/bin/python
# -*- coding: utf-8 -*-

from utils import log_msg, ADDON_ID, log_exception
from skinsettings import SkinSettings
from backgrounds_updater import BackgroundsUpdater
from listitem_monitor import ListItemMonitor
from kodi_monitor import KodiMonitor
from player_monitor import PlayerMonitor
from webservice import WebService
from simplecache import SimpleCache
from artutils import ArtUtils
import xbmc, xbmcaddon, xbmcgui
import time, datetime

class MainService:
    '''Service that holds the threads providing info to Kodi skins'''
    last_skin = ""

    def __init__(self):
        '''our main background service running the various threads'''
        self.win = xbmcgui.Window(10000)
        self.addon = xbmcaddon.Addon(ADDON_ID)
        self.cache = SimpleCache(autocleanup=True)
        self.artutils = ArtUtils()
        self.addonname = self.addon.getAddonInfo('name').decode("utf-8")
        self.addonversion = self.addon.getAddonInfo('version').decode("utf-8")
        self.kodimonitor = KodiMonitor(cache=self.cache, artutils=self.artutils, win=self.win)
        self.player_monitor = PlayerMonitor(cache=self.cache, artutils=self.artutils)
        listitem_monitor = ListItemMonitor(cache=self.cache, artutils=self.artutils, win=self.win, monitor=self.kodimonitor)
        backgrounds_updater = BackgroundsUpdater(cache=self.cache, artutils=self.artutils, win=self.win, monitor=self.kodimonitor)
        webservice = WebService(artutils=self.artutils, win=self.win)
        widget_task_interval = 520

        #start the extra threads
        listitem_monitor.start()
        backgrounds_updater.start()
        webservice.start()
        self.win.clearProperty("SkinHelperShutdownRequested")
        log_msg('%s version %s started' %(self.addonname, self.addonversion), xbmc.LOGNOTICE)

        #run as service, check skin every 10 seconds and keep the other threads alive
        while not (self.kodimonitor.abortRequested()):
            
            #check skin version info
            self.check_skin_version()
            
            #set generic widget reload
            widget_task_interval += 10
            if widget_task_interval >= 600:
                self.win.setProperty("widgetreload2", time.strftime("%Y%m%d%H%M%S", time.gmtime()))
                widget_task_interval = 0
            
            #sleep for 10 seconds
            self.kodimonitor.waitForAbort(10)

        #Abort was requested while waiting. We should exit
        self.win.setProperty("SkinHelperShutdownRequested","shutdown")
        log_msg('Shutdown requested !',xbmc.LOGNOTICE)
        #stop the extra threads
        backgrounds_updater.stop()
        listitem_monitor.stop()
        webservice.stop()
        #cleanup objects
        self.artutils.close()
        self.cache.close()
        del backgrounds_updater
        del listitem_monitor
        del webservice
        del self.win
        del self.kodimonitor
        del self.player_monitor
        del self.addon
        log_msg('%s version %s stopped'  %(self.addonname, self.addonversion), xbmc.LOGNOTICE)
        
    def check_skin_version(self):
        '''check if skin changed'''
        try:
            skin = xbmc.getSkinDir()
            skin_addon = xbmcaddon.Addon(id=skin)
            skin_label = skin_addon.getAddonInfo('name').decode("utf-8")
            skin_version = skin_addon.getAddonInfo('version').decode("utf-8")
            del skin_addon
            if self.last_skin != skin_label + skin_version:
                #auto correct skin settings
                self.last_skin = skin_label + skin_version
                self.win.setProperty("SkinHelper.skinTitle", "%s - %s: %s" 
                    %(skin_label, xbmc.getLocalizedString(19114),skin_version))
                self.win.setProperty("SkinHelper.skin_version", "%s: %s" 
                    %(xbmc.getLocalizedString(19114),skin_version))
                self.win.setProperty("SkinHelper.Version", self.addonversion.replace(".",""))
                SkinSettings().correct_skin_settings()
        except Exception as exc:
            log_exception(__name__,exc)
