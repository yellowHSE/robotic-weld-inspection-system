# 🤖 📷 Robotic-Weld-Inspection-System

> **자원 제약 환경에서의 YOLOv8 기반 용접 결함 탐지 및 로봇 시뮬레이션 통합 자동화 시스템 연구**

 본 프로젝트는 스마트 팩토리의 품질 관리 자동화를 위해 **YOLOv8 객체 탐지**와 **RoboDK 로봇 시뮬레이션**을 통합한 엔드투엔드(End-to-End) 솔루션을 제안합니다. 고사양 GPU(RTX 4080 SUPER) 환경에서 최적의 해상도 전략을 도출하고, 이를 다관절 로봇(UR10)의 분류 공정에 실시간 연동하였습니다.

## 📺 시연 영상 (Demo)

------

## 📂 파일 구조 (Project Structure)

저장소의 논리적 구성을 위해 다음과 같이 구조화되었습니다.

Plaintext

```
.
├── src/                        # 로봇 제어 및 공정 시뮬레이션 스크립트
│   ├── SetSimulationParams.py  # 실험 파라미터(속도, 크기 등) 설정
│   ├── PrepareSimulation.py    # 객체 및 용접 라벨 자동 생성 로직
│   ├── SimulateCamera.py       # 비전 검사 뷰 및 카메라 설정
│   ├── PartsToConveyor.py      # 로봇 1: 투입 및 이송 제어
│   ├── PartsToPallet.py        # 로봇 2: YOLO 연동 검사 및 분류 적재
│   └── HMI_Display.py          # 실시간 상태 모니터링 대시보드
├── models/                     # 학습된 YOLOv8 모델 가중치
│   ├── best_640.pt             # 640px 해상도 최적 가중치
│   └── best_480.pt             # 480px 해상도 최적 가중치 (추천 모델)
├── config/                     # 데이터셋 및 환경 설정 파일
│   ├── welding.yaml            # YOLO 데이터셋 경로 및 클래스 정의
│   └── station_env.rdk         # RoboDK 시뮬레이션 스테이션 파일
├── docs/                       # 보고서 및 시각화 자료
│   ├── report_final.pdf        # 최종 연구 결과 보고서
│   └── assets/                 # 분석 그래프(mAP, Loss) 및 결과 이미지
├── train.py                    # 모델 학습 및 검증 실행 스크립트
├── requirements.txt            # 라이브러리 의존성 파일
└── README.md                   # 프로젝트 개요 및 매뉴얼
```

------

## 📊 실험 결과 (AI Performance)

입력 해상도 변화에 따른 성능 및 추론 속도(Inference Speed) 비교 결과입니다.

| **Input Size**   | **mAP50**  | **Precision** | **Recall** | **Speed (RTX 4080s)** |
| ---------------- | ---------- | ------------- | ---------- | --------------------- |
| **640px**        | 0.6456     | 0.6726        | **0.6646** | 2.8ms                 |
| **480px (Best)** | **0.6523** | 0.6461        | 0.6516     | **2.1ms**             |
| **320px**        | 0.6241     | **0.7123**    | 0.5870     | 1.5ms                 |

- **최적 모델 선정**: 정확도와 연산 효율성을 동시에 만족하는 **480px** 설정을 최종 시스템에 적용함.

------

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

1. **RoboDK 실행**: `config/station_env.rdk` 파일을 로드합니다.
2. **파라미터 설정**: `src/SetSimulationParams.py`를 실행하여 공정 조건을 입력합니다.
3. **통합 공정 가동**: `src/PartsToPallet.py`를 실행하면 YOLOv8 모델이 카메라 뷰를 실시간 분석하여 로봇 분류를 시작합니다.

------

## 📜 라이선스 및 참고 문헌

- 본 프로젝트는 **Kaggle Welding Defect Dataset**과 **Ultralytics YOLOv8**을 활용하였습니다.
- 자세한 이론적 배경은 `docs/report_final.pdf`를 참조해 주시기 바랍니다.