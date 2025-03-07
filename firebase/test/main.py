from PIL import Image
import requests
import io
import json
import cgi
from firebase_functions import https_fn,options
from firebase_admin import initialize_app
initialize_app()
api_key = "tozW6NYoRua6naAIXmlEqg"
property_id = "473413511"
statsurl = f"https://www.google-analytics.com/mp/collect?measurement_id=G-{property_id}&api_secret={api_key}"
@https_fn.on_request(region="asia-east1")
def test(req: https_fn.Request) -> https_fn.Response:
    if req.method == 'POST':
        try:
            if not req.content_type.startswith('multipart/form-data'):
                requests.post(statsurl, json={"events": [{"name": "test400a","params": {}}]})
                return json.dumps({"error": "Content-Type 必須是 multipart/form-data"}), 400, {'Access-Control-Allow-Origin': 'https://howto3c.xyz','Content-Type': 'application/json'}

            form = cgi.FieldStorage(fp=req.stream, environ={'REQUEST_METHOD': 'POST', 'CONTENT_TYPE': req.content_type})

            if 'image' not in form:
                requests.post(statsurl, json={"events": [{"name": "test400b","params": {}}]})
                return json.dumps({"error": "請求中缺少 'image' 欄位"}), 400, {'Access-Control-Allow-Origin': 'https://howto3c.xyz','Content-Type': 'application/json'}

            if 'question' not in form:
                requests.post(statsurl, json={"events": [{"name": "test400c","params": {}}]})
                return json.dumps({"error": "請求中缺少 'question' 欄位"}), 400, {'Access-Control-Allow-Origin': 'https://howto3c.xyz','Content-Type': 'application/json'}

            image_file = form['image']
            question = form['question'].value # 取得文字內容

            if not isinstance(image_file, cgi.FieldStorage):
                requests.post(statsurl, json={"events": [{"name": "test400d","params": {}}]})
                return json.dumps({"error": "'image' 欄位必須是檔案"}), 400, {'Access-Control-Allow-Origin': 'https://howto3c.xyz','Content-Type': 'application/json'}

            image_bytes = image_file.file.read()

            try:
                # 嘗試開啟圖片，並處理可能的例外
                image = Image.open(io.BytesIO(image_bytes))
                # 確保圖片格式正確，例如轉換為 RGB
                image = image.convert('RGB')
            except OSError as e:
                requests.post(statsurl, json={"events": [{"name": "test400e","params": {}}]})
                return json.dumps({"error": f"圖片格式不正確或損壞: {e}"}), 400, {'Access-Control-Allow-Origin': 'https://howto3c.xyz','Content-Type': 'application/json'}


            try:
                requests.post(statsurl, json={"events": [{"name": "test200","params": {}}]})
                return json.dumps({"height":image.height,"width":image.width,"question":question}), 200, {'Access-Control-Allow-Origin': 'https://howto3c.xyz','Content-Type': 'application/json'}

            except Exception as model_error:
                requests.post(statsurl, json={"events": [{"name": "test500a","params": {}}]})
                return json.dumps({"error": f"模型處理錯誤: {model_error}"}), 500, {'Access-Control-Allow-Origin': 'https://howto3c.xyz','Content-Type': 'application/json'}

        except (AttributeError, KeyError, TypeError, ValueError) as e:
            requests.post(statsurl, json={"events": [{"name": "test400f","params": {}}]})
            return json.dumps({"error": f"請求解析錯誤: {e}"}), 400, {'Access-Control-Allow-Origin': 'https://howto3c.xyz','Content-Type': 'application/json'}
        except Exception as e:
            requests.post(statsurl, json={"events": [{"name": "test500b","params": {}}]})
            return json.dumps({"error": f"伺服器發生未預期錯誤: {e}"}), 500, {'Access-Control-Allow-Origin': 'https://howto3c.xyz','Content-Type': 'application/json'}
    else:
        requests.post(statsurl, json={"events": [{"name": "test405","params": {}}]})
        return json.dumps({"error": "只允許 POST 請求"}), 405, {'Access-Control-Allow-Origin': 'https://howto3c.xyz','Content-Type': 'application/json'}