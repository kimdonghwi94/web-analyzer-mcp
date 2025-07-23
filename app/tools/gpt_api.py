from openai import OpenAI
import re
import json


def summarize_text(question, text: str) -> str:

    """간단한 요약 함수.

    텍스트를 마침표/물음표/느낌표를 기준으로 문장 단위로 분할한 뒤
    앞에서부터 `max_sentences`개의 문장을 이어 붙인다. 만약
    요약된 문자열의 길이가 `max_chars`보다 길면 해당 위치에서 잘라
    '...'을 붙인다.

    Args:
        text: 요약할 원본 문자열

    Returns:
        요약된 문자열
    """
    client = OpenAI(api_key="")

    result = {
        "result": "답변"
    }
    SYSTEM_PROMPT = ("당신은 manager 정보를 받고, 사용자 질문과 매칭하여 질의 응답 해주는 에이전트 입니다. 사용자의 질문을 받고,답변을 해주세요"
                     f"- 출력은 다음과 같이 만들어 주세요 : {result}"
                     f"- 간략 대답해주세요"
                     f"- 항상 친절하게 대답하세요"
                     f"- 답변내용이 어려울 경우, 죄송합니다 답변할수없습니다 라고 대답하세요")



    msg = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"사용자 질문 : [{question}] 데이터:\n{text} 출력은 다음과 같이 만들어주세요 {result}"}
    ]
    res = client.chat.completions.create(
        model="gpt-4o-mini",  # 가볍게 빠른 모델 예시. 필요시 더 큰 모델로 교체
        messages=msg,
        temperature=0.2,
        max_tokens=400,
    )
    gpt_result = res.choices[0].message.content.strip()

    s = re.sub(r"'(\w+)'\s*:", r'"\1":', gpt_result)

    # 2) 값 '...'(안에 작은따옴표 있을 수 있음) -> json.dumps 로 안전 escape
    def repl(m):
        inner = m.group(1)
        return ": " + json.dumps(inner, ensure_ascii=False)

    s = re.sub(r':\s*\'(.*?)\'(?=\s*[,\}])', repl, s, flags=re.S)

    data = json.loads(s)

    return data['result']