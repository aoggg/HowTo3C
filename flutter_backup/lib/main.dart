import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:fluttertoast/fluttertoast.dart';
void main(){
  runApp(const MaterialApp(
    home: ChatScreen(),
  ));
}
class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});
  @override
  State<ChatScreen> createState() => _ChatScreenState();
}
class _ChatScreenState extends State<ChatScreen> {
  final TextEditingController _controller = TextEditingController();
  final List<ChatMessage> _messages = [];
  String _screenStreamUrl='';
  bool _showSettings=false;
  String _hintText='輸入問題...';
  String _questionNow='';
  Future<(Uint8List?,String?)> _callAPI(Uint8List img,String question) async {
    final uri = Uri.parse('https://howto.howto3c.xyz');
    var request = http.MultipartRequest('POST', uri)
      ..files.add(http.MultipartFile.fromBytes('image', img, filename: 'image.jpg'))
      ..fields['question']=question;
    final response=await request.send();
    if(response.statusCode==200){
      final reply=jsonDecode(await response.stream.bytesToString());
      final paintedImg=await drawPointOnImage(img, double.parse(reply['content']['x']), double.parse(reply['content']['y']));
      return (paintedImg,reply['content']['thought'] as String);
    }else{
      Fluttertoast.showToast(
        msg: "伺服器錯誤${response.statusCode}", // 訊息內容
        toastLength: Toast.LENGTH_SHORT, // 顯示時間長度
        gravity: ToastGravity.BOTTOM, // 顯示位置
        timeInSecForIosWeb: 1, // iOS 和 Web 上的顯示秒數
        backgroundColor: Colors.grey, // 背景顏色
        textColor: Colors.white, // 文字顏色
        fontSize: 16.0, // 文字大小
      );
      return (null,null);
    }
  }
  Future<Uint8List?> drawPointOnImage(Uint8List imgBytes, double x, double y) async {
    // 1. 將 Uint8List 解碼為 ui.Image
    final ui.Codec codec = await ui.instantiateImageCodec(imgBytes);
    final ui.FrameInfo frameInfo = await codec.getNextFrame();
    final ui.Image image = frameInfo.image;
    // 2. 建立 Canvas 並在上面繪製
    final ui.PictureRecorder recorder = ui.PictureRecorder();
    final Canvas canvas = Canvas(recorder);
    // 繪製原始圖片
    canvas.drawImage(image, Offset.zero, Paint());
    final point=Offset(x*image.width, y*image.height);
    // 繪製紅點
    final paint = Paint()
      ..color = Colors.red
      ..style = PaintingStyle.fill;
    canvas.drawCircle(point, 10, paint);
    // 3. 將 Canvas 轉換為 Uint8List
    final ui.Picture picture = recorder.endRecording();
    final ui.Image paintedImage = await picture.toImage(image.width, image.height);
    final ByteData? byteData = await paintedImage.toByteData(format: ui.ImageByteFormat.png);
    final Uint8List? paintedBytes = byteData?.buffer.asUint8List();
    //print('ok');
    return paintedBytes;
  }
  @override
  void initState() {
    super.initState();
    _loadSettings();
  }
  _loadSettings() async {
    SharedPreferences prefs = await SharedPreferences.getInstance();
    setState(() {
      _screenStreamUrl = prefs.getString('screenStreamUrl') ?? '';
    });
  }
  int findByteArray(Uint8List data, Uint8List pattern, int startIndex) {
    for (int i = startIndex; i <= data.length - pattern.length; i++) {
      bool match = true;
      for (int j = 0; j < pattern.length; j++) {
        if (data[i + j] != pattern[j]) {
          match = false;
          break;
        }
      }
      if (match) {
        return i;
      }
    }
    return -1;
  }
  Future<Uint8List?> getFirstMJPEGFrame(String mjpegUrl) async {
    final request = http.Request('get', Uri.parse(mjpegUrl));
    try{
      final streamedResponse = await request.send();
      if (streamedResponse.statusCode == 200) {
        //print('start');
        final stream = streamedResponse.stream.transform(StreamTransformer.fromHandlers(
          handleData: (List<int> data, EventSink<Uint8List> sink) {
            sink.add(Uint8List.fromList(data));
          },
        ));
        try {
          List<int> buffer = [];
          int chunksRead = 0; // 讀取的 chunk 數量
          const maxChunks = 100; // 最大讀取 chunk 數量
          Uint8List? resultData;
          await stream.takeWhile((Uint8List chunk){
            return chunksRead<maxChunks && resultData==null;
          }).forEach((Uint8List chunk) {
            //print('read chuck');
            buffer.addAll(chunk); // 將 chunk 添加到 buffer 中
            chunksRead++;
            Uint8List uint8Buffer = Uint8List.fromList(buffer);
            // 檢查是否找到 JPEG 標記
            int startIndex = 0;
            final startMarker = findByteArray(uint8Buffer, Uint8List.fromList([0xFF, 0xD8]), startIndex);
            if (startMarker != -1) {
              final endMarker = findByteArray(uint8Buffer, Uint8List.fromList([0xFF, 0xD9]), startMarker);
              if (endMarker != -1) {
                //print('find');
                final jpegBytes = uint8Buffer.sublist(startMarker, endMarker + 2);
                resultData=jpegBytes; // 找到完整的圖片，返回
              }
            }
          });
          //print('stop');
          //print(chunksRead);
          return resultData; // 未找到完整的圖片
        } catch (e) {
          //print('Error handling stream or decoding JPEG: $e');
          return null;
        }
      } else {
        //print('Failed to get MJPEG stream: ${streamedResponse.statusCode}');
        return null;
      }
    }catch(e){
      return null;
    }
  }
  Future<void> _sendImage() async {
    Uint8List? img=_screenStreamUrl.isEmpty?null:await getFirstMJPEGFrame('${_screenStreamUrl[_screenStreamUrl.length-1]=='/'?_screenStreamUrl:'$_screenStreamUrl/'}stream.mjpeg');
    if(img==null){
      Fluttertoast.showToast(
        msg: "無法獲取截圖", // 訊息內容
        toastLength: Toast.LENGTH_SHORT, // 顯示時間長度
        gravity: ToastGravity.BOTTOM, // 顯示位置
        timeInSecForIosWeb: 1, // iOS 和 Web 上的顯示秒數
        backgroundColor: Colors.grey, // 背景顏色
        textColor: Colors.white, // 文字顏色
        fontSize: 16.0, // 文字大小
      );
    }else{
      setState(() {
        _messages.add(ChatMessage(imgBytes: img, isMe: true,isImg: true));
      });
    }
  }
  Future<void> _sendMessage() async {
    if (_controller.text.isNotEmpty||_questionNow.isNotEmpty) {
      if(_controller.text.isNotEmpty)_questionNow=_controller.text;
      if(_messages.isEmpty||!_messages.last.isMe||!_messages.last.isImg){
        await _sendImage();
      }
      if(_messages.isEmpty||!_messages.last.isMe||!_messages.last.isImg)return;
      final (replyImg,replyText) = await _callAPI(_messages.last.imgBytes!, _questionNow);
      setState((){
        _messages.add(ChatMessage(text: _questionNow, isMe: true));
        _messages.add(ChatMessage(imgBytes: replyImg, isMe: false, isImg: true,));
        _messages.add(ChatMessage(text: replyText, isMe: false));
      });
      _controller.clear();
      _hintText='輸入新的問題，或者直接點擊送出可以沿用上個問題「${_questionNow}」';
    }
  }
  Widget _buildSettingsDialog() {
    return AlertDialog(
      title: Text('設定'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          TextFormField(
            decoration: InputDecoration(labelText: '輸入螢幕串流網址'),
            onChanged: (value) {
              _screenStreamUrl = value;
            },
            initialValue: _screenStreamUrl,
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () {
            setState(() {
              _showSettings = false;
            });
          },
          child: Text('取消'),
        ),
        TextButton(
          onPressed: () async{
            SharedPreferences prefs = await SharedPreferences.getInstance();
            await prefs.setString('screenStreamUrl', _screenStreamUrl);
            setState(() {
              _showSettings = false;
            });
          },
          child: Text('確定'),
        ),
      ],
    );
  }
  int _expandedIndex = -1;
  bool _isExpanded = false;
  void _toggleImageSize(int index) {
    setState(() {
      if (_isExpanded && _expandedIndex == index) {
        _isExpanded = false;
        _expandedIndex = -1;
      } else {
        _isExpanded = true;
        _expandedIndex = index;
      }
    });
  }
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('HowTo3C'),
        actions: [
          IconButton(
            icon: Icon(Icons.settings),
            onPressed: () {
              setState(() {
                _showSettings = true;
              });
            },
          ),
        ],
      ),
      body: Stack(
        children: [
          Padding(
            padding: const EdgeInsets.all(8.0),
            child: Column(
              children: [
                Expanded(
                  child: ListView.builder(
                    itemCount: _messages.length,
                    itemBuilder: (context, index) {
                      return _messages[index].isImg?GestureDetector(onTap:(){_toggleImageSize(index);},child:_messages[index],):_messages[index];
                    },
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.all(8.0),
                  child: Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _controller,
                          decoration: InputDecoration(
                            hintText: _hintText,
                            border: OutlineInputBorder(),
                          ),
                        ),
                      ),
                      IconButton(
                        icon: const Icon(Icons.send),
                        onPressed: _sendMessage,
                      ),
                      IconButton( // 新增的螢幕截圖按鈕
                        icon: const Icon(Icons.camera_alt),
                        onPressed: _sendImage,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          if (_isExpanded)
            Positioned(
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              child: GestureDetector(
                onTap: (){_toggleImageSize(_expandedIndex);},
                child: Center(
                  child: Image.memory(
                    _messages[_expandedIndex].imgBytes!,
                    fit: BoxFit.contain,
                    height: MediaQuery.of(context).size.height * 0.9,
                    width: MediaQuery.of(context).size.width * 0.9,
                  ),
                ),
              ),
            ),
          if (_showSettings)
            _buildSettingsDialog(),
        ],
      ),
    );
  }
}
class ChatMessage extends StatelessWidget {
  final String? text;
  final Uint8List? imgBytes;
  final bool isMe,isImg;
  const ChatMessage({super.key, this.text, this.imgBytes, required this.isMe, this.isImg=false});
  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: isMe ? Alignment.topRight : Alignment.topLeft,
      child:ConstrainedBox(
        constraints: BoxConstraints(
          maxHeight: MediaQuery.sizeOf(context).height*0.3,
        ),
        child: Container(
          padding: const EdgeInsets.all(8.0),
          margin: const EdgeInsets.symmetric(vertical: 4.0, horizontal: 8.0),
          decoration: BoxDecoration(
            color: isMe ? Colors.blue[200] : Colors.grey[300],
            borderRadius: BorderRadius.circular(8.0),
          ),
          child: isImg?Image.memory(imgBytes!):Text(text ?? ''),
        ),
      ),
    );
  }
}