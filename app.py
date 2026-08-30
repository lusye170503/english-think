import os
import streamlit as st
from google import genai

st.title("🔤 瞬間英作文 App (テストモード)")

api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.error("APIキーが見つかりません。")
    st.stop()

# SDKの初期化
client = genai.Client(api_key=api_key)

if st.button("テスト実行"):
    try:
        # 型指定や複雑なConfigを使わず、最もシンプルな文字列のみで呼び出し
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="英会話の練習をはじめます。最初の1問目を日本語で出題してください。"
        )
        st.success("動作確認成功！")
        st.write(response.text)
    except Exception as e:
        st.error(f"エラーが発生しました: {type(e).__name__}")
        st.exception(e)
