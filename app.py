#!/usr/bin/env python3
"""
LINE Auto Translator Bot
Automatically translates Thai <-> English messages in LINE groups.
- Thai messages -> English translation
- English messages -> Thai translation
"""

import os
import re
import logging
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from googletrans import Translator
from langdetect import detect, LangDetectException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# LINE Bot credentials
CHANNEL_ACCESS_TOKEN = os.environ.get(
    "LINE_CHANNEL_ACCESS_TOKEN",
    "TnZ3opN0xCRqNNNxX/cElBddwwNtxjIR8pVjDXFSnEbJDfptMmyFX+Hua3QMvyCJF6pEGvCDR3KQPn2VUm+Fqf842BEH6kM5ak3PgPeO+blWEmVmYjdXrbIevJnwtbknW4CQfUdZmQ6JiFI+bD0soQdB04t89/1O/w1cDnyilFU="
)
CHANNEL_SECRET = os.environ.get(
    "LINE_CHANNEL_SECRET",
    "7e73565ae6edbe6833252d372573ade4"
)

app = Flask(__name__)
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)
translator = Translator()


def contains_thai(text):
    """Check if text contains Thai characters."""
    thai_pattern = re.compile(r'[\u0E00-\u0E7F]')
    return bool(thai_pattern.search(text))


def contains_english(text):
    """Check if text contains English letters."""
    eng_pattern = re.compile(r'[a-zA-Z]')
    return bool(eng_pattern.search(text))


def detect_language(text):
    """
    Detect whether the text is Thai or English.
    Returns 'th', 'en', or 'unknown'.
    """
    if contains_thai(text):
        return 'th'
    try:
        lang = detect(text)
        if lang == 'en':
            return 'en'
        if contains_english(text) and lang in ['en', 'de', 'fr', 'es', 'it', 'nl', 'pt']:
            return 'en'
    except LangDetectException:
        pass
    if contains_english(text):
        return 'en'
    return 'unknown'


def translate_text(text, src_lang, dest_lang):
    """Translate text from src_lang to dest_lang using Google Translate."""
    try:
        result = translator.translate(text, src=src_lang, dest=dest_lang)
        return result.text
    except Exception as e:
        logger.error(f"Translation error: {e}")
        try:
            new_translator = Translator()
            result = new_translator.translate(text, src=src_lang, dest=dest_lang)
            return result.text
        except Exception as e2:
            logger.error(f"Translation retry error: {e2}")
            return None


@app.route("/callback", methods=["POST"])
def callback():
    """LINE Webhook callback endpoint."""
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    logger.info(f"Request body: {body[:200]}...")
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        logger.error("Invalid signature")
        abort(400)
    return "OK"


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    """Handle incoming text messages and auto-translate."""
    text = event.message.text.strip()
    if len(text) < 2 or text.startswith('/'):
        return
    lang = detect_language(text)
    logger.info(f"Detected language: {lang} for text: {text[:50]}...")
    if lang == 'th':
        translated = translate_text(text, 'th', 'en')
        if translated and translated.strip().lower() != text.strip().lower():
            reply = f"EN: {translated}"
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=reply)
            )
    elif lang == 'en':
        translated = translate_text(text, 'en', 'th')
        if translated and translated.strip() != text.strip():
            reply = f"TH: {translated}"
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=reply)
            )
    else:
        logger.info(f"Skipping message with unknown language: {text[:50]}...")


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return "OK"


@app.route("/", methods=["GET"])
def index():
    """Root endpoint."""
    return "LINE Auto Translator Bot is running!"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
