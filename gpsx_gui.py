#!/usr/bin/env python

''' kv sample3 '''
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.properties import ObjectProperty, StringProperty, BooleanProperty
from kivy.uix.popup import Popup
import datetime
import os
import gpsx

Builder.load_string('''
<MainWidget>:
	BoxLayout:
		orientation: 'vertical'
		size: root.size
		
		BoxLayout:
			orientation: 'horizontal'
			height: '50sp'
			size_hint: 1.0, None
			
			Button:
				text: 'Input file...'
				size_hint: 1, 1
				on_press: root.InputButtonPressed()
			
			Spinner:
				id: input_format
				width: '100sp'
				size_hint: None, 1.0
				
		TextInput:
			id: InputFile
			height: '100sp'
			size_hint: 1.0, None
		
		BoxLayout:
			orientation: 'horizontal'
			height: '50sp'
			size_hint: 1.0, None
			
			Button:
				text: 'Output file...'
				size_hint: 1, 1
				on_press: root.OutputButtonPressed()
			
			Spinner:
				id: output_format
				width: '100sp'
				size_hint: None, 1.0
				
		TextInput:
			id: OutputFile
			height: '100sp'
			size_hint: 1.0, None
		
		Button:
			height: '50sp'
			size_hint: 1, None
			text: 'Convert'
			on_press: root.ConvertButtonPressed()
		
		Label:
			text: 'Log'
			height: '30sp'
			size_hint: 1.0, None
			halign: 'left'
			text_size: self.size
		
		TextInput:
			text: root.Log
			readonly: True
			size_hint: 1.0, 1.0
			foreground_color: 1, 1, 1, 1
			background_color: 0, 0, 0, 1

<FileSelectPopup>:
	title: root.Path
	
	BoxLayout:
		orientation: 'vertical'
		size: root.size
		
		FileChooserIconView:
			id: FileChooser
			path: root.Path
			multiselect: root.Multi
			on_touch_down: root.title = self.path
		
		BoxLayout:
			orientation: 'horizontal'
			height: '50sp'
			size_hint: 1, None
			
			Button:
				text: 'OK'
				on_press: root.OkButtonPressed(FileChooser.path, FileChooser.selection)
			
			Button:
				text: 'Select dir'
				on_press: root.OkButtonPressed(FileChooser.path, None)
			
			Button:
				text: 'Cancel'
				on_press: root.CancelButtonPressed()
''')


class FileSelectPopup(Popup):
	OnOk		= ObjectProperty(None)
	OnCancel	= ObjectProperty(None)
	Path		= StringProperty(None)
	Multi		= BooleanProperty(False)
	
	def __init__(self, **kwargs) -> None:
		super(FileSelectPopup, self).__init__(**kwargs)
		self.auto_dismiss = False
		
	
	def OkButtonPressed(self, path, selection):
		# ファイルが何も選択されていない
		if selection is not None and len(selection) == 0:
			return
		
		self.dismiss()
		if self.OnOk:
			self.OnOk(path, selection)
	
	def CancelButtonPressed(self):
		self.dismiss()
		if self.OnCancel:
			self.OnCancel(path, selection)

class SimpleArg():
	def __init__(self):
		self.input_file		= []
		self.input_format	= None
		self.output_file	= None
		self.output_format	= None

class MainWidget(Widget):
	Log			= StringProperty('* GPS log converter\n')
	
	def __init__(self, **kwargs):
		super(MainWidget, self).__init__(**kwargs)
		FormatList = gpsx.GpsLogClass.GetAvailableFormat()
		FormatList[0].insert(0, 'auto')
		
		self.ids['InputFile'].text			= '/sdcard/OneDrive/vsd/log/vsd.log'
		self.ids['OutputFile'].text			= datetime.datetime.now().strftime('/sdcard/Android/data/com.racechrono.app/files/sessions/session_%Y%m%d_%H%M')
		
		self.ids['input_format'].text		= 'auto'
		self.ids['input_format'].values		= FormatList[0]
		self.ids['output_format'].text		= 'RaceChrono'
		self.ids['output_format'].values	= FormatList[1]
	
	def InputButtonPressed(self):
		self.popup = FileSelectPopup(
			Path		= os.path.dirname(self.ids['InputFile'].text.split('\n')[0]),
			size_hint	= (0.9, 0.9),
			Multi		= True,
			OnOk		= self.OnInputOk
		)
		self.popup.open()
	
	def OnInputOk(self, path, selection):
		if selection is None:
			self.ids['InputFile'].text = path + '/'
		else:
			selection.sort()
			self.ids['InputFile'].text = '\n'.join(selection)
		
		self.Log += '* Input file selected: ' + self.ids['InputFile'].text + '\n'
	
	def OutputButtonPressed(self):
		self.popup = FileSelectPopup(
			Path		= os.path.dirname(self.ids['OutputFile'].text),
			size_hint	= (0.9, 0.9),
			OnOk		= self.OnOutputOk
		)
		self.popup.open()
	
	def OnOutputOk(self, path, selection):
		if selection is None:
			self.ids['OutputFile'].text = path + '/'
		else:
			self.ids['OutputFile'].text = selection[0]
		
		self.Log += '* Output file selected: ' + self.ids['OutputFile'].text + '\n'
	
	def ConvertButtonPressed(self):
		Arg = SimpleArg()
		
		for file in self.ids['InputFile'].text.split('\n'):
			if len(file) > 0:
				Arg.input_file.append(file)
		Arg.input_format = self.ids['input_format'].text
		
		if Arg.input_format == 'auto':
			Arg.input_format = None
		
		Arg.output_file = self.ids['OutputFile'].text
		
		Arg.output_format = self.ids['output_format'].text
		if Arg.output_format == 'auto':
			Arg.output_format = None
		
		self.Log += ('* Start log converting...\n' +
			'  in: %s format=%s\n' +
			'  out: %s format=%s\n') % (
				Arg.input_file,  Arg.input_format,
				Arg.output_file, Arg.output_format
			)
		
		try:
			gpsx.Convert(Arg)
			self.Log += '* done.\n'
		except Exception as Error:
			self.Log += '* Error: ' + str(Error) + '\n'
	
class MyApp(App):
	def build(self):
		return MainWidget()

if __name__ == '__main__':
	MyApp().run()
