GPSX - gps log converter
======================

GPSX は，python / kivy で動作する GPS ログコンバータです．

以下を主眼に開発されています．

- [GPSBabel](https://www.gpsbabel.org/index.html) でサポートされない，マイナーな GPS フォーマットのサポート ([RaceChrono](https://play.google.com/store/apps/details?id=com.racechrono.app&hl=ja&gl=US) 等)
- python / kivy で記述されており，プラットフォームを選ばない
  - Android の [Pydroid 3](https://play.google.com/store/apps/details?id=ru.iiec.pydroid3) でも動作可能

## GUI 版コマンドライン

オプションはありません．

	gpsx_gui.py

## CLI 版コマンドライン オプション

	gpsx.py [-h] [-I input_format] [-O output_format] [-o output_file] [input_file [input_file ...]]

- input_file
  - 入力ファイルを指定 (複数可) します．1個も指定されていない場合は標準入力から入力します．
  - RaceChrono の場合は，session ファイルが格納されたディレクトリを指定します．.rcz (圧縮形式) はサポートしていません．

- input_format
  - 入力ファイルのフォーマットを指定します．input_file の拡張子から判断できる場合は省略可能です．

- output_file
  - 出力ファイルを指定します．出力ファイルが指定された場合，複数の入力ファイルが 1つの出力に集約されます．
  - 出力ファイルが指定されない場合，出力は集約されず，入力ファイルの拡張子を出力フォーマットのものに変更したファイルに出力されます．
  - `-` を指定すると，標準出力に出力します．
  - RaceChrono の場合は，session ファイルを格納するディレクトリを指定します．.rcz (圧縮形式) はサポートしていません．

- output_format
  - 出力ファイルのフォーマットを指定します．output_file の拡張子から判断できる場合は省略可能です．

- input_format / output_format には以下が使用できます．
  - nmea: NMEA 0183
  - gpx: GPS eXchange Format
  - kml: Google Keyhole Markup Language
  - RaceChrono: Android [RaceChrono](https://play.google.com/store/apps/details?id=com.racechrono.app&hl=ja&gl=US)

### コマンドライン例
	gpxy.py in1.nmea in2.nmea -O gpx
in1.nmea (NMEA) を GPX に変換し in1.gpx に出力し，in2.nmea (NMEA) を GPX に変換し in2.gpx に出力します．

	gpxy.py in1.nmea in2.nmea -o out.gpx
in1.nmea, in2.nmea (NMEA) を GPX に変換し out.gpx に集約し出力します．

	gpxy.py in1nme in2.nmea -o session -O RaceChrono
in1.nmea, in2.nmea (NMEA) を RaceChrono に変換し session ディレクトリに出力します．

	gpxy.py -I nmea -O gpx -o -
標準入力 (NMEA) を GPX に変換し標準出力に出力します．
