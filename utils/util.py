import os
import re
import socket
import subprocess
import sys
import time
import unicodedata
from typing import Optional

import wx


def call_after(func):
    """(装饰器)使用wx.CallAfter()包裹GUI方法，使其可在子线程中被正常地调用"""
    def wrapper(*args,**kargs):
        return wx.CallAfter(func,*args,**kargs)
    return wrapper

def isEmpty(string) -> bool:
    """判断字符串是否为空"""
    return string is None or string.strip()==""

def wxCopy(string):
    """将文本内容粘贴到剪切板"""
    text_data=wx.TextDataObject(string)
    if wx.TheClipboard.Open():
        wx.TheClipboard.SetData(text_data)
        wx.TheClipboard.Close()

def wxPaste() -> Optional[str]:
    """从剪切板获取文本内容"""
    text_data=wx.TextDataObject()
    if wx.TheClipboard.Open():
        success = wx.TheClipboard.GetData(text_data)
        wx.TheClipboard.Close()
    return text_data.GetText() if success else None

def getRgbColor(num:int) -> wx.Colour:
    """根据整数生成对应的wxUI颜色"""
    num=int(num)
    r=num//65536
    g=(num-65536*r)//256
    b=num-65536*r-256*g
    return wx.Colour(r,g,b)

def getTime(ts=None,ms=False,fmt="%H:%M:%S") -> str:
    """将时间戳ts按fmt格式转化为字符串，ms表示ts是否为毫秒级时间戳"""
    if ts is None:  ts=time.time()
    elif ms:        ts=ts/1000
    return time.strftime(fmt,time.localtime(ts))

def strToTs(string,fmt="%y-%m-%d %H:%M:%S") -> int:
    """将字符串string按fmt格式转化为秒级时间戳"""
    return int(time.mktime(time.strptime(string,fmt)))

def getTimeLineStr(seconds,style=0) -> str:
    """将秒数转化为时钟格式
    
    : style=0 -> MM:SS.X　　style!=0 -> MM:SS"""
    min=seconds//60
    sec=seconds-60*min
    fmt="%02d:%04.1f" if style==0 else "%2d:%02d"
    return fmt%(min,sec)

@call_after
def UIChange(obj:wx.Control,label=None,color:Optional[wx.Colour]=None,enabled=None):
    """设置wxUI部件的显示文本、前景色、是否启用"""
    try:
        if not obj: return # wx.Window部件在销毁时为False而不是None
        if color is not None:   obj.SetForegroundColour(color)
        if label is not None:   obj.SetLabel(label)
        if enabled is not None: obj.Enable(enabled)
    except RuntimeError: pass

def setFont(obj:wx.Control,size,bold=False,name=None):
    """设置wxUI部件的字体大小、是否加粗、字体名称"""
    weight=wx.FONTWEIGHT_BOLD if bold else wx.FONTWEIGHT_NORMAL
    try:
        if not obj: return
        if name is None:
            obj.SetFont(wx.Font(size,wx.FONTFAMILY_DEFAULT,wx.FONTSTYLE_NORMAL,weight))
        else:
            obj.SetFont(wx.Font(size,wx.FONTFAMILY_DEFAULT,wx.FONTSTYLE_NORMAL,weight,faceName=name))
    except RuntimeError: pass

def getNodeValue(parentNode,childName) -> str:
    """获取DOM父节点parentNode下名为childName的子节点的值"""
    try:    return parentNode.getElementsByTagName(childName)[0].childNodes[0].nodeValue.strip()
    except IndexError:  return ""

def editDictItem(_dict:dict,oldKey,newKey,newValue=None,setValueToNone=False) -> dict:
    """在不改变键的顺序的情况下修改字典键值对中的键，返回修改后的新字典"""
    keys,values=list(_dict.keys()),list(_dict.values())
    for i,_key in enumerate(keys):
        if _key==oldKey:  break
    else:
        _dict[newKey]=newValue
        return _dict
    keys[i]=newKey 
    values[i]=None if setValueToNone else (values[i] if newValue is None else newValue)
    return dict(zip(keys,values))

def splitTnL(lrc_line:str) -> list:
    """对lrc格式的歌词行进行处理，分离时间轴与歌词内容

    :示例输入："[01:35.49]壊れていたのは世界ではなくて"
    :示例输出：[["01:35", 95.49, "壊れていたのは世界ではなくて", "[01:35.49]"]]
    :注：可能存在一句歌词对应多个时轴的情况，故采用二维列表输出
    """
    fs,parts=[],lrc_line.split("]")
    if len(parts)<=1:   return []
    content = parts[-1].strip()
    for tl in parts[0:-1]:
        mo=re.match(r"\[(\d+):(\d+)(\.\d*)?",tl)
        if mo is None:  continue
        t_min,t_sec = int(mo.group(1)),int(mo.group(2))
        t_ms=0 if mo.group(3) is None else eval(mo.group(3))
        secnum = 60*t_min+t_sec+t_ms
        secfmt = "%2d:%02d"%(t_min,t_sec)
        secOrigin = mo.group()+"]"
        fs.append([secfmt, secnum, content, secOrigin])
    return fs

def charType(char,group=False) -> str:
    """获取字符类型(不考虑全角英文/数字)
    分组时的返回值： AN:字母/数字 CJ:汉字/日文假名 O:其他
    不分组时的返回值： A:字母 C:汉字 J:日文假名 N:数字 O:其他"""
    result="O"
    if "\u4E00"<=char<="\u9FA5": result="C"
    elif "\u0041"<=char<="\u005A" or "\u0061"<=char<="\u007A": result="A"
    elif "\u0030"<=char<="\u0039": result="N"
    elif "\u3040"<=char<="\u309F" or "\u30A0"<=char<="\u30FF": result="J"
    if group:
        if result in "AN": return "AN"
        if result in "CJ": return "CJ"
    return result

def showInfoDialog(content="",title=""):
    """弹出确认对话框并返回False"""
    dlg = wx.MessageDialog(None, content, title, wx.OK)
    dlg.ShowModal()
    dlg.Destroy()
    return False

def bindHint(obj:wx.Control,hint:str):
    """为wx控件绑定事件，点击后弹出帮助窗口"""
    if not obj: return
    obj.Bind(wx.EVT_LEFT_DOWN, lambda event: showInfoDialog(hint,"帮助"))
    obj.SetForegroundColour("DARK TURQUOISE")
    obj.SetCursor(wx.Cursor(wx.CURSOR_HAND))

def logDebug(msg:str):
    """输出调试日志"""
    try:
        path="logs/debug/DEBUG_%s.log"%getTime(fmt="%y-%m")
        with open(path,"a",encoding="utf-8") as f:
            f.write("%s｜%s\n"%(getTime(fmt="%m-%d %H:%M:%S"),msg))
    except: pass

def transformToRegex(string,join="") -> str:
    """将普通字符串string转换为正则字符串，各字符之间以join来连接"""
    string = re.sub(r"\s+", "", string)
    pattern = re.sub(r"([+.*?^$|(){}\[\]\\])",r"\\\1","∷".join(string))
    return pattern.replace("∷", join)

def searchByOneCharTag(char, dictionary, split_tag_by=";") -> list:
    """
    根据单个字符char对dictionary内每个值中的所有标签进行精确查询，返回满足匹配条件的所有键
    e.g. char="m" dictionary={"k1":"a;b;c","k2":"L;M;N","k3":"money;boom","k4":"m"} return ["k2","k4"]
    """
    res = []
    for key in dictionary.keys():
        tags = dictionary[key].split(split_tag_by)
        for tag in tags:
            if tag.lower().strip()==char.lower():
                res.append(key)
                break
    return res

def searchByTag(keyword, dictionary, split_tag_by=";") -> list:
    """
    根据字符串word对dictionary内每个值中的所有标签进行模糊查询，返回满足匹配条件的所有键
    e.g. word="abc" dictionary={"k1":"cba;bca","k2":"dabcd","k3":"adbdc;d;e"} return ["k3","k2"]
    """
    suggestions = []
    pattern = "(?i)"+transformToRegex(keyword,".*?")
    regex = re.compile(pattern)
    for key in dictionary.keys():
        sug = []
        tags = dictionary[key].split(split_tag_by)
        for tag in tags:
            match = regex.search(tag.lstrip())
            if match:
                sug.append((len(match.group()), match.start()))
        if len(sug) > 0:
            sug = sorted(sug)
            suggestions.append((sug[0][0], sug[0][1], key))
    return [x for _, _, x in sorted(suggestions)]

def getStrWidth(string) -> int:
    """获取字符串string的大致显示宽度，返回值以半角字符的长度为单位"""
    width=0
    for char in string:
        if unicodedata.east_asian_width(char) in ["W","F"]: width+=2
        else: width+=1
    return width

def key2code(key) -> int:
    """获取按键对应的KeyCode（暂仅支持26个英文字母键和4个方向键）。对于不支持的按键，返回0"""
    if len(key) != 1 :
        return 0
    keycode = ord(key.upper())
    if 65 <= keycode <= 90:
         return keycode
    if 8592 <= keycode <= 8595:
        return (wx.WXK_LEFT,wx.WXK_UP,wx.WXK_RIGHT,wx.WXK_DOWN)[keycode-8592]
    return 0

def code2key(keycode) -> str:
    """将KeyCode表示为对应的按键（暂仅支持26个英文字母键和4个方向键）"""
    _d = {wx.WXK_LEFT: "←", wx.WXK_UP: "↑", wx.WXK_RIGHT: "→", wx.WXK_DOWN: "↓"}
    if keycode in _d.keys():
        return _d[keycode]
    if 65 <= keycode <= 90:
        return chr(keycode)
    return ""

def isPortUsed(ip:str="127.0.0.1", port:int=8080) -> bool:
    """检查端口是否已被占用"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((ip, port))
        s.shutdown(socket.SHUT_RDWR)
        return True
    except: return False
    finally:    s.close()

def updateCsvFile(file_path:str,key_index:int,new_records:dict,max_size:int=1024):
    """更新csv文件的结尾部分（修改原有记录或新增记录）
    
    :param: file_path  CSV文件路径
    :param: key_index  数据项的键值在CSV文件中的列编号
    :param: new_records  待更新项的字典，每项为 键值：数据项整行的文本数据
    :param: max_size  从CSV文件结尾开始，允许向前读取并修改的最大字节数"""
    with open(file_path, "r+b") as f:
        f.seek(0,2)
        read_size = block_size = min(max_size, f.tell())
        f.seek(-block_size,2)
        if block_size==max_size: read_size = block_size-f.read().index(b'\n')-1
        f.seek(-read_size,2)
        content=str(f.read(),encoding="utf-8").strip()
        f.seek(-read_size,2)
        f.truncate()
    old_lines,old_records=[],{}
    if content!="": old_lines=content.strip().split("\n")
    for i,v in enumerate(old_lines):
        line_items=v.strip().split(",")
        if len(line_items)>key_index:
            old_records[line_items[key_index]]=v
        else:   old_records[i]=v
    with open(file_path, "a", encoding="utf-8") as f:
        for k,v in old_records.items():
            if k in new_records.keys():
                f.write(new_records[k].strip()+"\n")
            else: f.write(v.strip()+"\n")
        for k,v in new_records.items():
            if k not in old_records.keys():
                f.write(v.strip()+"\n")

def openFile(path:str, platform="win"):
    """打开文件"""
    try:
        if platform=="win": os.startfile(path)
        else: subprocess.call(["open",path])
    except: raise

def getResourcePath(code_path:str, exe_path:str) -> str:
    '''返回资源绝对路径

    :param: code_path: 在代码层级，资源关于<调用该资源的文件>的相对路径
    :param: exe_path: 打包为可执行文件后，资源关于<程序入口>的相对路径
    '''
    if getattr(sys, 'frozen', False):
        return os.path.join(getattr(sys, '_MEIPASS', None), exe_path) # 打包为可执行文件后会调用
    else:
        return os.path.join(os.path.dirname(__file__), code_path) # 以代码形式运行会调用
