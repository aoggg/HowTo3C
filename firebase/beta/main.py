from PIL import Image
import requests
import io
import json
import cgi
from firebase_functions import https_fn,options
from firebase_admin import initialize_app
import base64
import os
from google import genai
from google.genai import types
initialize_app()
prompt="""你正在操作一台電腦或手機，使用與人類相同的作業系統。

透過讀取及分析螢幕截圖，找出螢幕截圖中的重要資訊如常見服務的Logo、文字、圖標，並且理解使用者的目標，找出下一個最能達成使用者目標的操作。

有 4 種可能的操作可供選擇。你的回覆將會被json.load函式解析。

1. click - 移動滑鼠或手指並在特定位置點擊一次
```json
[{ \"thought\": \"在這裡簡要紀錄思考流程，用於指導使用者學習\", \"operation\": \"click\", \"x\": \"x座標（例如0.27）\", \"y\": \"y座標（例如0.13）\" } ] # x,y表示點擊之位置，其中座標為在0到1內的小數，代表以螢幕左上角為原點，右方為x正向，下方為y正向，右下角為座標(1,1)
```

2. write - 用實體鍵盤或螢幕鍵盤在特定位置輸入文字
```json
[{ \"thought\": \"在這裡簡要紀錄思考流程，用於指導使用者學習\", \"operation\": \"write\", \"content\": \"要輸 入的文字\" , \"x\": \"x座標（例如0.19）\", \"y\": \"y座標（例如0.83）\"}]
```

3. other - 使用其他方式如鍵盤快捷鍵、按鈕、手勢操作電腦、手機，包含手機上可能需要使用者回到主頁面或者返回上一頁，但如果有可以透過click或write達到的方法，請考慮優先使用這兩種操作，例如使用者在瀏覽器的畫面中詢問如何開啟YouTube，則考慮告訴使用者搜尋YouTube而不是回到桌面尋找YouTube APP
```json
[{ \"thought\": \"在這裡簡要紀錄思考流程，用於指導使用者學習\", \"operation\": \"other\" }]
```

4. done－目標完成，螢幕截圖的內容與使用者之目標大致吻合，使用者不必進行其他操作即可完成目標，可以提 醒使用者若還有需要可以改以其他方式詢問
```json
[{ \"thought\": \"在這裡簡要紀錄思考流程，用於指導使用者學習\", \"operation\": \"done\"}]
```

一次返回一個操作，除非操作的連貫性相當高，例如在某個位置輸入文字可以直接使用write，又或者預期使用者 輸入完可以直接按下enter送出則可以在使用write的同時在thought部分加入...並且按下enter送出。

這是一個例子：

範例1：使用者目標「開啟Google Chrome」(附帶使用者桌面的截圖，其中包含Google Chrome的圖標，並且在螢幕正中間向上移動0.29倍螢幕高度之位置)
```json
[{ \"thought\": \"在桌面上找到 Google Chrome，點擊以開啟該應用程式\", \"operation\": \"click\", \"x\": \"0.50\" , \"y\": \"0.21\" }]
```

範例 2：使用者目標「進入Facebook網站」(附帶開啟Google Chrome新分頁的螢幕截圖，其中搜尋欄的位置在(0.40,0.17)座標)
```json
[{ \"thought\": \"因為Google Chrome瀏覽器已開啟，嘗試在搜尋欄輸入Facebook並按下enter以進行搜尋\", \"operation\": \"write\",\"content\": \"Facebook\",\"x\": \"0.40\", \"y\": \"0.17\"}]
```
再次收到與上面相同的使用者目標「進入Facebook網站」(附帶一張Google Chrome瀏覽器的截圖，其中主要頁面顯示的內容為Facebook的搜尋結果，在座標(0.33,0.40)處有facebook.com的網站)
```json
[{ \"thought\": \"點擊搜尋結果中代表facebook.com的項目以進入該網頁\", \"operation\": \"click\", \"x\": \"0.33\" , \"y\": \"0.40\"}]
```

除了使用者目標外，若有給出其他資訊，還要利用其他給定的資訊來給出最精準的指示。
其中第一個資訊是你過去回覆的紀錄，這些資訊主要用來避免出現重複給出高度相似指示的情況，請考慮使用者已經做出前述指示但畫面沒有顯著變化的情況，或者畫面中可以明確得知使用者沒有依前一個指示進行操作，則盡可能改變成較前次回覆更易懂的敘述來避免使用者無法理解；除此之外，回覆紀錄的資訊還要用來避免指示進入迴圈，例如使用者要傳送電子郵件，前一個回覆是「點擊傳送」，而使用者再點擊傳送後回到了信箱的首頁，此時就要避免重複告訴使用者要撰寫新的電子郵件，而是可以告訴使用者「郵件已經成功寄出，可以前往寄件匣檢查寄件紀錄」。

而包含以上額外資訊後的輸入格是將會如下：
(輸入開始，實際輸入從以下開始)
=====歷史訊息=====
-3:'''這裡會包含你回覆使用者的倒數第三則指示'''
-2:'''這裡會包含你回覆使用者的倒數第二則指示'''
-1:'''這裡會包含你回覆使用者的最後一則指示'''
=====使用者目標=====
'''這裡會包含最重要的使用者目標'''
(輸入結束，實際輸入到以上結束)

除此之外，一些重要的注意事項：

- 不要回覆無法協助處理請求。你只是透過傳送文字的操作指示給使用者來間接協助使用者操作作業系統。
- 每次回覆操作時thought部分以能指導大多數使用者為第一目標，以加入其他必要訊息(如使用者詢問銀行APP操 控時加入「操作銀行相關服務時請留意個人財產安全，如有疑慮請盡速撥打165反詐騙專線」、使用者出示酒類購 買頁面時加入「注意不要過量飲酒或酒後駕車」)為第二目標，再以精簡為最後目標。
- 盡可能考慮畫面中可能存在的干擾因素，避免做出錯誤操作，如釣魚廣告中顯示的下載按鈕。
- 記得在條件大致吻合時就使用done操作，例如使用者的問題只有打開某個網頁沒有表明其他用途，則檢測到打開該網頁就停止不須再額外提醒使用者進行操作。
- 若在畫面中存取到網頁或者APP中有顯著的「HowTo3C」字樣，並且畫面中大多數部分顯示的是類似通訊軟體聊天室的介面、包含「下一步」、「繼續」、「縮小」、「放大」等按鈕，則這是本服務與使用者互動的畫面，請不要將其當成搜尋引擎或通訊軟體，可以優先考慮告訴使用者回到主頁面或在網頁中開啟新分頁，同樣優先使用click、write指令而不是other，但如果僅是在畫面中出現一小部分的HowTo3C字樣並且畫面中可以辨識出其他元素，則照常回覆。且以上狀況皆不用特別提到偵測到HowTo3C網頁，只要直接說明給使用者的指示即可。"""

def generate(image,text):
    client = genai.Client(
        api_key="AIzaSyDLjGtTzhDWJ23WvIqGNjoVBUhU1E-dCTQ",
    )
    model = "gemini-2.0-flash"
    generate_content_config = types.GenerateContentConfig(
        temperature=1,
        top_p=0.95,
        top_k=40,
        max_output_tokens=8192,
        response_mime_type="text/plain",
        system_instruction=[
            types.Part.from_text(
                text=prompt
          ),
      ],
  )

    return client.models.generate_content(
        model=model,
        contents=[image,text],
        config=generate_content_config,
    )
    

api_key = "tozW6NYoRua6naAIXmlEqg"
property_id = "473413511"
statsurl = f"https://www.google-analytics.com/mp/collect?measurement_id=G-{property_id}&api_secret={api_key}"
@https_fn.on_request(region="asia-east1",memory=options.MemoryOption.MB_512)
def beta(req: https_fn.Request) -> https_fn.Response:
    if req.method == 'POST':
        try:
            if not req.content_type.startswith('multipart/form-data'):
                requests.post(statsurl, json={"events": [{"name": "beta400a","params": {}}]})
                return json.dumps({"error": "Content-Type 必須是 multipart/form-data"}), 400, {'Access-Control-Allow-Origin': 'https://howto3c.xyz','Content-Type': 'application/json'}

            form = cgi.FieldStorage(fp=req.stream, environ={'REQUEST_METHOD': 'POST', 'CONTENT_TYPE': req.content_type})

            if 'image' not in form:
                requests.post(statsurl, json={"events": [{"name": "beta400b","params": {}}]})
                return json.dumps({"error": "請求中缺少 'image' 欄位"}), 400, {'Access-Control-Allow-Origin': 'https://howto3c.xyz','Content-Type': 'application/json'}

            if 'question' not in form:
                requests.post(statsurl, json={"events": [{"name": "beta400c","params": {}}]})
                return json.dumps({"error": "請求中缺少 'question' 欄位"}), 400, {'Access-Control-Allow-Origin': 'https://howto3c.xyz','Content-Type': 'application/json'}

            image_file = form['image']
            question = form['question'].value # 取得文字內容

            if not isinstance(image_file, cgi.FieldStorage):
                requests.post(statsurl, json={"events": [{"name": "beta400d","params": {}}]})
                return json.dumps({"error": "'image' 欄位必須是檔案"}), 400, {'Access-Control-Allow-Origin': 'https://howto3c.xyz','Content-Type': 'application/json'}

            image_bytes = image_file.file.read()

            try:
                # 嘗試開啟圖片，並處理可能的例外
                image = Image.open(io.BytesIO(image_bytes))
                # 確保圖片格式正確，例如轉換為 RGB
                image = image.convert('RGB')
            except OSError as e:
                requests.post(statsurl, json={"events": [{"name": "beta400e","params": {}}]})
                return json.dumps({"error": f"圖片格式不正確或損壞: {e}"}), 400, {'Access-Control-Allow-Origin': 'https://howto3c.xyz','Content-Type': 'application/json'}


            try:
                # 正確地將 PIL Image 物件傳遞給模型
                response = generate(image,question)
                content = json.loads(response.text[7:-4])[0] #解析json字串
                response_data = {"content": content,"origin":response.text}
                requests.post(statsurl, json={"events": [{"name": "beta200","params": {}}]})
                return json.dumps(response_data), 200, {'Access-Control-Allow-Origin': 'https://howto3c.xyz','Content-Type': 'application/json'}

            except Exception as model_error:
                requests.post(statsurl, json={"events": [{"name": "beta500a","params": {}}]})
                return json.dumps({"error": f"模型處理錯誤: {model_error},模型回傳 {response.text}"}), 500, {'Access-Control-Allow-Origin': 'https://howto3c.xyz','Content-Type': 'application/json'}

        except (AttributeError, KeyError, TypeError, ValueError) as e:
            requests.post(statsurl, json={"events": [{"name": "beta400f","params": {}}]})
            return json.dumps({"error": f"請求解析錯誤: {e}"}), 400, {'Access-Control-Allow-Origin': 'https://howto3c.xyz','Content-Type': 'application/json'}
        except Exception as e:
            requests.post(statsurl, json={"events": [{"name": "beta500b","params": {}}]})
            return json.dumps({"error": f"伺服器發生未預期錯誤: {e}"}), 500, {'Access-Control-Allow-Origin': 'https://howto3c.xyz','Content-Type': 'application/json'}
    else:
        requests.post(statsurl, json={"events": [{"name": "beta405","params": {}}]})
        return json.dumps({"error": "只允許 POST 請求"}), 405, {'Access-Control-Allow-Origin': 'https://howto3c.xyz','Content-Type': 'application/json'}