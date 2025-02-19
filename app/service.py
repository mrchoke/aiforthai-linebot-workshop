from fastapi import APIRouter, Request

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageMessage

from aift import setting
from aift.multimodal import textqa
from aift.image.classification import maskdetection

from datetime import datetime

from app.configs import Configs

router = APIRouter(tags=[""])

cfg = Configs()


setting.set_api_key(cfg.AIFORTHAI_APIKEY)
line_bot_api = LineBotApi(cfg.LINE_CHANNEL_ACCESS_TOKEN)  # CHANNEL_ACCESS_TOKEN
handler = WebhookHandler(cfg.LINE_CHANNEL_SECRET)  # CHANNEL_SECRET


@router.post("/message")
async def hello_word(request: Request):
    signature = request.headers["X-Line-Signature"]
    body = await request.body()
    try:
        handler.handle(body.decode("UTF-8"), signature)
    except InvalidSignatureError:
        print(
            "Invalid signature. Please check your channel access token or channel secret."
        )
    return "OK"


@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    # session id
    current_time = datetime.now()
    # extract day, month, hour, and minute
    day, month = current_time.day, current_time.month
    hour, minute = current_time.hour, current_time.minute
    # adjust the minute to the nearest lower number divisible by 10
    adjusted_minute = minute - (minute % 10)
    result = f"{day:02}{month:02}{hour:02}{adjusted_minute:02}"

    # aiforthai multimodal chat
    text = textqa.chat(
        event.message.text, result + cfg.AIFORTHAI_APIKEY, temperature=0.6, context=""
    )["response"]

    # return text response
    send_message(event, text)


@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    message_id = event.message.id
    image_content = line_bot_api.get_message_content(message_id)

    # Save the image locally and process it
    with open("image.jpg", "wb") as f:
        for chunk in image_content.iter_content():
            f.write(chunk)

    # aiforthai maskdetection
    result = maskdetection.analyze("image.jpg", return_json=False)
    result = result[0]["result"]

    # return text response
    send_message(event, result)


def echo(event):
    line_bot_api.reply_message(
        event.reply_token, TextSendMessage(text=event.message.text)
    )


# function for sending message
def send_message(event, message):
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=message))
