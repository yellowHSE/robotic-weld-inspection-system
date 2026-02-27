# 🤖 📷 Robotic-Weld-Inspection-System


> **자원 제약 환경에서의 YOLOv8 기반 용접 결함 탐지 및 로봇 시뮬레이션 통합 자동화 시스템 연구**


 본 프로젝트는 스마트 팩토리의 품질 관리 자동화를 위해 **YOLOv8 객체 탐지**와 **RoboDK 로봇 시뮬레이션**을 통합한 엔드투엔드(End-to-End) 솔루션을 제안합니다. 고사양 GPU(RTX 4080 SUPER) 환경에서 최적의 해상도 전략을 도출하고, 이를 다관절 로봇(UR10)의 분류 공정에 실시간 연동하였습니다.

## 📺 시연 영상 (Demo)

[[[[URL]]]]

## 📂 프로젝트 구조 (Project Structure)
robotic-weld-inspection-system/
│
├─ ai/ # AI 모델 및 추론 스크립트
│ ├─ configs/ # 설정 파일
│ │ └─ welding.yaml
│ ├─ inferenrce/ # 추론용 스크립트
│ │ └─ inference.py
│ ├─ models/ # 모델 가중치 및 학습 스크립트
│ │ ├─ pretrained/ # 사전 학습 모델
│ │ │ └─ yolov8s.pt
│ │ ├─ trained/ # 학습 완료 모델 (해상도별)
│ │ │ ├─ res320/weights/
│ │ │ ├─ res480/weights/
│ │ │ └─ res640/weights/
│ │ └─ training/ # 학습 스크립트
│ │ ├─ train320.py
│ │ ├─ train480.py
│ │ └─ train640.py
│ ├─ results/ # 학습/추론 결과
│ │ ├─ res320/
│ │ ├─ res480/
│ │ └─ res640/
│ └─ utils/
│ └─ data_download.py
│
├─ robotics/ # 로봇 시뮬레이션 관련 파일
│ ├─ imgs/ # 용접 템플릿 이미지
│ ├─ objects/ # 용접 템플릿 3D 모델
│ │ ├─ WeldTpl_01/
│ │ ├─ WeldTpl_02/
│ │ ├─ WeldTpl_03/
│ │ ├─ WeldTpl_04/
│ │ ├─ WeldTpl_05/
│ │ ├─ WeldTpl_06/
│ │ ├─ WeldTpl_07/
│ │ ├─ WeldTpl_08/
│ │ └─ WeldTpl_09/
│ └─ scripts/ # 시뮬레이션 제어 스크립트
│ ├─ PartsToConveyor.py
│ ├─ PartsToPallet.py
│ ├─ PrepareSimulation.py
│ ├─ SetSimulationParams.py
│ └─ SimulateCamera.py
│
├─ .gitignore
└─ README.md

## 📊 실험 결과 (AI Performance)

입력 해상도 변화에 따른 성능 및 추론 속도(Inference Speed) 비교 결과입니다.

| **Input Size**   | **mAP50**  | **Precision** | **Recall** | **Speed (RTX 4080s)** |
| ---------------- | ---------- | ------------- | ---------- | --------------------- |
| **640px**        | 0.6456     | 0.6726        | **0.6646** | 2.8ms                 |
| **480px (Best)** | **0.6523** | 0.6461        | 0.6516     | **2.1ms**             |
| **320px**        | 0.6241     | **0.7123**    | 0.5870     | 1.5ms                 |

- **최적 모델 선정**: 정확도와 연산 효율성을 동시에 만족하는 **480px** 설정을 최종 시스템에 적용함.


## 🚀 시작하기 (How to Run)

### **1. 환경 구축**

Bash

```
git clone https://github.com/yellowHSE/robotic-weld-inspection-system.git
cd robotic-weld-inspection-system
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### **2. 시뮬레이션 실행**
RoboDK에서 시뮬레이션 환경을 구성합니다.  
1. `robotics/objects` 폴더에 있는 8개의 용접 객체(WeldTpl_01 ~ WeldTpl_08)를 RoboDK 환경에 추가합니다.  
2. `robotics/scripts` 폴더 내 4개의 스크립트 파일을 불러와 프로그램을 생성한 후 실행합니다.

**프로그램 실행 순서:**
1. Call `PrepareSimulation` – 시뮬레이션 초기 환경 설정
2. Call `SimulateCamera` – 카메라 시뮬레이션
3. Run `MoveConveyor` – 컨베이어 이동
4. Run `PartsToConveyor` – 부품 컨베이어로 이동
5. Call `PartsToPallet` – 부품 팔레트로 이동

## 📜 참고 자료
- 본 프로젝트에서는 **Kaggle Welding Defect Dataset**을 활용하였습니다.
- RoboDK 무료 버전 사용으로 인해 시뮬레이션 파일 자체는 저장되지 않아, 스크립트만 제공합니다.