import os
import streamlit as st
from google import genai
from google.genai import types

# ---------------------------------------------------------
# システムプロンプトの設定
# ---------------------------------------------------------
SYSTEM_INSTRUCTION = """
あなたは専属の英会話コーチです。ユーザーは「瞬間英作文」を通して、日本語を見た瞬間に英語を反射的に話せるようになることを目指しています。

【進め方とフォーマット】
ユーザーの回答（テキストまたは音声）に対して、必ず以下のフォーマットでフィードバックを行い、最後に次の問題を1問出題してください。
※見やすさを重視し、各項目の間には必ず空行を入れて読みやすくレイアウトしてください。

【採点】
・◯点 / 100点

【良かった点】
・（内容）

【文法ミスの修正】
・（内容）

【より自然な言い方】
・（内容）

【ネイティブがよく使う表現】
・（内容）

【覚えておきたいポイント】
・（内容）

【発音・音声フィードバック】※音声回答時のみ
・（発音、アクセント、リンキング、イントネーションの詳細）

【次の問題】
・（日本語の文章を1文だけ出題）

【条件】
・問題は中学英語レベル（英検3級〜準2級程度、15語以内）から始め、正答率に合わせて自動調整する。
・同じ文型が連続しないようにする。
・解説はすべて日本語で行う。
"""

# ---------------------------------------------------------
# 初期化
# ---------------------------------------------------------
st.set_page_config(page_title="瞬間英作文コーチ", page_icon="🔤")
st.title("🔤 瞬間英作文 App with Gemini")

api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("GEMINI_API_KEY が設定されていません。Secretsを設定してください。")
    st.stop()

client = genai.Client(api_key=api_key)

# 確実なシステム指示設定の生成
def get_config():
    return types.GenerateContentConfig(
        system_instruction=[types.Part.from_text(text=SYSTEM_INSTRUCTION)],
        temperature=0.7,
    )

# 学習ログの保持 [{role: "user"|"model", text: "..."}]
if "history" not in st.session_state:
    st.session_state.history = []

if "audio_key" not in st.session_state:
    st.session_state.audio_key = 0

# ---------------------------------------------------------
# 補助関数：プロンプトの組み立て
# ---------------------------------------------------------
def make_prompt(user_text_override=None):
    recent_history = st.session_state.history[-6:]
    
    prompt_lines = [
        "以下はここまでのレッスン履歴です。文脈を踏まえて採点・解説を行い、次の問題を出題してください。\n"
    ]
    
    for item in recent_history:
        label = "ユーザー" if item["role"] == "user" else "コーチ"
        prompt_lines.append(f"{label}: {item['text']}")
        
    if user_text_override:
        prompt_lines.append(f"ユーザー: {user_text_override}")
        
    return "\n".join(prompt_lines)

# ---------------------------------------------------------
# サイドバー
# ---------------------------------------------------------
with st.sidebar:
    st.header("メニュー")
    total_q = len([h for h in st.session_state.history if h["role"] == "user"])
    st.write(f"回答数: **{total_q} 回**")
    
    if st.button("📓 復習ノートを作成する"):
        note_prompt = make_prompt("これまでのレッスン内容（問題・解答・解説・ポイント）を振り返り、音読練習に使いやすい復習ノートを作成してください。「文法解説」「単語」「熟語」に分類した弱点分析も含めてください。")
        with st.spinner("復習ノートを作成中..."):
            res = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=note_prompt,
                config=get_config()
            )
            st.session_state.history.append({"role": "user", "text": "復習ノートの作成をリクエストしました"})
            st.session_state.history.append({"role": "model", "text": res.text})
            st.rerun()

    if st.button("🔄 最初からやり直す"):
        st.session_state.history = []
        st.session_state.audio_key += 1
        st.rerun()

# ---------------------------------------------------------
# 初回起動（1問目の自動出題）
# ---------------------------------------------------------
if len(st.session_state.history) == 0:
    with st.spinner("コーチを準備中..."):
        first_prompt = "レッスンを開始します。最初の1問目（日本語）を出題してください。"
        res = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=first_prompt,
            config=get_config()
        )
        st.session_state.history.append({"role": "model", "text": res.text})

# ---------------------------------------------------------
# 画面上の履歴表示
# ---------------------------------------------------------
for item in st.session_state.history:
    avatar = "🤖" if item["role"] == "model" else "👤"
    with st.chat_message(item["role"], avatar=avatar):
        st.markdown(item["text"])

# ---------------------------------------------------------
# 入力エリア
# ---------------------------------------------------------
st.write("---")

audio_val = st.audio_input("🎙️ 声で回答する", key=f"audio_{st.session_state.audio_key}")
user_text = st.chat_input("またはテキストで回答...")

# 音声入力時の処理
if audio_val:
    audio_bytes = audio_val.read()
    st.session_state.audio_key += 1
    
    st.session_state.history.append({"role": "user", "text": "🎙️（音声で回答しました）"})
    
    with st.chat_message("user", avatar="👤"):
        st.audio(audio_bytes, format="audio/wav")
        
    with st.chat_message("model", avatar="🤖"):
        with st.spinner("音声を聞いて採点中..."):
            prompt_text = make_prompt("（音声で回答しました。以下の音声データを聞いて採点・フィードバックし、次の問題を出題してください）")
            
            contents = [
                types.Part.from_text(text=prompt_text),
                types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav")
            ]
            
            res = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=get_config()
            )
            st.markdown(res.text)
            st.session_state.history.append({"role": "model", "text": res.text})
            st.rerun()

# テキスト入力時の処理
elif user_text:
    st.session_state.history.append({"role": "user", "text": user_text})
    
    with st.chat_message("user", avatar="👤"):
        st.write(user_text)
        
    with st.chat_message("model", avatar="🤖"):
        with st.spinner("採点中..."):
            prompt_text = make_prompt()
            res = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt_text,
                config=get_config()
            )
            st.markdown(res.text)
            st.session_state.history.append({"role": "model", "text": res.text})
            st.rerun()
