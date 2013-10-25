#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import wx,win32con,win32gui,time,os,re
from lxml import etree
from datetime import datetime,timedelta
reload(sys) 
sys.setdefaultencoding('utf-8')

class Rev_Frame(wx.Frame):
    def __init__(self,parent,id):
        wx.Frame.__init__(self,parent,id,"Timer",size=(358,300))
        panel=wx.Panel(self)

        #倒数时间计时
        self.rm_time=0


        #显示是否在倒计时
        self.notification_bar=wx.StaticText(panel,-1,u"当前没有任何任务",pos=(110,60))

        #显示剩余时间
        self.remaining_time=wx.StaticText(panel,-1,u"",pos=(135,120))

        #显示历史事件
        self.history_bar_text=wx.StaticText(panel,-1,u"历史记录:",pos=(90,180))        
        self.history_bar=wx.StaticText(panel,-1,u"",pos=(150,180))

        #十分钟
        self.choose_min(10)
        self.Bind(wx.EVT_HOTKEY,lambda event:self.choose_evt(event,10),id=self.hotKeyId)
        
        #二十分钟
        self.choose_min(20)
        self.Bind(wx.EVT_HOTKEY,lambda event:self.choose_evt(event,20),id=self.hotKeyId)

        #三十分钟
        self.choose_min(30)
        self.Bind(wx.EVT_HOTKEY,lambda event:self.choose_evt(event,30),id=self.hotKeyId)
        
        #四十分钟
        self.choose_min(40)
        self.Bind(wx.EVT_HOTKEY,lambda event:self.choose_evt(event,40),id=self.hotKeyId)

        #五十分钟
        self.choose_min(50)
        self.Bind(wx.EVT_HOTKEY,lambda event:self.choose_evt(event,50),id=self.hotKeyId)
        
        #六十分钟
        self.choose_min(60)
        self.Bind(wx.EVT_HOTKEY,lambda event:self.choose_evt(event,60),id=self.hotKeyId)

        #任意倒计时开始F7开始（调用start_random_timer函数），F8结束(调用end_random_timer函数)
        self.shift_F7()
        self.Bind(wx.EVT_HOTKEY,self.start_random_timer,id=self.hotKeyId)
        self.shift_F8()
        self.Bind(wx.EVT_HOTKEY,self.end_random_timer,id=self.hotKeyId)

        #时间销毁器（停止此次时间）
        self.shift_F10()
        self.Bind(wx.EVT_HOTKEY,self.cancel_timer,id=self.hotKeyId)  

        #这个倒计时用于判断每隔半小时是否有总倒计时在运行，假如没有则弹出窗口发出提示
        self.check_timer=wx.Timer(self,wx.NewId()) 
        self.check_timer.Start(1000*60*5,oneShot=False)
        self.Bind(wx.EVT_TIMER,self.check_is_running,self.check_timer)

        #这个按钮show_history_button将调用show_history函数,显示一天之内不同的项目干了多少时间
        self.show_history_button=wx.Button(panel,label=u"显示历史",pos=(7,7),size=(60,25))
        self.Bind(wx.EVT_BUTTON,self.show_history,self.show_history_button)




    '''正常倒计时'''
    #按下快捷键，确定要倒计的时间
    def choose_min(self,mins):
        min_dic={10:win32con.VK_F1,20:win32con.VK_F2,30:win32con.VK_F3,40:win32con.VK_F4,50:win32con.VK_F5,60:win32con.VK_F6}#时间选择列表
        self.hotKeyId=mins*10
        self.RegisterHotKey(
            self.hotKeyId,
            win32con.MOD_SHIFT,
            min_dic[mins]           
            )
    #1.开始总倒计时，2.文字显示notification_bar展示总倒计时已经开始，3.窗口min_alert_message弹出显示剩余时间信息并自动消除,4.文字显示notification_bar展示还剩多少时间，
    def choose_evt(self,evt,mins):
        # 开始总倒计时,并记录现在时间(为了在中途中断时间,记录时间所用)
        self.min_timer=wx.Timer(self,1234)
        self.min_timer.Start(mins*1000*60,oneShot=True)   
        #ONLY FOR DEBUG!
        # self.min_timer.Start(4000,oneShot=True)
        self.Bind(wx.EVT_TIMER,lambda event:self.time_up(event,mins),self.min_timer)#绑定时间一到执行的操作
        self.start_time=datetime.now()

        # 2.文字显示notification_bar展示总倒计时已经开始
        message=u" %s minutes 倒计时开始！"%(mins)
        self.notification_bar.SetLabel(message)


        #3.窗口min_alert_message弹出显示剩余时间信息并自动消除
        min_alert_dlg=MessageDialog(message,"min_alert")
        #隔一点五秒就消失
        wx.FutureCall(1500,min_alert_dlg.Destroy)
        min_alert_dlg.ShowModal()


        # 4.文字显示notification_bar展示还剩多少时间，
        self.rm_time=mins
        self.show_timer=wx.Timer(self,wx.NewId())#时间器，每隔一分钟刷新
        self.show_timer.Start(1000*60,oneShot=False)
        self.remaining_time.SetLabel(u"还剩%s minutes"%str(self.rm_time))
        self.Bind(wx.EVT_TIMER,self.count_time,self.show_timer)
    #时间到点后输入做的任务
    def time_up(self,event,mins):
        #1.暂停显示的倒计时,并擦除文字显示remaining_time上展示的剩余时间，notification_bar恢复显示为”当前没有任何任务“
        self.show_timer.Stop()
        self.remaining_time.SetLabel("")
        self.notification_bar.SetLabel(u"当前没有任何任务")

        #2.窗口time_up_dlg弹出说明时间已到，并将信息记录在xml中调用time_log函数
        time_up_dlg=TextEntryDialog(None,u"时间到！",caption=u"时间到！")
        if time_up_dlg.ShowModal()==wx.ID_OK:
            message=unicode(time_up_dlg.GetValue())
            info={"message":message,"mins":mins}#将完成信息和完成的时间放在info上
            self.time_log(info)#将信息记录在xml中


    '''任意倒计时'''
    #从未知时间开始
    def shift_F7(self):
        self.hotKeyId=700
        self.RegisterHotKey(
            self.hotKeyId,
            win32con.MOD_SHIFT,
            win32con.VK_F7          
        )
    #开始任意时间计时
    def start_random_timer(self,event):
        #1.记录现在时间,改变notification_bar的标签
        self.start_time=datetime.now()
        self.notification_bar.SetLabel(u"开始任意倒计时！")

        #2.弹出窗口,说明开始倒计时
        dlg=MessageDialog(u"开始任意倒计时！","min_alert")
        #隔一点五秒就消失
        wx.FutureCall(1500,dlg.Destroy)
        dlg.ShowModal()

        #3.每隔一段时间,remaining_time显示为已经过了多久,调用elapsed_time函数
        self.rm_time=1
        self.show_timer=wx.Timer(self,1234)
        self.show_timer.Start(1000*60,oneShot=False) 
        self.Bind(wx.EVT_TIMER,self.elapsed_time,self.show_timer)
    #按F8结束任意倒计时
    def shift_F8(self):
        self.hotKeyId=800
        self.RegisterHotKey(
            self.hotKeyId,
            win32con.MOD_SHIFT,
            win32con.VK_F8          



        )
    #结束任意时间计时
    def end_random_timer(self,event):

        #1.记录用了多少分钟
        self.end_time=datetime.now()
        inteverval=(self.end_time-self.start_time).seconds/60

        #2.暂停显示的倒计时,并擦除文字显示remaining_time上展示的剩余时间，notification_bar恢复显示为”当前没有任何任务“
        self.show_timer.Stop()
        self.remaining_time.SetLabel("")
        self.notification_bar.SetLabel(u"无任务")

        #3.窗口time_up_dlg弹出说明时间已到，并将信息记录在xml中调用time_log函数
        dlg=TextEntryDialog(None,u"时间到！",caption=u"时间到！")
        if dlg.ShowModal()==wx.ID_OK:
            message=unicode(dlg.GetValue())
            info={"message":message,"mins":inteverval}
            self.time_log(info)


    '''终止任务'''
    #销毁记录或者记录时间
    def shift_F10(self):
        self.hotKeyId=1000
        self.RegisterHotKey(
            self.hotKeyId,
            win32con.MOD_SHIFT,
            win32con.VK_F10       
        )
    def cancel_timer(self,event):
        #1.判断是任意倒计时结束,还是常规倒计时结束,然后再结束倒计时,并擦除notifation_bar和remaining_time标签
        if re.search(u"任意",self.notification_bar.Label):
            self.show_timer.Stop()
        else:
            self.min_timer.Stop()
        self.remaining_time.SetLabel("")
        self.notification_bar.SetLabel(u"无任务")

        #2.弹出窗口,取消点叉确认点OK
        dlg=TextEntryDialog(None,u"输入任务",caption=u"输入任务")
        if dlg.ShowModal()==wx.ID_OK:
            self.end_time=datetime.now()
            inteverval=(self.end_time-self.start_time).seconds/60
            message=unicode(dlg.GetValue())
            info={"message":message,"mins":inteverval}
            self.time_log(info)

        dlg.Destroy()

    '''显示历史'''
    def show_history(self,event):
        #处理time_list.xml
        #1.将属于今天的元素找出
        tree=etree.parse(os.path.normcase(unicode("F:/历史记录/近期/【项目】小项目/定时器/time_list.xml")))
        today_date=datetime.now().strftime("%Y-%m-%d")
        # ONLY FOR DEBUG
        # today_date="2013-10-16"
        today_elements=tree.xpath('//workList[date="%s"]'%(today_date))
        #2.将所有的标签分类
        all_list=[]
        tags=set([today_element.find("tag").text for today_element in today_elements])
        for (today_element,today_number) in zip(today_elements,xrange(len(today_elements))):
            item_list=[]
            item_list.append(today_element.find("tag").text)
            item_list.append(int(re.search("\d{1,3}",today_element.find("duration").text).group()))
            all_list.append(item_list)

        # 3.将标签中所有的时间相加得出总时间
        sum_up_dict={}
        self.history_bar.SetLabel('')
        for pos_num,tag in enumerate(tags):
            for item in all_list:
                if item[0]==tag:
                    try:
                        sum_up_dict[tag]+=item[1]
                    except KeyError:
                        sum_up_dict[tag]=item[1]
            self.history_bar.SetLabel(self.history_bar.Label+u"%s:%s分钟\n"%(tag,sum_up_dict[tag]))


    '''二级函数'''
    #将info中的任务名字和时间，还有转换算成的起始时间计入time_list.xml中。试用了lxml中etree生成xml
    #格式、“<workList wlID="1"><tag>学习</tag><date>2013-10-12</date><from>15:10</from><to>15:30</to><duration>20 分钟</duration></workList>   
    def time_log(self,info):
        tree=etree.parse(os.path.normcase(unicode("F:/历史记录/近期/【项目】小项目/定时器/time_list.xml")))
        root=tree.getroot()
        #确定编号wlID
        try:
            elem_number=int(tree.find("//workList[last()]").attrib["wlID"])+1
        except:
            elem_number=1

        work_list=etree.SubElement(root,"workList",attrib={"wlID":str(elem_number)})
        #添加tag标签
        w_tag=etree.SubElement(work_list,"tag")
        w_tag.text=info["message"]
        #添加date标签
        w_date=etree.SubElement(work_list,u"date")
        w_date.text=datetime.now().strftime("%Y-%m-%d")
        #添加from和to标签
        w_from=etree.SubElement(work_list,u"from")
        w_from.text=(datetime.now()-timedelta(minutes=info["mins"])).strftime("%H:%M")
        w_to=etree.SubElement(work_list,u"to")
        w_to.text=datetime.now().strftime("%H:%M")
        #添加duration标签
        w_duration=etree.SubElement(work_list,u"duration")
        w_duration.text=u"%s 分钟"%info["mins"]
        #写入列表
        tree.write(open(os.path.normcase(unicode("F:/历史记录/近期/【项目】小项目/定时器/time_list.xml")),"r+"),encoding="utf-8")
    #显示还有多少时间，在choose_evt函数中调用
    def count_time(self,event):
        self.remaining_time.SetLabel(u"还剩%s minutes"%str(self.rm_time-1))
        self.rm_time-=1
    #显示已经走了多少时间，在unknowned_time中调用
    def elapsed_time(self,event):
        self.remaining_time.SetLabel(str(self.rm_time))
        self.rm_time+=1
    #判断是否在总计时，假如没有则弹出窗口已确认
    def check_is_running(self,event):

        if(self.notification_bar.Label==u"当前没有任何任务"):
            self.notification_bar.SetLabel(u"提醒中")
            self.warn_box=wx.MessageDialog(None,u"请确定倒计时！",caption="Warn",style=wx.OK|wx.CENTRE|wx.STAY_ON_TOP)
            retcode=self.warn_box.ShowModal()

            if(retcode==wx.ID_OK):
                self.warn_box.Destroy()
                self.notification_bar.SetLabel(u"当前没有任何任务")

class MessageDialog(wx.Dialog):
    def __init__(self,message,title):
        wx.Dialog.__init__(self,None,-1,title,size=(300,120),style=wx.STAY_ON_TOP)
        self.CenterOnScreen(wx.BOTH)
        text = wx.StaticText(self, -1, message)
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(text, 1, wx.ALIGN_CENTER|wx.TOP, 10)
        self.SetSizer(vbox)


class TextEntryDialog(wx.Dialog):
    def __init__(self,parent,title,caption):
        super(TextEntryDialog,self).__init__(parent,-1,title,style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER|wx.STAY_ON_TOP)
        text=wx.StaticText(self,-1,caption,)
        word_input=wx.TextCtrl(self,-1)
        word_input.SetInitialSize((100, 50))
        buttons = self.CreateButtonSizer(wx.OK)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(text, 0, wx.ALL, 5)
        sizer.Add(word_input, 1, wx.EXPAND|wx.ALL, 5)
        sizer.Add(buttons, 0, wx.EXPAND|wx.ALL, 5)
        self.SetSizerAndFit(sizer)
        self.word_input = word_input

    def SetValue(self, value):
        self.word_input.SetValue(value)
    def GetValue(self):
        return self.word_input.GetValue()





if __name__ == '__main__':   
    app = wx.PySimpleApp()
    frame=Rev_Frame(parent=None, id=-1)
    frame.Show()
    app.MainLoop()