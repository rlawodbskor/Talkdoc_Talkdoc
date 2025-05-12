import tkinter as tk
from tkinter import filedialog, messagebox
import re
from collections import defaultdict
import random
import openai

class KakaoTalkClone:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("카카오톡 대화학습 AI 챗봇 Talkdoc_Talkdoc")
        self.window.geometry("500x700")
        
        self.setup_ui()
        self.friend_data = {
            'name': '',
            'messages': [],
            'style_patterns': {
                'endings': defaultdict(int),
                'emoticons': defaultdict(int),
                'phrases': defaultdict(int),
                'sentence_length': [],
                'honorific_ratio': {'formal': 0, 'casual': 0}
            },
            'personality': '',
            'relation_type': ''
        }
        
        # GPT 설정
        self.system_prompt = ""
        self.conversation_history = []
        self.max_history = 5
        
    def setup_ui(self):
        # 상단 정보 표시
        self.info_frame = tk.Frame(self.window)
        self.info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.friend_label = tk.Label(self.info_frame, text="친구: 아직 학습 전")
        self.friend_label.pack(side=tk.LEFT)
        
        self.style_label = tk.Label(self.info_frame, text="말투: 분석 전")
        self.style_label.pack(side=tk.RIGHT)
        
        # 파일 선택 버튼
        tk.Button(self.window, text="카톡 파일 선택", command=self.load_file).pack(pady=5)
        
        # 채팅창
        chat_frame = tk.Frame(self.window)
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.chat_box = tk.Text(chat_frame, height=25)
        scrollbar = tk.Scrollbar(chat_frame, command=self.chat_box.yview)
        self.chat_box.configure(yscrollcommand=scrollbar.set)
        
        self.chat_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 입력창
        input_frame = tk.Frame(self.window)
        input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.input_box = tk.Entry(input_frame)
        self.input_box.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.input_box.bind('<Return>', lambda e: self.send_message())
        
        tk.Button(input_frame, text="전송", command=self.send_message).pack(side=tk.RIGHT, padx=5)
    
    def analyze_messages(self, messages):
        total_messages = len(messages)
        personality_traits = []
        
        # 기본 패턴 분석
        for msg in messages:
            # 이모티콘
            emoticons = re.findall(r'[ㅋㅎㅉㅠㅜㅇㄷㄱㅂㅅㄹㅎㅋ]{2,}|[\U0001F300-\U0001F9FF\U0001F600-\U0001F64F\U0001F680-\U0001F6FF\u2600-\u26FF\u2700-\u27BF]+', msg)
            for emo in emoticons:
                self.friend_data['style_patterns']['emoticons'][emo] += 1
            
            # 문장 끝맺음
            if len(msg) > 0:
                ending = msg[-1] if not msg[-1].isspace() else msg[-2]
                self.friend_data['style_patterns']['endings'][ending] += 1
            
            # 문장 길이
            self.friend_data['style_patterns']['sentence_length'].append(len(msg))
            
            # 존댓말 vs 반말
            if any(word in msg for word in ['습니다', '니다', '세요']):
                self.friend_data['style_patterns']['honorific_ratio']['formal'] += 1
            elif any(word in msg for word in ['야', '어', '음', '죠', '함']):
                self.friend_data['style_patterns']['honorific_ratio']['casual'] += 1
            
            # 자주 쓰는 표현 (2글자 이상)
            words = msg.split()
            for word in words:
                if len(word) >= 2:
                    self.friend_data['style_patterns']['phrases'][word] += 1
        
        # 성격 특성 분석
        emoticon_ratio = len(self.friend_data['style_patterns']['emoticons']) / total_messages
        avg_length = sum(self.friend_data['style_patterns']['sentence_length']) / total_messages
        formal_ratio = self.friend_data['style_patterns']['honorific_ratio']['formal'] / total_messages
        
        if emoticon_ratio > 0.5:
            personality_traits.append("활발하고 감정표현이 풍부한")
        else:
            personality_traits.append("차분하고 절제된")
        
        if avg_length > 20:
            personality_traits.append("말이 많은")
        else:
            personality_traits.append("간결한 대화를 선호하는")
        
        if formal_ratio > 0.5:
            personality_traits.append("예의바른")
        else:
            personality_traits.append("친근한")
        
        self.friend_data['personality'] = ', '.join(personality_traits)
        
        # 관계 유형 파악
        if any(title in self.friend_data['name'] for title in ['선생님', '교수님', '원장님', '쌤']):
            self.friend_data['relation_type'] = 'teacher'
        elif self.friend_data['style_patterns']['honorific_ratio']['formal'] > self.friend_data['style_patterns']['honorific_ratio']['casual']:
            self.friend_data['relation_type'] = 'formal'
        else:
            self.friend_data['relation_type'] = 'casual'
        
        # GPT 시스템 프롬프트 생성
        self.create_system_prompt()
    
    def create_system_prompt(self):
        # 가장 자주 쓰는 표현들
        top_phrases = sorted(self.friend_data['style_patterns']['phrases'].items(), 
                           key=lambda x: x[1], reverse=True)[:10]
        top_emoticons = sorted(self.friend_data['style_patterns']['emoticons'].items(), 
                             key=lambda x: x[1], reverse=True)[:5]
        
        if self.friend_data['relation_type'] == 'teacher':
            self.system_prompt = f"""
당신은 이제 {self.friend_data['name']}입니다. 학생들과 편하게 카톡하는 선생님입니다.

말투 특징:
1. 자주 쓰는 표현: {', '.join(f"'{p[0]}'" for p in top_phrases)}
2. 자주 쓰는 이모티콘: {', '.join(f"'{e[0]}'" for e in top_emoticons)}

반드시 지켜야 할 규칙:
- 기본적으로는 반말을 섞어서 편하게 대화하세요
- 너무 격식있거나 딱딱한 말투는 피하세요
- "~해", "~하자", "~했어?", "~구나" 같은 편한 어미를 사용하세요
- 이모티콘도 자유롭게 사용하세요
- 가끔 "ㅋㅋ", "ㅎㅎ" 같은 가벼운 표현도 사용해도 됩니다
- 학생을 대하는 따뜻함은 유지하되, 너무 형식적이지 않게 해주세요

예시:
- "시험 잘 봤어?"
- "그래 다음에 물어보자 ㅎㅎ"
- "숙제는 다 했니?"
- "응 알겠어~ 수고했어"
- "다음 주까지 하면 돼 ㅋㅋ"
- "그럼 내일 보자~"
"""
        elif self.friend_data['relation_type'] == 'casual':
            self.system_prompt = f"""
당신은 이제 {self.friend_data['name']}입니다. 10대~20대의 친한 친구와 카톡하듯이 자연스럽게 대화하세요.

말투 특징:
1. 격식 없이 완전 친근하게 대화하세요
2. 자주 쓰는 표현: {', '.join(f"'{p[0]}'" for p in top_phrases)}
3. 자주 쓰는 이모티콘: {', '.join(f"'{e[0]}'" for e in top_emoticons)}

반드시 지켜야 할 규칙:
- 친한 친구처럼 완전 편하게 대화하세요
- 가벼운 욕이나 친근한 표현 사용 가능 ("야", "씨", "아 진짜", "미친", "대박" 등)
- 맞춤법이나 띄어쓰기는 신경쓰지 마세요
- 축약어 자주 쓰기 ("ㅇㅇ", "ㄴㄴ", "ㄹㅇ", "ㅋㅋㅋ", "ㅇㅈ" 등)
- 문장을 완성하지 않아도 됨 (끊어서 보내기)
- 이모티콘 많이 쓰기
- 상황에 따라 답답할 때는 짜증도 내도 됨

대화 예시:
- "야 미친ㅋㅋㅋㅋ"
- "아 진짜?"
- "ㄹㅇ 개웃기다"
- "아씨 짜증나네"
- "대박 미쳤다"
- "ㅇㅈㅇㅈ"
- "아 몰랑"
- "ㄴㄴ 아님 ㅋㅋ"
- "와 실화냐"

위의 규칙들을 자연스럽게 섞어가면서, 진짜 친한 친구처럼 대화해주세요. 하지만 심한 욕설은 사용하지 마세요.
"""
    
    def get_gpt_response(self, user_input):
        try:
            # 대화 기록 업데이트
            self.conversation_history.append({"role": "user", "content": user_input})
            
            # API 요청
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    *self.conversation_history[-self.max_history:]
                ],
                temperature=0.9,
                presence_penalty=0.6,
                frequency_penalty=0.2,
                max_tokens=150
            )
            
            reply = response.choices[0].message.content
            self.conversation_history.append({"role": "assistant", "content": reply})
            
            return reply
            
        except Exception as e:
            return f"죄송해요, 오류가 발생했어요: {str(e)}"
    
    def load_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # 실제 대화 내용이 있는 줄부터 시작
                chat_lines = []
                for line in lines:
                    if '---------------' in line or '저장한 날짜' in line:
                        continue
                    if re.match(r'\[.*?\] \[.*?\]', line):  # [이름] [시간] 형식인 줄만 저장
                        chat_lines.append(line)
                
                # 대화 참여자 찾기
                participants = set()
                for line in chat_lines:
                    match = re.match(r'\[(.*?)\]', line)
                    if match:
                        name = match.group(1)
                        participants.add(name)
                
                # 내 이름을 제외한 상대방 찾기
                my_name = "김재윤"  # 본인 이름
                friend_name = next(name for name in participants if name != my_name)
                self.friend_data['name'] = friend_name
                
                # 친구 메시지만 추출
                friend_messages = []
                for line in chat_lines:
                    if f"[{friend_name}]" in line:
                        # 날짜, 시간, 이름 제거하고 메시지만 추출
                        clean_msg = re.sub(r'\[.*?\] \[.*?\]', '', line).strip()
                        if clean_msg:  # 빈 메시지가 아닌 경우만
                            friend_messages.append(clean_msg)
                
                if not friend_messages:
                    raise Exception("대화 내용을 찾을 수 없습니다.")
                
                self.friend_data['messages'] = friend_messages
                self.analyze_messages(friend_messages)
                
                # UI 업데이트
                self.friend_label.config(text=f"친구: {self.friend_data['name']}")
                self.style_label.config(text=f"말투: 학습 완료")
                
                self.chat_box.insert(tk.END, f"=== {self.friend_data['name']}님의 말투를 학습했어요! ===\n")
                self.chat_box.insert(tk.END, f"성격: {self.friend_data['personality']}\n\n")
                
            except Exception as e:
                messagebox.showerror("에러", f"파일 읽기 실패: {str(e)}")
    
    def send_message(self):
        msg = self.input_box.get().strip()
        if msg:
            self.chat_box.insert(tk.END, f"나: {msg}\n")
            response = self.get_gpt_response(msg)
            self.chat_box.insert(tk.END, f"{self.friend_data['name']}: {response}\n\n")
            self.chat_box.see(tk.END)
            self.input_box.delete(0, tk.END)
    
    def run(self):
        self.window.mainloop()

if __name__ == "__main__":
    # OpenAI API 키 설정
    openai.api_key = ""
    
    app = KakaoTalkClone()
    app.run()