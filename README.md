# ainoveltools

1. 이제 GPT / Claude / Gemini 3가지 모델을 쓸 수 있음
2. 구조가 [소설폴더] - [챕터폴더] - [텍스트파일] 구조로 변형됨. 이에따라 설정도 구조에 맞춰 간소화됨. 디폴트 프롬프트 - 소설 설정 - 챕터 설정 - 장면 설정으로 적용됨.
3. 텍스트파일 생성(장면 생성)이 끝날때마다 소설 설정에 자동으로 [챕터폴더] 내의 텍스트파일 내용들이 요약되어 정리됨. 요약용 AI 모델을 따로 설정해야함.
4. 주의사항 : [챕터 폴더] 내의 텍스트파일들만 인풋이 들어감. 1-6화까지 있으면, 7화는 1-6화의 내용 + 소설 설정 + 챕터 설정 + 7화의 장면 설정이 들어가는 식임.
5. 만약 1-4화가 있는 상태에서 2화를 재생성하면 1화의 내용 + 소설 설정 + 챕터 설정 + 2화의 장면 설정이 들어가나, 소설설정에는 챕터폴더 내의 모든 텍스트파일이 요약되어 있으므로 내용이 괴상할 수도 있음.
6. 새로운 생성은 어떤 화의 텍스트파일을 클릭한 채로 생성해도 가장 마지막 생성된 텍스트파일까지 인풋으로 넣고 생성됨. 어지간하면 전개 변형을 원하는 곳까지 지우고 생성할 것.
7. 최초에 API 키를 3번 물음. 하나만 적어도 구동됨. 그런데 실행때마다 계속 물어볼텐데, 이건 설정 - API 설정에서 체크박스를 끄고 저장버튼을 눌러서 끌 수 있음.
8. 그 외 기타 등등 자잘한 수정이 있었음.
