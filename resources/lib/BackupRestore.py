import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import xbmcplugin
import os
import json
import shutil
import hashlib
import urllib
import time
import zipfile
import shutil
from Utils import *
import random

doDebugLog = False


def backup():
    try:
        #get backup destination
        backup_path = None
        backup_path = get_browse_dialog(dlg_type=3,heading=ADDON.getLocalizedString(32018))
        if backup_path != None and backup_path != "":
        
            from xml.dom.minidom import parse
            guisettings_path = xbmc.translatePath('special://profile/guisettings.xml').decode("utf-8")
            if xbmcvfs.exists(guisettings_path):
                logMsg("guisettings.xml found")
                doc = parse(guisettings_path)
                skinsettings = doc.documentElement.getElementsByTagName('setting')
                newlist = []
                for count, skinsetting in enumerate(skinsettings):
                    if skinsetting.childNodes:
                        value = skinsetting.childNodes[0].nodeValue
                    else:
                        value = ""
                    if skinsetting.attributes['name'].nodeValue.startswith(xbmc.getSkinDir()):
                        name = skinsetting.attributes['name'].nodeValue
                        name = name.replace(xbmc.getSkinDir(),"")
                        newlist.append((skinsetting.attributes['type'].nodeValue, name, value))

                if not xbmcvfs.exists(backup_path):
                    xbmcvfs.mkdir(backup_path)
                
                #create temp path
                temp_path = xbmc.translatePath('special://temp/skinbackup/').decode("utf-8")
                if xbmcvfs.exists(temp_path):
                    shutil.rmtree(temp_path)
                xbmcvfs.mkdir(temp_path)
                    
                skinshortcuts_path = temp_path + "skinshortcuts/"
                if not xbmcvfs.exists(skinshortcuts_path):
                    xbmcvfs.mkdir(skinshortcuts_path)
                    
                #get skinshortcuts preferences
                skinshortcuts_path_source = xbmc.translatePath('special://profile/addon_data/script.skinshortcuts/').decode("utf-8")
                logMsg(skinshortcuts_path_source)
                if xbmcvfs.exists(skinshortcuts_path_source):
                    dirs, files = xbmcvfs.listdir(skinshortcuts_path_source)
                    for file in files:
                        if ".xml" in file:
                            sourcefile = skinshortcuts_path_source + file
                            destfile = skinshortcuts_path + file
                            logMsg("source --> " + sourcefile)
                            logMsg("destination --> " + destfile)
                            xbmcvfs.copy(sourcefile,destfile)    
                
                #save guisettings
                text_file_path = os.path.join(temp_path, "guisettings.txt")
                text_file = xbmcvfs.File(text_file_path, "w")
                json.dump(newlist, text_file)
                text_file.close()
                
                from datetime import datetime
                i = datetime.now()
                
                #zip the backup
                backup_name = xbmc.getSkinDir().replace("skin.","") + "_SKIN_BACKUP_" + i.strftime('%Y%m%d-%H%M')
                zip_temp = xbmc.translatePath('special://temp/' + backup_name)
                zip_final = backup_path + backup_name + ".zip"
                zip(temp_path,zip_temp)
                
                #copy to final location
                xbmcvfs.copy(zip_temp + ".zip", zip_final)
                
                #cleanup temp
                shutil.rmtree(temp_path)
                xbmcvfs.delete(zip_temp + ".zip")
                
                xbmcgui.Dialog().ok(ADDON.getLocalizedString(32028), ADDON.getLocalizedString(32029))
                
            else:
                xbmcgui.Dialog().ok(ADDON.getLocalizedString(32028), ADDON.getLocalizedString(32030))
                logMsg("guisettings.xml not found")
    
    except Exception as e:
        xbmcgui.Dialog().ok(ADDON.getLocalizedString(32028), ADDON.getLocalizedString(32030))
        logMsg("ERROR while creating backup ! --> " + str(e), 0)


        
def restore():
    
    try:
        zip_path = None
        zip_path = get_browse_dialog(dlg_type=1,heading=ADDON.getLocalizedString(32031),mask=".zip")
        
        if zip_path != None and zip_path != "":
            logMsg("zip_path " + zip_path)
            progressDialog = xbmcgui.DialogProgress(ADDON.getLocalizedString(32032))
            progressDialog.create(ADDON.getLocalizedString(32032))
            progressDialog.update(0, "unpacking backup...")
            
            #create temp path
            temp_path = xbmc.translatePath('special://temp/skinbackup/').decode("utf-8")
            if xbmcvfs.exists(temp_path):
                shutil.rmtree(temp_path)
            xbmcvfs.mkdir(temp_path)
            
            #unzip to temp
            if "\\" in zip_path:
                delim = "\\"
            else:
                delim = "/"
            
            zip_temp = xbmc.translatePath('special://temp/' + zip_path.split(delim)[-1])
            xbmcvfs.copy(zip_path,zip_temp)
            zfile = zipfile.ZipFile(zip_temp)
            zfile.extractall(temp_path)
            zfile.close()
            xbmcvfs.delete(zip_temp)
            
            #copy skinshortcuts preferences
            skinshortcuts_path_source = None
            if xbmcvfs.exists(temp_path + "skinshortcuts/"):
                
                skinshortcuts_path_source = temp_path + "skinshortcuts/"
                skinshortcuts_path_dest = xbmc.translatePath('special://profile/addon_data/script.skinshortcuts/').decode("utf-8")
                
                if xbmcvfs.exists(skinshortcuts_path_dest):
                    shutil.rmtree(skinshortcuts_path_dest)
                xbmcvfs.mkdir(skinshortcuts_path_dest)
            
                dirs, files = xbmcvfs.listdir(skinshortcuts_path_source)
                for file in files:
                    if ".xml" in file:
                        sourcefile = skinshortcuts_path_source + file
                        destfile = skinshortcuts_path_dest + file
                        logMsg("source --> " + sourcefile)
                        logMsg("destination --> " + destfile)
                        xbmcvfs.copy(sourcefile,destfile)    
            
            #read guisettings
            text_file_path = os.path.join(temp_path, "guisettings.txt")
            f = open(text_file_path,"r")
            importstring = json.load(f)
            f.close()
            
            xbmc.sleep(200)
            for count, skinsetting in enumerate(importstring):
                if progressDialog.iscanceled():
                    return

                progressDialog.update((count * 100) / len(importstring), ADDON.getLocalizedString(32033) + ' %s' % skinsetting[1])
                
                #some legacy...
                setting = skinsetting[1].replace("TITANSKIN.", "")
                
                if skinsetting[0] == "string":
                    if skinsetting[2] is not "":
                        xbmc.executebuiltin("Skin.SetString(%s,%s)" % (setting, skinsetting[2]))
                    else:
                        xbmc.executebuiltin("Skin.Reset(%s)" % setting)
                elif skinsetting[0] == "bool":
                    if skinsetting[2] == "true":
                        xbmc.executebuiltin("Skin.SetBool(%s)" % setting)
                    else:
                        xbmc.executebuiltin("Skin.Reset(%s)" % setting)
                xbmc.sleep(30)
            
            #cleanup temp
            xbmc.sleep(500)
            shutil.rmtree(temp_path)
            xbmcgui.Dialog().ok(ADDON.getLocalizedString(32032), ADDON.getLocalizedString(32034))
    
    except Exception as e:
        xbmcgui.Dialog().ok(ADDON.getLocalizedString(32032), ADDON.getLocalizedString(32035))
        logMsg("ERROR while restoring backup ! --> " + str(e), 0)



def zip(src, dst):
    zf = zipfile.ZipFile("%s.zip" % (dst), "w", zipfile.ZIP_DEFLATED)
    abs_src = os.path.abspath(src)
    for dirname, subdirs, files in os.walk(src):
        for filename in files:
            absname = os.path.abspath(os.path.join(dirname, filename))
            arcname = absname[len(abs_src) + 1:]
            logMsg('zipping %s as %s' % (os.path.join(dirname, filename),
                                        arcname))
            zf.write(absname, arcname)
    zf.close()
       

def reset():
    yeslabel=xbmc.getLocalizedString(107)
    nolabel=xbmc.getLocalizedString(106)
    dialog = xbmcgui.Dialog()
    
    ret = dialog.yesno(heading=ADDON.getLocalizedString(32036), line1=ADDON.getLocalizedString(32037), nolabel=nolabel, yeslabel=yeslabel)
    if ret:
        xbmc.executebuiltin("RunScript(script.skinshortcuts,type=resetall&warning=false)")
        xbmc.sleep(250)
        xbmc.executebuiltin("Skin.ResetSettings")
        xbmc.sleep(250)
        xbmc.executebuiltin("ReloadSkin")
       
        
def save_to_file(content, filename, path=""):
    if path == "":
        text_file_path = get_browse_dialog() + filename + ".txt"
    else:
        if not xbmcvfs.exists(path):
            xbmcvfs.mkdir(path)
        text_file_path = os.path.join(path, filename + ".txt")
    logMsg("save to textfile: " + text_file_path)
    text_file = xbmcvfs.File(text_file_path, "w")
    json.dump(content, text_file)
    text_file.close()
    return True

def read_from_file(path=""):
    if path == "":
        path = get_browse_dialog(dlg_type=1)
    if xbmcvfs.exists(path):
        f = open(path)
        fc = json.load(f)
        logMsg("loaded textfile " + path)
        return fc
    else:
        return False

        
def get_browse_dialog(default="protocol://", heading="Browse", dlg_type=3, shares="files", mask="", use_thumbs=False, treat_as_folder=False):
    dialog = xbmcgui.Dialog()
    value = dialog.browse(dlg_type, heading, shares, mask, use_thumbs, treat_as_folder, default)
    return value