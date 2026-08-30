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
※見やすさを重視し、項目ごとに必ず改行と空行を入れて読みやすくレイアウトしてください。

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

④ その後、次の問題を1問だけ出してください。 

# 条件 
・レベル感は英検3級〜準2級程度まで、中期の目標はCEFRのB1レベル、最終目標はCEFRのB2レベルを目指す
・アメリカ英語を基準とする
・英語は私が答えるまで表示しない 
・解説は日本語で行う 
・難易度は私の正答率に合わせて自動調整する 
・同じ文型が続かないようにする 
・音声データで回答があった場合は、英文の正しさに加えて、実際に聞こえる「発音・リンキング・イントネーションの良さや改善点」も具体的に評価・指導してください。
・ユーザーから10問ごとの復習ノート作成を求められた場合は、音読練習にも使い易い体裁で、10問分のレッスン内容を振り返る綺麗で読みやすい復習用ノートを作成してください。
"""

# ---------------------------------------------------------
# Streamlit UI & 初期化
# ---------------------------------------------------------
st.set_page_config(page_title="瞬間英作文コーチ", page_icon="🔤")
st.title("🔤 瞬間英作文 App with Gemini")

# APIキー取得
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.error("GEMINI_API_KEY が設定されていません。Secretsを設定してください。")
    st.stop()

client = genai.Client(api_key=api_key)

# 画面表示＆コンテキスト管理用の履歴
if "text_history" not in st.session_state:
    st.session_state.text_history = []

# 音声入力Widgetのリセット用キー
if "audio_key_count" not in st.session_state:
    st.session_state.audio_key_count = 0


def build_prompt_from_history():
    """
    直近のやり取り（最大6件/3往復）を1つのプロンプトテキストに整形
    """
    recent_messages = st.session_state.text_history[-6:] if len(st.session_state.text_history) > 6 else st.session_state.text_history
    
    prompt = "以下はこれまでの学習履歴です。文脈を踏まえて次のステップを進めてください。\n\n"
    for msg in recent_messages:
        speaker = "ユーザー" if msg["role"] == "user" else "コーチ"
        prompt += f"[{speaker}]: {msg['text']}\n"
    
    prompt += "\n上記を踏まえ、指示に従ってフィードバックと次の問題の出題を行ってください。"
    return prompt


# ---------------------------------------------------------
# サイドバー機能
# ---------------------------------------------------------
with st.sidebar:
    st.header("メニュー")
    st.write(f"現在の総ラリー数: **{len(st.session_state.text_history) // 2} 回**")
    
    if st.button("📓 復習ノートを作成する（10問ごと）"):
        prompt_note = "これまでのレッスン内容（問題・解答・解説・ポイント）を振り返る、音読練習に使いやすい綺麗な復習用ノートを作成してください。「文法解説」「単語（品詞含む）」「熟語・慣用句」に分類した苦手分析も含めてください。"
        
        st.session_state.text_history.append({"role": "user", "text": prompt_note})
        
        with st.spinner("復習ノートを生成中..."):
            prompt = build_prompt_from_history()
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.7,
                )
            )
            st.session_state.text_history.append({"role": "model", "text": response.text})
            st.rerun()

    if st.button("🔄 画面をクリア"):
        st.session_state.text_history = []
        st.session_state.audio_key_count += 1
        st.rerun()

# ---------------------------------------------------------
# 初回起動処理（1問目の出題）
# ---------------------------------------------------------
if len(st.session_state.text_history) == 0:
    first_prompt = "スタート！最初の1問目を出題してください。"
    
    with st.spinner("コーチを呼び出し中..."):
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=first_prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.7,
            )
        )
        st.session_state.text_history.append({"role": "model", "text": response.text})

# ---------------------------------------------------------
# チャット履歴の表示
# ---------------------------------------------------------
for msg in st.session_state.text_history:
    avatar = "🤖" if msg["role"] == "model" else "👤"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["text"])

# ---------------------------------------------------------
# 回答入力エリア
# ---------------------------------------------------------
st.write("---")

audio_key = f"audio_input_{st.session_state.audio_key_count}"
audio_val = st.audio_input("🎙️ マイクを押して英語を声で回答する", key=audio_key)
user_input = st.chat_input("またはテキストで入力...")

# 音声入力があった場合
if audio_val:
    audio_bytes = audio_val.read()
    st.session_state.audio_key_count += 1

    # 履歴に回答事実を保存
    st.session_state.text_history.append({"role": "user", "text": "🎙️ （音声で回答しました）"})

    with st.chat_message("user", avatar="👤"):
        st.audio(audio_bytes, format="audio/wav")

    with st.chat_message("model", avatar="🤖"):
        with st.spinner("コーチが音声を聞いて採点中..."):
            # プロンプト（テキスト）と音声バイナリをパーツとして安全に結合
            text_prompt = build_prompt_from_history()
            contents = [
                types.Part.from_text(text=text_prompt),
                types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav")
            ]
            
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.7,
                )
            )
            st.markdown(response.text)
            st.session_state.text_history.append({"role": "model", "text": response.text})
            st.rerun()

# テキスト入力があった場合
elif user_input:
    st.session_state.text_history.append({"role": "user", "text": user_input})

    with st.chat_message("user", avatar="👤"):
        st.write(user_input)

    with st.chat_message("model", avatar="🤖"):
        with st.spinner("コーチが採点中..."):
            prompt = build_prompt_from_history()
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.7,
                )
            )
            st.markdown(response.text)
            st.session_state.text_history.append({"role": "model", "text": response.text})
            st.rerun()
