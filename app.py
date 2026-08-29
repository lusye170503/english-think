import os
import streamlit as st
from google import genai
from google.genai import types

# ---------------------------------------------------------
# システムプロンプトの設定
# ---------------------------------------------------------
SYSTEM_INSTRUCTION = """
# 役割 
あなたは私専属の英会話コーチです。 
私は瞬間英作文を通して、英語を瞬時に口から出す力を鍛えたいです。 

# 目的 
日本語を見た瞬間に英語で話せるようになることが目標です。 
英語を考え込まず、反射的に話せるようにトレーニングしてください。 

# 進め方 
①日本語を1文だけ出題してください。
・難易度は中学英語レベルから始める 
・日常会話でよく使う表現を優先する 
・1文は15語以内で短めにする 
② 私が英訳します。 
③ 私が回答したら、以下の順番でフィードバックしてください。 

【フィードバック】 
・採点（100点満点） 
・良かった点 
・文法ミスの修正 
・より自然な言い方 
・ネイティブがよく使う表現 
・覚えておきたいポイント
④ その後、次の問題を1問だけ出してください。 

# 条件 
・レベル感は英検3級〜準2級程度まで、中期の目標はCEFRのB1レベル、最終目標はCEFRのB2レベルを目指す
・アメリカ英語を基準とする
・英語は私が答えるまで表示しない 
・解説は日本語で行う 
・英会話でよく使う表現を優先する 
・難易度は私の正答率に合わせて自動調整する 
・同じ文型が続かないようにする 
・10問ごとに苦手な文法や表現を分析し、重点的に復習問題を出してください。
・分析した内容は「文法解説」「単語（品詞も含む）」「熟語、慣用句」に分類してまとめる
・私が音声（ボイスメッセージや音声入力）で回答した旨が示された場合は、英文の正しさに加えて「発音・リンキング・イントネーションの良さ」も褒めてください。
・ユーザーから10問ごとの復習ノート作成を求められた場合は、音読練習にも使い易い体裁で、10問分のレッスン内容（問題・解答・解説・NATポイント）を振り返る綺麗で読みやすい復習用ノートを作成してください。
"""

# ---------------------------------------------------------
# Streamlit UI & セッション状態の初期化
# ---------------------------------------------------------
st.set_page_config(page_title="瞬間英作文コーチ", page_icon="🔤")
st.title("🔤 瞬間英作文 App with Gemini")

# APIキー取得（Streamlit Secrets または 環境変数から）
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.error("GEMINI_API_KEY が設定されていません。Secretsまたは環境変数を設定してください。")
    st.stop()

# Gemini クライアントの初期化
client = genai.Client(api_key=api_key)

# チャット履歴の保持
if "chat_session" not in st.session_state:
    st.session_state.chat_session = client.chats.create(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.7,
        )
    )

if "messages" not in st.session_state:
    st.session_state.messages = []
    # 最初の問題を出題させるため自動起動
    initial_response = st.session_state.chat_session.send_message("スタート！最初の1問目を出題してください。")
    st.session_state.messages.append({"role": "model", "content": initial_response.text})

# ---------------------------------------------------------
# サイドバー機能（復習ノート作成ボタンなど）
# ---------------------------------------------------------
with st.sidebar:
    st.header("メニュー")
    if st.button("📓 復習ノートを作成する（10問ごと）"):
        prompt_note = "これまでの10問分のレッスン内容（問題・解答・解説・NATポイント）を振り返る、音読練習に使いやすい綺麗な復習用ノートを作成してください。「文法解説」「単語（品詞含む）」「熟語・慣用句」に分類した苦手分析も含めてください。"
        st.session_state.messages.append({"role": "user", "content": prompt_note})
        response = st.session_state.chat_session.send_message(prompt_note)
        st.session_state.messages.append({"role": "model", "content": response.text})
        st.rerun()

    if st.button("🔄 チャットをリセット"):
        st.session_state.clear()
        st.rerun()

# ---------------------------------------------------------
# チャット履歴の表示
# ---------------------------------------------------------
for msg in st.session_state.messages:
    avatar = "🤖" if msg["role"] == "model" else "👤"
    with st.chat_message(msg["role"], avatar=avatar):
        st.write(msg["content"])

# ---------------------------------------------------------
# ユーザー入力
# ---------------------------------------------------------
user_input = st.chat_input("英語で回答を入力してください...")

if user_input:
    # ユーザーメッセージの表示と保存
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="👤"):
        st.write(user_input)

    # Geminiからの回答を取得
    with st.chat_message("model", avatar="🤖"):
        with st.spinner("コーチが採点・分析中..."):
            response = st.session_state.chat_session.send_message(user_input)
            st.write(response.text)
            st.session_state.messages.append({"role": "model", "content": response.text})
