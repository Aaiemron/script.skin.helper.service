from Utils import *

      
def musicSearch():
    xbmc.executebuiltin( "ActivateWindow(MusicLibrary)" )
    xbmc.executebuiltin( "SendClick(8)" )

def addShortcutWorkAround():
    xbmc.executebuiltin( "Dialog.Close(busydialog)" )
    xbmc.executebuiltin('SendClick(301)')
    
    count = 0
    #wait for the empy item is focused
    while (count != 60 and xbmc.getCondVisibility("Window.IsActive(script-skinshortcuts.xml)")):
        if not xbmc.getCondVisibility("StringCompare(Container(211).ListItem.Property(path), noop)"):
            xbmc.sleep(100)
            count += 1
        else:
            break
        
    if xbmc.getCondVisibility("StringCompare(Container(211).ListItem.Property(path), noop) + Window.IsActive(script-skinshortcuts.xml)"):
        xbmc.executebuiltin('SendClick(401)')
                    
def selectOverlayTexture():
    overlaysList = []
    overlaysList.append("Custom Overlay Image")
    dirs, files = xbmcvfs.listdir("special://skin/extras/bgoverlays/")
    for file in files:
        if file.endswith(".png"):
            label = file.replace(".png","")
            overlaysList.append(label)
    
    overlaysList.append("None")
    
    dialog = xbmcgui.Dialog()
    ret = dialog.select(ADDON.getLocalizedString(32015), overlaysList)
    if ret == 0:
        dialog = xbmcgui.Dialog()
        custom_texture = dialog.browse( 2 , ADDON.getLocalizedString(32016), 'files')
        if custom_texture:
            xbmc.executebuiltin("Skin.SetString(BackgroundOverlayTexture,Custom)")
            xbmc.executebuiltin("Skin.SetString(CustomBackgroundOverlayTexture,%s)" % custom_texture)
    else:
        xbmc.executebuiltin("Skin.SetString(BackgroundOverlayTexture,%s)" % overlaysList[ret])
        xbmc.executebuiltin("Skin.Reset(CustomBackgroundOverlayTexture)")

def selectBusyTexture():
    
    import Dialogs as dialogs
    spinnersList = []
    
    currentSpinnerTexture = xbmc.getInfoLabel("Skin.String(SkinHelper.SpinnerTexture)")
    
    listitem = xbmcgui.ListItem(label="None")
    listitem.setProperty("icon","None")
    spinnersList.append(listitem)
    
    listitem = xbmcgui.ListItem(label=ADDON.getLocalizedString(32052))
    listitem.setProperty("icon","")
    spinnersList.append(listitem)
    
    listitem = xbmcgui.ListItem(label=ADDON.getLocalizedString(32053))
    listitem.setProperty("icon","")
    spinnersList.append(listitem)
    
    path = "special://skin/extras/busy_spinners/"
    if xbmcvfs.exists(path):
        dirs, files = xbmcvfs.listdir(path)
        
        for dir in dirs:
            listitem = xbmcgui.ListItem(label=dir)
            listitem.setProperty("icon",path + dir)
            spinnersList.append(listitem)
        
        for file in files:
            if file.endswith(".gif"):
                label = file.replace(".gif","")
                listitem = xbmcgui.ListItem(label=label)
                listitem.setProperty("icon",path + file)
                spinnersList.append(listitem)

    w = dialogs.DialogSelectBig( "DialogSelect.xml", ADDON_PATH, listing=spinnersList, windowtitle=ADDON.getLocalizedString(32051),multiselect=False )
    
    count = 0
    for li in spinnersList:
        if li.getLabel() == currentSpinnerTexture:
            w.autoFocusId = count
        count += 1
         
    w.doModal()
    selectedItem = w.result
    del w
    
    if selectedItem == -1:
        return
    
    if selectedItem == 1:
        dialog = xbmcgui.Dialog()
        custom_texture = dialog.browse( 2 , ADDON.getLocalizedString(32052), 'files', mask='.gif')
        if custom_texture:
            xbmc.executebuiltin("Skin.SetString(SkinHelper.SpinnerTexture,%s)" %spinnersList[selectedItem].getLabel())
            xbmc.executebuiltin("Skin.SetString(SkinHelper.SpinnerTexturePath,%s)" % custom_texture)
    elif selectedItem == 2:
        dialog = xbmcgui.Dialog()
        custom_texture = dialog.browse( 0 , ADDON.getLocalizedString(32053), 'files')
        if custom_texture:
            xbmc.executebuiltin("Skin.SetString(SkinHelper.SpinnerTexture,%s)" %spinnersList[selectedItem].getLabel())
            xbmc.executebuiltin("Skin.SetString(SkinHelper.SpinnerTexturePath,%s)" % custom_texture)
    else:
        xbmc.executebuiltin("Skin.SetString(SkinHelper.SpinnerTexture,%s)" %spinnersList[selectedItem].getLabel())
        xbmc.executebuiltin("Skin.SetString(SkinHelper.SpinnerTexturePath,%s)" % spinnersList[selectedItem].getProperty("icon"))
                
def enableViews():
    import Dialogs as dialogs
    
    allViews = []   
    views_file = xbmc.translatePath( 'special://skin/extras/views.xml' ).decode("utf-8")
    if xbmcvfs.exists( views_file ):
        doc = parse( views_file )
        listing = doc.documentElement.getElementsByTagName( 'view' )
        for count, view in enumerate(listing):
            id = view.attributes[ 'value' ].nodeValue
            label = xbmc.getLocalizedString(int(view.attributes[ 'languageid' ].nodeValue)) + " (" + str(id) + ")"
            type = view.attributes[ 'type' ].nodeValue
            listitem = xbmcgui.ListItem(label=label)
            listitem.setProperty("id",id)
            if not xbmc.getCondVisibility("Skin.HasSetting(SkinHelper.View.Disabled.%s)" %id):
                listitem.select(selected=True)
            allViews.append(listitem)
    
    w = dialogs.DialogSelectSmall( "DialogSelect.xml", ADDON_PATH, listing=allViews, windowtitle=ADDON.getLocalizedString(32017),multiselect=True )
    w.doModal()
    
    selectedItems = w.result
    if selectedItems != -1:
        itemcount = len(allViews) -1
        while (itemcount != -1):
            viewid = allViews[itemcount].getProperty("id")
            if itemcount in selectedItems:
                #view is enabled
                xbmc.executebuiltin("Skin.Reset(SkinHelper.View.Disabled.%s)" %viewid)
            else:
                #view is disabled
                xbmc.executebuiltin("Skin.SetBool(SkinHelper.View.Disabled.%s)" %viewid)
            itemcount -= 1    
    del w        

def setForcedView(contenttype):
    currentView = xbmc.getInfoLabel("Skin.String(SkinHelper.ForcedViews.%s)" %contenttype)
    if not currentView:
        currentView = "0"
    selectedItem = selectView(contenttype, currentView, True, True)
    
    if selectedItem != -1 and selectedItem != None:
        xbmc.executebuiltin("Skin.SetString(SkinHelper.ForcedViews.%s,%s)" %(contenttype, selectedItem))
    
def setView():
    #sets the selected viewmode for the container
    import Dialogs as dialogs
    
    #get current content type
    contenttype = getCurrentContentType()
        
    currentView = xbmc.getInfoLabel("Container.Viewmode").decode("utf-8")
    selectedItem = selectView(contenttype, currentView)
    currentForcedView = xbmc.getInfoLabel("Skin.String(SkinHelper.ForcedViews.%s)" %contenttype)
    
    #also store forced view    
    if contenttype and currentForcedView and currentForcedView != "None" and xbmc.getCondVisibility("Skin.HasSetting(SkinHelper.ForcedViews.Enabled)"):
        xbmc.executebuiltin("Skin.SetString(SkinHelper.ForcedViews.%s,%s)" %(contenttype, selectedItem))
        WINDOW.setProperty("SkinHelper.ForcedView",selectedItem)
        if not xbmc.getCondVisibility("Control.HasFocus(%s)" %currentForcedView):
            xbmc.sleep(100)
            xbmc.executebuiltin("Container.SetViewMode(%s)" %selectedItem)
            xbmc.executebuiltin("SetFocus(%s)" %selectedItem)
    else:
        WINDOW.clearProperty("SkinHelper.ForcedView")
    
    #set view
    if selectedItem != -1 and selectedItem != None:
        xbmc.executebuiltin("Container.SetViewMode(%s)" %selectedItem)
    
def searchYouTube(title,windowHeader=""):
    xbmc.executebuiltin( "ActivateWindow(busydialog)" )
    import Dialogs as dialogs
    libPath = "plugin://plugin.video.youtube/kodion/search/query/?q=" + title
    media_array = None
    allResults = []
    media_array = getJSON('Files.GetDirectory','{ "properties": ["title","art","plot"], "directory": "%s", "media": "files", "limits": {"end":25} }' %libPath)
    for media in media_array:
        
        if not media["filetype"] == "directory":
            label = media["label"]
            label2 = media["plot"]
            image = None
            if media.has_key('art'):
                if media['art'].has_key('thumb'):
                    image = (media['art']['thumb'])
                    
            path = media["file"]
            listitem = xbmcgui.ListItem(label=label, label2=label2, iconImage=image)
            listitem.setProperty("path",path)
            listitem.setProperty("icon",image)
            allResults.append(listitem)
    xbmc.executebuiltin( "Dialog.Close(busydialog)" )
    w = dialogs.DialogSelectBig( "DialogSelect.xml", ADDON_PATH, listing=allResults, windowtitle=windowHeader,multiselect=False )
    w.doModal()
    selectedItem = w.result
    del w
    if selectedItem != -1:
        path = allResults[selectedItem].getProperty("path")
        xbmc.executebuiltin("PlayMedia(%s)" %path)
            
def selectView(contenttype="other", currentView=None, displayNone=False, displayViewId=False):
    import Dialogs as dialogs
    currentViewSelectId = None

    allViews = []
    if displayNone:
        listitem = xbmcgui.ListItem(label="None")
        listitem.setProperty("id","None")
        allViews.append(listitem)
        
    views_file = xbmc.translatePath( 'special://skin/extras/views.xml' ).decode("utf-8")
    if xbmcvfs.exists( views_file ):
        doc = parse( views_file )
        listing = doc.documentElement.getElementsByTagName( 'view' )
        itemcount = 0
        for count, view in enumerate(listing):
            label = xbmc.getLocalizedString(int(view.attributes[ 'languageid' ].nodeValue)).encode("utf-8").decode("utf-8")
            id = view.attributes[ 'value' ].nodeValue
            if displayViewId:
                label = label + " (" + str(id) + ")"
            type = view.attributes[ 'type' ].nodeValue.lower()
            if label.lower() == currentView.lower() or id == currentView:
                currentViewSelectId = itemcount
                if displayNone == True:
                    currentViewSelectId += 1
            if (type == "all" or contenttype.lower() in type) and not xbmc.getCondVisibility("Skin.HasSetting(SkinHelper.View.Disabled.%s)" %id):
                image = "special://skin/extras/viewthumbs/%s.jpg" %id
                listitem = xbmcgui.ListItem(label=label, iconImage=image)
                listitem.setProperty("id",id)
                listitem.setProperty("icon",image)
                allViews.append(listitem)
                itemcount +=1
    w = dialogs.DialogSelectBig( "DialogSelect.xml", ADDON_PATH, listing=allViews, windowtitle=ADDON.getLocalizedString(32054),multiselect=False )
    w.autoFocusId = currentViewSelectId
    w.doModal()
    selectedItem = w.result
    del w
    if selectedItem != -1:
        id = allViews[selectedItem].getProperty("id")
        return id

def waitForSkinShortcutsWindow():
    #wait untill skinshortcuts is active window (because of any animations that may have been applied)
    for i in range(40):
        if not (xbmc.getCondVisibility("Window.IsActive(DialogSelect.xml) | Window.IsActive(script-skin_helper_service-ColorPicker.xml) | Window.IsActive(DialogKeyboard.xml)")):
            break
        else: xbmc.sleep(100)
        
def setSkinShortCutsProperty(setting="",windowHeader="",propertyName=""):
    curValue = xbmc.getInfoLabel("$INFO[Container(211).ListItem.Property(%s)]" %propertyName).decode("utf-8")
    if not curValue: curValue = "None"
    if setting:
        (value, label) = setSkinSetting(setting, windowHeader, None, curValue)
    else:
        value = xbmcgui.Dialog().input(windowHeader, curValue, type=xbmcgui.INPUT_ALPHANUM).decode("utf-8")
    if value:
        waitForSkinShortcutsWindow()
        xbmc.executebuiltin("SetProperty(customProperty,%s)" %propertyName.encode("utf-8"))
        xbmc.executebuiltin("SetProperty(customValue,%s)" %value.encode("utf-8"))
        xbmc.executebuiltin("SendClick(404)")
        if setting:
            xbmc.sleep(250)
            xbmc.executebuiltin("SetProperty(customProperty,%s.name)" %propertyName.encode("utf-8"))
            xbmc.executebuiltin("SetProperty(customValue,%s)" %label.encode("utf-8"))
            xbmc.executebuiltin("SendClick(404)")
        
def setSkinSetting(setting="", windowHeader="", sublevel="", valueOnly=""):
    import Dialogs as dialogs
    curValue = xbmc.getInfoLabel("Skin.String(%s)" %setting).decode("utf-8")
    if valueOnly: curValue = valueOnly
    curValueLabel = xbmc.getInfoLabel("Skin.String(%s.label)" %setting).decode("utf-8")
    useRichLayout = False
    selectId = 0
    itemcount = 0
    
    allValues = []        
    settings_file = xbmc.translatePath( 'special://skin/extras/skinsettings.xml' ).decode("utf-8")
    if xbmcvfs.exists( settings_file ):
        doc = parse( settings_file )
        listing = doc.documentElement.getElementsByTagName( 'setting' )
        if sublevel:
            listitem = xbmcgui.ListItem(label="..", iconImage="DefaultFolderBack.png")
            listitem.setProperty("icon","DefaultFolderBack.png")
            listitem.setProperty("value","||BACK||")
            allValues.append(listitem)
        for count, item in enumerate(listing):
            id = item.attributes[ 'id' ].nodeValue
            if id.startswith("$"): id = xbmc.getInfoLabel(id).decode("utf-8")
            label = xbmc.getInfoLabel(item.attributes[ 'label' ].nodeValue).decode("utf-8")
            if (not sublevel and id.lower() == setting.lower()) or (sublevel and sublevel.lower() == id.lower()):
                value = item.attributes[ 'value' ].nodeValue
                condition = item.attributes[ 'condition' ].nodeValue
                icon = item.attributes[ 'icon' ].nodeValue
                description = item.attributes[ 'description' ].nodeValue
                description = xbmc.getInfoLabel(description.encode("utf-8"))
                if condition and not xbmc.getCondVisibility(condition): continue
                if icon: useRichLayout = True
                if icon and icon.startswith("$"): icon = xbmc.getInfoLabel(icon)
                if curValue and (curValue.lower() == value.lower() or label.lower() == curValueLabel.lower()): selectId = itemcount
                listitem = xbmcgui.ListItem(label=label, iconImage=icon)
                listitem.setProperty("value",value)
                listitem.setProperty("icon",icon)
                listitem.setProperty("description",description)
                listitem.setLabel2(description)
                #additional onselect actions
                additionalactions = []
                for action in item.getElementsByTagName( 'onselect' ):
                    condition = action.attributes[ 'condition' ].nodeValue
                    if condition and not xbmc.getCondVisibility(condition): continue
                    command = action.firstChild.nodeValue
                    if "$" in command: command = xbmc.getInfoLabel(command)
                    additionalactions.append(command)
                listitem.setProperty("additionalactions"," || ".join(additionalactions))
                allValues.append(listitem)
                itemcount +=1
        if useRichLayout:
            w = dialogs.DialogSelectBig( "DialogSelect.xml", ADDON_PATH, listing=allValues, windowtitle=windowHeader,multiselect=False )
        else:
            w = dialogs.DialogSelectSmall( "DialogSelect.xml", ADDON_PATH, listing=allValues, windowtitle=windowHeader,multiselect=False )
        if selectId > 0 and sublevel: selectId += 1
        w.autoFocusId = selectId
        w.doModal()
        selectedItem = w.result
        del w
        if selectedItem != -1:
            value = try_decode( allValues[selectedItem].getProperty("value") )
            label = try_decode( allValues[selectedItem].getLabel() )
            description = allValues[selectedItem].getProperty("description")
            if value.startswith("||SUBLEVEL||"):
                sublevel = value.replace("||SUBLEVEL||","")
                setSkinSetting(setting, windowHeader, sublevel)
            elif value == "||BACK||":
                setSkinSetting(setting, windowHeader)
            else:
                if value == "||BROWSEIMAGE||":
                    if xbmcgui.Dialog().yesno( label, ADDON.getLocalizedString(32064), yeslabel=ADDON.getLocalizedString(32065), nolabel=ADDON.getLocalizedString(32066) ):
                        value = xbmcgui.Dialog().browse( 2 , label, 'files')
                    else: value = xbmcgui.Dialog().browse( 0 , ADDON.getLocalizedString(32067), 'files')
                if value:
                    if valueOnly: 
                        return (value,label)
                    else:
                        xbmc.executebuiltin("Skin.SetString(%s,%s)" %(setting.encode("utf-8"),value.encode("utf-8")))
                        xbmc.executebuiltin("Skin.SetString(%s.label,%s)" %(setting.encode("utf-8"),label.encode("utf-8")))
                        additionalactions = allValues[selectedItem].getProperty("additionalactions").split(" || ")
                        for action in additionalactions:
                            xbmc.executebuiltin(action)
        else: return (None,None)
                    
def toggleKodiSetting(settingname):
    #toggle kodi setting
    curValue = xbmc.getCondVisibility("system.getbool(%s)"%settingname)
    if curValue == True:
        newValue = "false"
    else:
        newValue = "true"
    xbmc.executeJSONRPC('{"jsonrpc":"2.0", "id":1, "method":"Settings.SetSettingValue","params":{"setting":"%s","value":%s}}' %(settingname,newValue))
     
def show_splash(file,duration=5):
    logMsg("show_splash --> " + file)
    if file.lower().endswith("jpg") or file.lower().endswith("gif") or file.lower().endswith("png") or file.lower().endswith("tiff"):
        #this is an image file
        WINDOW.setProperty("SkinHelper.SplashScreen",file)
        #for images we just wait for X seconds to close the splash again
        start_time = time.time()
        while(time.time() - start_time <= duration):
            xbmc.sleep(500)
    else:
        #for video or audio we have to wait for the player to finish...
        xbmc.Player().play(file,windowed=True)
        xbmc.sleep(500)
        while xbmc.getCondVisibility("Player.HasMedia"):
            xbmc.sleep(150)

    #replace startup window with home
    startupwindow = xbmc.getInfoLabel("$INFO[System.StartupWindow]")
    xbmc.executebuiltin("ReplaceWindow(%s)" %startupwindow)
    
    #startup playlist (if any)
    AutoStartPlayList = xbmc.getInfoLabel("$ESCINFO[Skin.String(AutoStartPlayList)]")
    if AutoStartPlayList: xbmc.executebuiltin("PlayMedia(%s)" %AutoStartPlayList)